from PySide6.QtGui import QStandardItemModel, QStandardItem, QFont
from PySide6.QtCore import Qt, QItemSelectionModel, QModelIndex
from PySide6.QtWidgets import QTreeView
from Receipt import Receipt
import ImageProc
import numpy as np
import os
import cv2
from util import get_exif, set_exif, msgBox, print_caller_info, SaveMode, find_sheet_date, sort_rects, make_json, BooleanWatcher
from typing import List, Any


class ReceiptManager:
    def __init__(self, image_path: str, image: np.ndarray = None, main_window=None, model: QStandardItemModel = None):
        self.receipts: list[Receipt] = []
        self.sheet_date: str = ""
        self.current_index: int = 0
        self.current_receipt: Receipt = None
        self.image_path: str = image_path
        self.sheet_image: np.ndarray = image
        self.mainWindow: Any = main_window
        self.receipt_items_model: QStandardItemModel = model
        self.receiptList_model: QItemSelectionModel = self.mainWindow.receiptList_TreeView.selectionModel()
        self.updating_model: bool = False
        self.isReceipt_selected_watcher: BooleanWatcher = self.mainWindow.isReceipt_selected_watcher
        self.flags = self.mainWindow.flags

        if image_path != "":
            self.create_receipt_manager(image_path)

    def __len__(self):
        return len(self.receipts)

    def __eq__(self, other: list[Receipt]):
        self.receipts == other

    def clear(self):
        self.receipts.clear()
        self.current_index = 0
        self.image_path = None
        self.sheet_image = None

    def add_receipt(self, receipt: Receipt):
        self.receipts.append(receipt)

    def sheet_change(self, file_path):
        print_caller_info()
        self.receipts.clear()
        self.sheet_date = ""
        self.current_index = 0
        self.image_path = ""
        self.sheet_image = ""
        model = self.receipt_items_model
        if not os.path.isfile(file_path):
            return None
        exif = get_exif(file_path)
        self.image_path = file_path
        try:
            self.sheet_image = ImageProc.imread(self.image_path)
        except ValueError:
            msgBox("画像ファイルが読み込めませんでした。")
            return None
        finally:
            self.updating_model = True
            if exif.result is True:
                self.update_model(model, exif)
            elif exif.result is False:
                # 新規のシートを選択したときに領域を認識してReceiptManagerに追加・表示
                rectangles = ImageProc.get_crop_rects(self.sheet_image, self.mainWindow.sliders_value)
                sorted_rectangles = [] if not rectangles\
                    else rectangles if len(rectangles) == 1 \
                    else sort_rects(rectangles)

                for rect in sorted_rectangles:
                    self.add_receipt(Receipt(rect))

            _ = self.renew_model(self.receipts)
            self.updating_model = False
            return self

    def update_model(self, model: QStandardItemModel, exif):
        print_caller_info()
        model.removeRows(0, model.rowCount())
        receipts_data = sort_rects(exif.receipt_data)
        self.sheet_date = exif.sheet_date
        self.set_receipt_infos(receipts_data)

    def renew_model(self, receipts=None):
        model: QStandardItemModel = self.receipt_items_model
        model.removeRows(0, model.rowCount())
        model = self.remake_receipts_list_model(model, receipts)
        self.receipts = receipts
        self.isReceipt_selected_watcher.v = self.receiptList_model.hasSelection()
        return model

    def remake_receipts_list_model(self, model: QStandardItemModel, receipts: List[Receipt]):
        font1 = QFont()
        font1.setPointSize(12)
        font2 = QFont()
        font2.setPointSize(16)
        for receipt in receipts:
            category_item = QStandardItem(receipt.item_category)
            category_item.setTextAlignment(Qt.AlignCenter | Qt.AlignCenter)   # 中央揃え
            category_item.setFont(font1)
            supplyer_item = QStandardItem(receipt.supplyer_name)
            supplyer_item.setTextAlignment(Qt.AlignCenter | Qt.AlignCenter)  # 中央揃え
            supplyer_item.setFont(font1)

            amount_item = QStandardItem(str(receipt.amount))
            amount_item.setTextAlignment(Qt.AlignCenter | Qt.AlignRight)   # 右揃え
            amount_item.setFont(font2)
            model.appendRow([category_item, supplyer_item, amount_item])
        return model

    def remove(self, receipt: Receipt):
        treeView: QTreeView = self.mainWindow.receiptList_TreeView
        receipt_index = self.get_receipt_index(receipt)
        treeView.model().removeRow(receipt_index, parent=QModelIndex())
        self.receipts.remove(receipt)

    def get_sheet_image_pixpap(self):
        return ImageProc.mat_to_pixmap(self.sheet_image)

    def get_sheet_image_mat(self):
        return self.sheet_image

    def get_receipts(self) -> List[Receipt]:
        return self.receipts

    def set_receipt_infos(self, infos: list):
        # ReceiptManagerにinfosのレシートをすべて追加
        for info in infos:
            if isinstance(info, Receipt):
                receipt = info if isinstance(info, Receipt)\
                    else Receipt(rect=info) if isinstance(info, cv2.RotatedRect)\
                    else Receipt().create_receipt(info)
            self.add_receipt(receipt)

        self.receipts, self.sheet_date = find_sheet_date(self.get_receipts())

        # self.set_receipt_info_for_edit(self.receipts[0])

    def get_current_index(self) -> int:
        return self.receiptList_model.currentIndex().row()

    def get_receipt_index(self, receipt: Receipt) -> int:
        return self.receipts.index(receipt)

    def get_current_receipt(self) -> Receipt:
        if len(self.receipts) > 0:
            return self.receipts[self.receiptList_model.currentIndex().row()]

    def update_receipt(self, receipt: Receipt):
        self.receipts[self.current_index] = receipt
        self.renew_model(self.receipts)

    def set_current_receipt_property(self, property_name: str, value: Any):
        model: QStandardItemModel = self.receipt_items_model
        current_receipt: Receipt = self.get_current_receipt()
        if hasattr(current_receipt, property_name):
            setattr(current_receipt, property_name, value)

        column_idx = 0 if property_name == "item_category" else 1 if property_name == "supplyer_name" else 2 if property_name == "amount" else None
        if column_idx is not None and model is not None:
            item = model.item(self.receiptList_model.currentIndex().row(), column_idx)
            if item is not None:
                item.setText(str(value))
        elif property_name == "date":
            self.sheet_date = value
            for receipt in self.receipts:
                receipt.date = value
        elif property_name == "rect":
            items = [current_receipt.item_category, current_receipt.supplyer_name, current_receipt.amount]
            for i, item in enumerate(items, start=0):
                column_item = model.item(self.receiptList_model.selectedRows()[0].row(), i)
                column_item.setText(str(item))

        self.mainWindow.realtime_selected_sheet = self.receipts

    def set_current_receipt(self, indexNo: int):
        self.current_receipt = self.receipts[indexNo]
        self.current_index = indexNo

    def next_receipt(self) -> int:
        self.next_index = (self.current_index + 1) % len(self.receipts)
        return self.next_index, self.receipts[self.current_index]

    def previous_receipt(self) -> int:
        self.current_index = (self.current_index - 1) % len(self.receipts)
        return self.current_index, self.receipts[self.current_index]

    def create_receipt_manager(self, item_path):
        if os.path.isfile(item_path):
            exif = get_exif(item_path)
            self.image_path = item_path
            try:
                self.sheet_image = ImageProc.imread(self.image_path)
            except ValueError:
                msgBox("画像ファイルが読み込めませんでした。")
                return None
            finally:
                if exif.result and self.flags.AUTO_MODE is not True:
                    receipts_data = sort_rects(exif.receipt_data)
                    self.set_receipt_infos(receipts_data)

                elif not exif.result or self.flags.AUTO_MODE:
                    # 新規のシートを選択したときに領域を認識してReceiptManagerに追加・表示
                    rectangles = ImageProc.get_crop_rects(self.sheet_image, self.mainWindow.sliders_value)
                    if not rectangles:
                        return
                    sorted_rectangles = rectangles if len(rectangles) == 1 else sort_rects(rectangles)
                    for rect in sorted_rectangles:
                        self.add_receipt(Receipt(rect))
                return self
        else:
            return None

    def get_json(self) -> str:
        receipts = self.get_receipts()
        if len(receipts) == 0:
            return ""

        return make_json(sheet_date=self.sheet_date, receipts=receipts)

    def setExif(self, Mode: SaveMode = SaveMode.SAVE_NEW):

        self.receipts, self.sheet_date = find_sheet_date(self.get_receipts())
        new_filename = set_exif(self, Mode=Mode)
        return new_filename
