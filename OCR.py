# -*- coding: utf-8 -*-
from io import BytesIO
import os
from asyncio import get_event_loop, gather
import numpy as np
import pytesseract
from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QCheckBox
from typing import List
from PIL import Image
from google.cloud import vision
from google.oauth2 import service_account
from Receipt import Receipt
from ImageProc import SlidersValue, apply_mask_image, to_gray, imread, crop_image, get_crop_rects
from util import sort_rects, set_exif, get_exif, find_sheet_date, set_receipt_info_from_ocr, make_json


def get_service(script_dir):

    key_file_name = 'credentials.json'
    key_file_path = os.path.join(script_dir, key_file_name)
    creadentials = service_account.Credentials.from_service_account_file(key_file_path)
    client = vision.ImageAnnotatorClient(credentials=creadentials)
    return client


def sort_bounds_old(text_annotations):
    """テキストの位置情報を基にしてソートし、行ごとにテキストを整理する"""
    sorted_by_x = sorted(text_annotations[1:], key=lambda x: x.bounding_poly.vertices[0].x)
    lines = []

    while sorted_by_x:
        line = []
        temp_sorted_results = []
        base_item = min(sorted_by_x, key=calculate_y_value)
        base_y_value = calculate_y_value(base_item)
        for item in sorted_by_x:
            if abs(calculate_y_value(item) - base_y_value) <= 15:
                line.append(item)
            else:
                temp_sorted_results.append(item)
        lines.append(line)
        sorted_by_x = temp_sorted_results
    return lines


def calculate_y_value(item):
    """
    テキストアノテーションアイテムの中心のY座標を計算します。

    Parameters:
    - item (google.cloud.vision_v1.types.TextAnnotation):  テキストアノテーションアイテム。

    Returns:
    - float:  テキストアノテーションアイテムの中心のY座標。
    """
    return item.bounding_poly.vertices[0].y + (item.bounding_poly.vertices[2].y - item.bounding_poly.vertices[0].y) / 2


def sort_bounds(text_annotations):
    """
    テキストアノテーションをX座標でソートし、Y座標に基づいて行ごとにテキストを整理します。

    Parameters:
    - text_annotations (list):  テキストアノテーションのリスト。

    Returns:
    - list:  行ごとに整理されたテキストアノテーションのリスト。
    """
    sorted_by_x = sorted(text_annotations[1:], key=lambda x: x.bounding_poly.vertices[0].x)
    lines = []

    while sorted_by_x:
        line = []
        temp_sorted_results = []
        base_item = min(sorted_by_x, key=calculate_y_value)
        base_y_value = calculate_y_value(base_item)
        for item in sorted_by_x:
            if abs(calculate_y_value(item) - base_y_value) <= 15:
                line.append(item)
            else:
                temp_sorted_results.append(item)
        lines.append(line)
        sorted_by_x = temp_sorted_results
    return lines


def vision_ocr(client, image):
    """
    Google Cloud Vision APIを使用して画像からテキストを抽出します。

    Parameters:
    - client (google.cloud.vision_v1.ImageAnnotatorClient): Vision APIクライアント。
    - image (numpy.ndarray):   画像データ。

    Returns:
    - str: 抽出されたテキスト。
    """
    #  画像データをPILイメージに変換
    image_pil = Image.fromarray(image)
    #  バイト配列を作成して画像をPNG形式で保存
    img_byte_arr = BytesIO()
    image_pil.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()

    # Google Cloud Vision APIのImageオブジェクトを作成
    image = vision.Image(content=img_byte_arr)

    #  テキスト検出を実行
    response = client.text_detection(image=image)
    #  テキストアノテーションを取得
    text_annotations = response.text_annotations
    #  テキストアノテーションを行ごとにソート
    lines = sort_bounds(text_annotations)
    # 各行のテキストを整理
    line_text_arr = []
    for line in lines:
        texts = []
        if len(line) > 0:
            #  最初のアイテムの幅と文字数を取得
            vert = line[0].bounding_poly.vertices
            item_width = vert[2].x - vert[0].x
            item_str_length = len(line[0].description)
            item_char_width = item_width / item_str_length
            for i, item in enumerate(line):
                if i > 0:
                    #  前のアイテムとの間のスペースを計算
                    item_vert = item.bounding_poly.vertices
                    this_item_left = item_vert[0].x
                    end_item = line[i - 1]
                    end_item_right = end_item.bounding_poly.vertices[1].x
                    space = this_item_left - end_item_right
                    #  スペースが文字幅よりも大きい場合、スペースをスペース文字で補完
                    if item_char_width < space:
                        space_count = int(space / item_char_width)
                        if space_count > 0:
                            texts.append(' ' * space_count)
                #  アイテムのテキストを追加
                texts.append(item.description)
        #  行のテキストを結合
        line_text_arr.append(''.join(texts))
    #  すべての行のテキストを改行で結合
    ocr_text = '\n'.join(line_text_arr)
    #  エラーメッセージがある場合は例外を発生させる
    if response.error.message:
        raise Exception('{}\nFor more info on error messages, check: '
                        'https://cloud.google.com/apis/design/errors'.format(response.error.message))

    return ocr_text


def tess_OCR(img, tess_command=""):
    image = pre_process_for_receipt(img)

    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    custom_config = fr"{tess_command}"
    # Tesseractを使用してOCR実行
    text = pytesseract.image_to_string(image, config=custom_config)
    # 結果のテキストを表示
    return text


def pre_process_for_receipt(img: np.ndarray) -> np.ndarray:
    maskd_image = apply_mask_image(img)
    gray = to_gray(maskd_image)
    return gray


