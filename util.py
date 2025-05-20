# -*- coding: utf-8 -*-

import inspect
import os
from sys import exit
from re import search
import datetime as dt
from enum import Enum
import json
from threading import RLock
from datetime import datetime
from typing import Tuple, Optional
from collections import namedtuple
from piexif import load as exif_load, ImageIFD, dump as exif_dump, insert
from PySide6.QtWidgets import QWidget, QMessageBox, QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import QObject, QEvent
from Receipt import Receipt, RotatedRect
import cv2


class ApplicationEventFilter(QObject):
    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.FocusIn:
            if isinstance(watched, QWidget):  # ウィジェットにフォーカスが移ったことを確認
                pass
        return super().eventFilter(watched, event)
# アプリケーション全体に対するイベントフィルタを設置する際に、以下のように設置
# if __name__ == '__main__':
#   app = QApplication(sys.argv)
#   event_filter = ApplicationEventFilter()
#   app.installEventFilter(event_filter)


class ImageType(Enum):
    Both = 0
    Sheet = 1
    Receipt = 2


class MoveTo(Enum):
    Previous = 0
    Next = 1


class BooleanWatcher:
    def __init__(self, initial_value=False, callback=None):
        self._lock = RLock()
        self._v = initial_value
        self._callback = callback

    @property
    def v(self):
        with self._lock:
            return self._v

    @v.setter
    def v(self, new_value):
        with self._lock:
            if self._v != new_value:
                self._v = new_value
                if self._callback:
                    self._callback(self)


class Point:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def pos(self):
        return (self.x, self.y)


class SaveMode(Enum):
    OVER_WRITE = 0
    SAVE_NEW = 1


def convert_to_rotated_rect(rect: Tuple[Tuple[int, int], Tuple[int, int], int]) -> RotatedRect:
    return RotatedRect(center=rect[0], size=rect[1], angle=rect[2])


def scaled_point_to_original_point(self: QLabel, event):
    original_SheetPixmap: QPixmap = self.original_SheetPixmap
    if original_SheetPixmap is None:
        return Point(x=0, y=0), False
    pixmapScaled = self.pixmap().size()
    scaleWidth = pixmapScaled.width() / original_SheetPixmap.width()
    scaleHeight = pixmapScaled.height() / original_SheetPixmap.height()

    xOriginal = (event.x() - (self.width() - pixmapScaled.width()) / 2) / scaleWidth
    yOriginal = (event.y() - (self.height() - pixmapScaled.height()) / 2) / scaleHeight
    result = Point(x=int(xOriginal), y=int(yOriginal))
    # result: ResultPoint = self.scaled_point_to_original_point(event)

    pixmap = original_SheetPixmap
    isInArea = isPoint_in_area(result, pixmap)
    if result.x < 0:
        result.x = 0
    elif result.x > pixmap.width():
        result.x = pixmap.width()

    if result.y < 0:
        result.y = 0
    elif result.y > pixmap.height():
        result.y = pixmap.height()

    return result, isInArea


def isPoint_in_area(point, pixmap) -> bool:

    if (pixmap.width() > point.x > 0) and (pixmap.height() > point.y > 0):
        return True
    return False


