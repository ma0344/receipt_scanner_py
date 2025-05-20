# -*- coding: utf-8 -*-
from re import sub, search, MULTILINE
from typing import Tuple
import numpy as np
from numpy import ndarray
from attridict import AttriDict
import cv2
import ImageProc


class RotatedRect:
    def __init__(self, center: Tuple[float, float], size: Tuple[float, float], angle: float):
        self.center = center
        self.size = size
        self.angle = angle

    def __eq__(self, other):
        if not isinstance(other, RotatedRect):
            return False
        return (self.center == other.center
                and self.size == other.size
                and self.angle == other.angle)

    def __deepcopy__(self, memo):
        return RotatedRect(self.center, self.size, self.angle)

    def to_cv2_rotated_rect(self) -> Tuple[Tuple[float, float], Tuple[float, float], float]:
        return (self.center, self.size, self.angle)


class Receipt:
    def __init__(self, rect: cv2.RotatedRect = None, date: str = "", supplyer_name: str = "", item_category: str = "", amount: int = 0, ocr: str = ""):
        self.date: str = date
        self.supplyer_name: str = supplyer_name
        self.item_category: str = item_category
        self.amount: int = amount
        self.rect: RotatedRect = rect  # RotateRectオブジェクト
        self.ocr_text: str = ocr
        self.receipt_image: ndarray = None

    def __eq__(self, other: 'Receipt'):
        if not isinstance(other, Receipt):
            return False
        return (self.date == other.date
                and self.supplyer_name == other.supplyer_name
                and self.item_category == other.item_category
                and self.amount == other.amount
                and self.rect == other.rect
                and self.ocr_text == other.ocr_text)
        # RotatedRectの比較にはRotatedRectクラスにも__eq__を実装する必要があります

    def __deepcopy__(self, memo):
        return Receipt(self.rect, self.date, self.supplyer_name, self.item_category, self.amount, self.ocr_text)

    def create_receipt(self, info):

        d = AttriDict(info)
        if 'suplyer' in info:
            receipt = Receipt(date=d.date, supplyer_name=d.suplyer, item_category=d.category, amount=d.amount, rect=d.rect, ocr=d.ocrt)
        elif 'supplyer' in info:
            receipt = Receipt(date=d.date, supplyer_name=d.supplyer, item_category=d.category, amount=d.amount, rect=d.rect, ocr=d.ocrt)
        else:
            rect = self.parse_rect_dic_to_rotatedrect(d.Rect)
            receipt = Receipt(date=d.Date, supplyer_name=d.Name, item_category=d.Text, amount=d.Payd, rect=rect, ocr=d.OCRT)
        return receipt

    def convert_rotatedrect_to_dic(self):
        rect = self.rect
        if hasattr(rect, 'center'):
            return
        rect_dic = {}
        rect_dic["center"] = (rect[0][0], rect[0][1])
        rect_dic["size"] = (rect[1][0], rect[1][1])
        rect_dic["angle"] = rect[2]
        self.rect = rect_dic

    def parse_rect_dic_to_rotatedrect(self, rect_dic: dict) -> RotatedRect:
        r = AttriDict(rect_dic)
        center = (r.Center.X, r.Center.Y)
        size = (r.Size.Width, r.Size.Height)
        angle = r.Angle
        return RotatedRect(center, size, angle)

    def add_ocr_text(self, ocr_text):
        self.ocr_text = ocr_text

    def calculate_sum(self, ocr_text, labels):
        numbers = []
        for label in labels:
            reglabel = fr'^{label}.*'
            match = search(reglabel, ocr_text, MULTILINE)
            if match:
                numbers.append(self.extract_number(match.group(), label))
        return sum(numbers)

    def calculate_direct(self, ocr_text, labels):
        for label in labels:
            reglabel = fr'^{label}.*'
            match = search(reglabel, ocr_text, MULTILINE)
            if match:
                return self.extract_number(match.group(), label)

        return 0

    def extract_number(self, text, label):
        label_deleted_text = sub(label, '', text)
        number_str = sub('[^0-9]', '', label_deleted_text)
        return int(number_str) if number_str else 0

    def get_receipt_image(self, sheet_image: np.ndarray):
        if self.rect:
            clopped_image = ImageProc.crop_image(mat_image=sheet_image, rect=self.rect)
        elif self.rect is None:
            self.rect = cv2.RotatedRect(center=(1, 1), size=(3, 3), angle=0)
            image = np.full((600, 300, 3), (255, 255, 255), np.uint8)
            cv2.rectangle(image, (0, 0), (300 - 1, 600 - 1), (0, 0, 0), thickness=3)
            clopped_image = cv2.rectangle()
        pixmap = ImageProc.mat_to_pixmap(clopped_image)
        return pixmap