async def async_tess_OCR(receipt: Receipt, supplyer_dic, tess_command=""):

    loop = get_event_loop()

    with ThreadPoolExecutor() as executor:
        receipt.ocr_text = await loop.run_in_executor(executor, tess_OCR, receipt.receipt_image, tess_command)
        receipt = set_receipt_info_from_ocr(receipt, supplyer_dic)
    return receipt


def get_receipt_image_list(source, receipts):
    if isinstance(source, str):
        image = imread(source)
    elif isinstance(source, np.ndarray):
        image = source

    for receipt in receipts:
        receipt: Receipt = receipt
        receipt.receipt_image = crop_image(image, receipt.rect)

    return receipts


async def start_async_ocr(image_path, supplyer_dic, slider_values: SlidersValue):
    # rm.create_receipt_manager(image_path)
    rectangles = get_crop_rects(image_path, slider_values)
    receipts: List[Receipt] = []
    for rect in rectangles:
        receipts.append(Receipt(rect))
    receipts = get_receipt_image_list(image_path, receipts)
    tess_command = get_tess_command()
    tasks = [async_tess_OCR(receipt, supplyer_dic, tess_command) for receipt in receipts]
    await gather(*tasks)
    receipts, sheet_date_str = find_sheet_date(receipts)
    json_string = make_json(sheet_date=sheet_date_str, receipts=receipts)
    set_exif(receipts=receipts, filename=image_path, sheet_date=sheet_date_str, json_string=json_string)

    return receipts


class ReceiptOCRThread_by_Vision(QThread):
    finished_OCR = Signal()

    def __init__(self, receipt: Receipt, supplyer_dic, client):
        super().__init__()
        self.rec = receipt
        self.supplyer_dic = supplyer_dic
        self.client = client

    def run(self):
        receipt = self.rec
        receipt.ocr_text = vision_ocr(self.client, receipt.receipt_image)
        receipt = set_receipt_info_from_ocr(receipt, supplyer_dic=self.supplyer_dic)
        self.finished_OCR.emit()


class ReceiptOCRThread(QThread):
    finished_OCR = Signal()

    def __init__(self, receipt: Receipt, supplyer_dic, tess_command):
        super().__init__()
        self.rec = receipt
        self.supplyer_dic = supplyer_dic
        self.tess_command = tess_command

    def run(self):
        receipt = self.rec
        receipt.ocr_text = tess_OCR(receipt.receipt_image, self.tess_command)
        receipt = set_receipt_info_from_ocr(receipt, supplyer_dic=self.supplyer_dic)
        self.finished_OCR.emit()


def get_tess_command():
    tess_command = ""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # command.txtのパスを取得
    command_path = os.path.join(current_dir, 'command.txt')
    with open(command_path, 'r', encoding='utf-8') as file:
        tess_command = file.read()
    return tess_command


class SheetProcessThread(QThread):
    finished = Signal(object)
    started = Signal(object)
    on_finished_ocr = Signal()

    def __init__(self, mainWindow, filepath, isOcrOnly=False):
        super().__init__()
        self.mainWIndow = mainWindow
        self.sliders_value = mainWindow.sliders_value
        self.filepath = filepath
        self.ocrThreadsFinished = 0
        self.ocrThreads = []
        self.receipts: List[Receipt] = []
        self.supplyer_dic = mainWindow.supplyer_dic
        self.tess_command = get_tess_command()
        checkbox: QCheckBox = mainWindow.OCR_Tesseract_CheckBox
        self.isTessOCR = checkbox.isChecked()
        self.isOcrOnly = isOcrOnly

    def run(self):
        filepath = self.filepath
        if not os.path.isfile(filepath):
            return
        sheet_image = imread(filepath)
        if self.isOcrOnly:
            result, _, self.receipts = get_exif(filepath)
            if result is False:
                return
        else:
            rectangles = get_crop_rects(sheet_image, self.sliders_value)
            if not rectangles:
                return
            sorted_rectangles = rectangles if len(rectangles) == 1 else sort_rects(rectangles)

            for rect in sorted_rectangles:
                self.receipts.append(Receipt(rect))

        get_receipt_image_list(sheet_image, self.receipts)
        self.started.emit(len(self.receipts))
        for receipt in self.receipts:
            if self.isTessOCR:
                thread = ReceiptOCRThread(receipt, self.supplyer_dic, self.tess_command)
            else:  # Vision OCRの場合は、スレッドを分ける必要があるため、ReceiptOCRThread_by_Visionを使うようにする。
                thread = ReceiptOCRThread_by_Vision(receipt, self.supplyer_dic, self.mainWIndow.client)
            self.receipts = self.receipts
            thread.finished_OCR.connect(self.on_finished_ocr)  # スレッドの完了シグナルを受け取る
            thread.finished.connect(self.checkAllSubThreadsFinished)  # スレッドの完了シグナルを受け取る
            thread.start()
            self.ocrThreads.append(thread)

    def checkAllSubThreadsFinished(self):
        self.ocrThreadsFinished += 1
        # すべてのサブスレッドが終了した場合
        if self.ocrThreadsFinished == len(self.ocrThreads):
            if len(self.receipts) != 0:
                self.receipts, sheet_date_str = find_sheet_date(self.receipts)
                json_string = make_json(sheet_date=sheet_date_str, receipts=self.receipts)
                saved_fileName = set_exif(receipts=self.receipts, filename=self.filepath, sheet_date=sheet_date_str, json_string=json_string)
            self.finished.emit([saved_fileName, self.filepath])  # 処理完了シグナルを発信