def parse_date_string(datelike: str) -> Optional[dt.date]:
    if datelike is None:
        return None
    elif isinstance(datelike, dt.date):
        return datelike
    for format in ("%Y年%m月%d日", "%Y/%m/%d", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(datelike, format)
        except ValueError:
            #            print(f"Error parse_date_string with {datelike} with format {format}")
            continue
    return None


def conv_date_string(datelike) -> Optional[str]:
    if datelike is None:
        return ""
    elif isinstance(datelike, dt.date):
        return datelike.strftime('%Y年%m月%d日')
    elif isinstance(datelike, str):
        if datelike == "" or datelike is None:
            return ""
        try:
            date_value: dt.date = parse_date_string(datelike)
            if date_value is None:
                return ""
            date_str = date_value.strftime('%Y年%m月%d日')
            if isinstance(date_str, str):
                return date_str
        except Exception as e:
            print(f"Error conv_date_string with {datelike} with format {format}", e)
            return ""
    return ""


class surplyer_dic:
    def __init__(self):
        with open('suplyerDictionary.json', 'r', encoding='utf-8') as file:
            self.suplyer_dic = json.load(file)

    def get_suplyer(self):
        return self.suplyer_dic


def msgBox(text: str, title: str = "メッセージ", icon_type=QMessageBox.Information, button_type: int = QMessageBox.Ok):
    msg = QMessageBox()
    msg.setIcon(icon_type)
    msg.setText(text)
    msg.setWindowTitle(title)
    msg.setStandardButtons(button_type)
    retval = msg.exec()
    return retval


def set_receipt_info_from_ocr(self: Receipt, supplyer_dic) -> Receipt:
    ocr_text = self.ocr_text
    self.item_category = "食材料費"
    self.ocr_text = ocr_text
    # 店名の特定
    for supplyer, data in supplyer_dic.items():
        if any(search(pattern, ocr_text) for pattern in data['Values']):
            self.supplyer_name = supplyer
            labels = data['CalculationLabels']
            if data['CalculationMethod'] == 'Sum':
                total = self.calculate_sum(ocr_text, labels)
            elif data['CalculationMethod'] == 'Direct':
                total = self.calculate_direct(ocr_text, labels)
            self.amount = total = str(total)
            break

    # 日付の解析
    date_patterns = [
        r"\d{4}\s*/\s*\d{1,2}\s*/\s*\d{1,2}",  # YYYY/M/D
        r"\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日"  # YYYY年M月D日
    ]

    for pattern in date_patterns:
        match = search(pattern, ocr_text)
        if match:
            date_value = parse_date_string(match.group().replace(" ", "").replace("　", "").replace("年", "-").replace("月", "-").replace("日", "").replace("/", "-"))

            self.date = date_value.strftime("%Y年%m月%d日") if date_value is not None else ""
            break
    return self


def calculate_x_value(item):
    # 角度が0度以上45度未満の場合、box[0]からbox[1]は高さ
    # 角度が45度以上の場合、box[0]からbox[1]は幅
    # 角度を元に幅と高さを調整
    if isinstance(item, Receipt):
        item = item.rect
    angle = item.angle
    if angle < 45:
        return item.center[0] - item.size[0] / 2
    else:
        return item.center[0] - item.size[1] / 2


def sort_by_x(sorted_by_y: list[Receipt]) -> list[Receipt]:
    # ソートを実行し、Xの値が小さい順にソートされFたリストを返す
    # Xの値の計算関数はcalculate_x_value関数に任せる
    sorted_results = []
    while sorted_by_y:
        temp_sorted_results = []
        # 基準となるアイテム（Xの値が最小のもの）
        base_item = min(sorted_by_y, key=calculate_x_value)
        base_x_value = calculate_x_value(base_item)

        # グループ化されるアイテムを選択
        for item in sorted_by_y:
            if abs(calculate_x_value(item) - base_x_value) <= 300:
                sorted_results.append(item)
            else:
                temp_sorted_results.append(item)

        # グループ化されたアイテムを元のリストから削除
        sorted_by_y = temp_sorted_results

    return sorted_results


def sort_rects(arg) -> list[Receipt]:
    if isinstance(arg, list):
        if len(arg) == 0:
            return None
        # list[RotatedRect]
        if isinstance(arg[0], Receipt):
            data = arg
            sorted_by_y = sorted(data, key=lambda x: x.rect.center[1] - (x.rect.size[0] if x.rect.angle < 45 else x.rect.center[1]) / 2)
        elif isinstance(arg[0], cv2.RotatedRect):
            data = arg
            sorted_by_y = sorted(data, key=lambda x: x.center[1] - (x.size[0] if x.angle < 45 else x.center[1]) / 2)

    elif isinstance(arg, str):
        # JSON文字列
        if is_json(arg):
            data = json.loads(arg)
        elif os.path.isfile(arg):
            with open(arg, encoding="utf-8") as file:
                data = json.load(file)
        sorted_by_y = sorted(data, key=lambda x: x["Rect"]["Center"]["Y"])

    elif isinstance(arg, dict):
        data = arg

    else:
        return None
    # ソートを実行
    sorted_result = sort_by_x(sorted_by_y)
    return sorted_result


def is_json(myjson: str) -> bool:
    try:
        _ = json.loads(myjson)
    except ValueError:
        return False
    return True


def find_sheet_date(receipts: list[Receipt], date=None,) -> tuple[list[Receipt], str]:
    sheet_date = None
    if parse_date_string(date) is not None:
        sheet_date = date
        return receipts, sheet_date
    if len(receipts) == 1:
        sheet_date = receipts[0].date
        return receipts, sheet_date
    elif len(receipts) == 0:
        sheet_date = ""
        return receipts, sheet_date
    # receiptsのdateの値を候補日付としてリスト作成
    date_candidates_str = []
    for receipt in receipts:
        if receipt.date != "":
            date_candidates_str.append(receipt.date)
    date_candidates = [parse_date_string(date_str) for date_str in date_candidates_str]
    if len(date_candidates) == 0:
        sheet_date = ""
        return receipts, sheet_date

    # date_candidatesの値が全て同じだったら
    if len(set(date_candidates)) == 1:
        date_val = date_candidates[0]
    else:  # 最も実行日に近い日付を見つける
        date_val = min(date_candidates, key=lambda date: abs(date - datetime.today()))

    sheet_date = conv_date_string(date_val)
    for receipt in receipts:
        receipt.date = sheet_date
    return receipts, sheet_date


def make_json(sheet_date: str, receipts: list[Receipt]):
    json_list = {}
    json_list["sheet_date"] = sheet_date
    receipt_data = []
    for receipt in receipts:
        r = receipt.rect
        receipt_arr = {
            "date": receipt.date,
            "category": receipt.item_category,
            "supplyer": receipt.supplyer_name,
            "amount": receipt.amount,
            "ocrt": receipt.ocr_text,
            "rect": {"center": r.center, "size": r.size, "angle": r.angle}}
        receipt_data.append(receipt_arr)
    json_list["receipt_data"] = receipt_data

    return json.dumps(json_list, ensure_ascii=False)


def create_unique_receipt_filename(path, lang, font_name, ext):
    """
    指定されたパスに対して、既存のファイルと重複しないユニークなファイル名を生成します。
    既にファイルが存在する場合は、カウンタを付加して新しいファイル名を生成します。
    :param path: 生成するユニークなファイル名の基本となるパス
    :param lang: ファイル名の言語
    :param font_name: ファイル名のフォント名
    :param ext: ファイル名の拡張子
    :return: 既存のファイルと重複しないユニークなファイル名。エラーが発生した場合はNoneを返す
    """
    counter = 0
    new_filename = f"{lang}.{font_name}.exp{counter}{ext}"
    fullpath = os.path.join(path, new_filename)
    # 既存のファイルと重複しない場合は元のファイル名を返す
    if not os.path.exists(fullpath):
        return fullpath
    counter += 1
    # 新しいファイル名を生成するまでループ
    while os.path.exists(fullpath):
        new_filename = f"{lang}.{font_name}.exp{counter}{ext}"
        fullpath = os.path.join(path, new_filename)
        counter += 1
    # 生成したユニークなファイル名を返す
    return fullpath


def create_unique_fullpath(filepath, receipts: list[Receipt], sheet_date=""):
    """
    指定されたファイルパスに対して、既存のファイルと重複しないユニークなファイルパスを生成します。
    既にファイルが存在する場合は、カウンタを付加して新しいファイル名を生成します。

    :param filepath: 生成するユニークなファイルパスの基本となるファイルパス
    :return: 既存のファイルと重複しないユニークなファイルパス。エラーが発生した場合は None を返す
    """
    try:
        # パスからディレクトリとファイル名を分離
        counter = 1
        _path, filename = os.path.split(filepath)
        base, extension = os.path.splitext(filename)
        # 新しいファイル名を生成する
        if len(receipts) <= 0 or sheet_date == "":
            return filepath
        new_base = sheet_date
        new_filename = f"{new_base}_{counter}{extension}"
        new_filepath = os.path.join(_path, new_filename)
        # 既存のファイルと重複しない場合は元のファイルパスを返す
        if not os.path.exists(new_filepath):
            return new_filepath
        counter += 1
        # 新しいファイルパスを生成するまでループ
        while True:
            new_filename = f"{new_base}_{counter}{extension}"
            new_filepath = os.path.join(_path, new_filename)

            # 生成したファイルパスが既存のファイルと重複しない場合
            if not os.path.exists(new_filepath):
                return new_filepath

            counter += 1

        # エラーメッセージを mainWindow の add_message を使って表示
    except Exception as e:
        msgBox(f"ユニークなファイルパスの生成中にエラーが発生しました: {e}", "エラー", icon_type=QMessageBox.Critical)
        exit(1)


def load_json_file(filename, file_desc="JSON file"):
    """
    指定されたJSONファイルを読み込む。

    :param filename: 読み込むファイルの名前
    :param file_desc: ファイルの説明（デフォルトは"JSON file"）
    :return: ファイルから読み込んだデータ、またはファイルが存在しない場合は空の辞書
    """
    # ファイルの存在確認
    if os.path.exists(filename):
        try:
            # ファイルを開いてJSONデータを読み込む
            with open(filename, "r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError as e:
            # JSONデコードエラーが発生した場合
            print(f"{file_desc}の読み込み中にエラーが発生しました: {e}")
            return
        except Exception as e:
            # その他のエラーが発生した場合
            print(f"{file_desc}の読み込みに失敗しました: {e}")
            return
    else:
        # ファイルが存在しない場合
        print(f"{file_desc}が見つかりません。")
        return


def save_json_file(filename, data):
    """
    指定されたデータをJSON形式でファイルに保存する。

    :param filename: 保存するファイルの名前
    :param data: JSONに変換して保存するデータ
    """
    try:
        # JSON形式の文字列に変換
        json_str = json.dumps(data, ensure_ascii=False, indent=4)
        # ファイルへの書き込み
        with open(filename, "w", encoding="utf-8") as file:
            file.write(json_str)
    except Exception as e:
        # エラーメッセージをMainWindowのテキストブラウザに表示
        print(f"JSONファイルの保存中にエラーが発生しました: {e}")


def set_exif(rec_man=None, receipts: list[Receipt] = None, filename: str = None, sheet_date=None, json_string: str = None, Mode: SaveMode = SaveMode.SAVE_NEW) -> None:
    if rec_man is not None:
        if len(rec_man.receipts) == 0 or rec_man.sheet_date == "":
            return rec_man.image_path

        filename, receipts, sheet_date = rec_man.image_path, rec_man.receipts, rec_man.sheet_date
        json_string = rec_man.get_json()
    elif receipts and filename and sheet_date and json_string:
        pass
    else:
        return
    new_filepath = create_unique_fullpath(filepath=filename, receipts=receipts, sheet_date=sheet_date)

    description = json_string.encode('utf-8')
    exif = exif_load(filename)
    exif['0th'][ImageIFD.ImageDescription] = description
    # 変更したEXIFデータをバイト列に変換
    exif_bytes = exif_dump(exif)
    # EXIFデータを画像に挿入し、新しいファイルとして保存
    insert(exif_bytes, filename, filename)

    if Mode == SaveMode.OVER_WRITE:
        return filename
    if rec_man:
        rec_man.image_path = new_filepath

    if filename != new_filepath:
        os.rename(filename, new_filepath)
    return new_filepath


def get_exif(filename: str) -> tuple[Optional[bool], Optional[str], Optional[list[Receipt]]]:
    Result = namedtuple('Result', ['result', 'sheet_date', 'receipt_data'])
    try:
        exif = exif_load(filename)
        description = exif['0th'][ImageIFD.ImageDescription]
        if is_json(description):
            exif_data = json.loads(description)
            if 'receipt_data' in exif_data:
                sheet_date = exif_data['sheet_date']
                receipts_arr = exif_data['receipt_data']
            elif 'sheet_date' in exif_data:
                sheet_date = exif_data['sheet_date']
                receipts_arr = None
            else:
                sheet_date = ""
                receipts_arr = exif_data

            receipt_data = []
            for a_data in receipts_arr:
                receipt = Receipt().create_receipt(a_data)
                receipt_data.append(receipt)
            return Result(True, sheet_date, receipt_data)

        elif description == '':
            receipt_data = []
            return Result(False, "", receipt_data)
        else:
            exif['0th'][ImageIFD.ImageDescription] = ''
            # 変更したEXIFデータをバイト列に変換
            exif_bytes = exif_dump(exif)
            # EXIFデータを画像に挿入し、新しいファイルとして保存
            insert(exif_bytes, filename, filename)
            receipt_data = []
            return Result(False, "", receipt_data)
    except Exception as e:
        if e.args[0] != 270:
            print(e)
        return Result(None, None, None)


def to_cv2_rotated_rect(self) -> Tuple[Tuple[float, float], Tuple[float, float], float]:
    return (self.center, self.size, self.angle)


def set_debug_mode(mode: bool):
    global DEBUG_MODE
    DEBUG_MODE = mode
    return None


def get_debug_mode():
    global DEBUG_MODE
    return DEBUG_MODE


def print_caller_info():
    if not get_debug_mode():
        return
    _stack = inspect.stack()
    caller = _stack[2]  # 呼び出し元の呼び出し元の情報を取得
    info = inspect.getframeinfo(caller[0])
    string = f"{info.function} が {_stack[1].function} を呼び出しました\n"
    print(string)
    return string
