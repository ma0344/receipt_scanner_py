# -*- coding: utf-8 -*-
from os import getcwd, chdir, remove
import os
import sys
import cv2
from shutil import rmtree
from copy import deepcopy
from locale import setlocale, LC_ALL
from asyncio import run
from send2trash import send2trash
from traceback import format_exception
import numpy as np
from typing import Any
from datetime import datetime
from PySide6.QtGui import QStandardItemModel, QPixmap
from PySide6.QtCore import Qt, Slot, QEvent, QItemSelectionModel, QModelIndex, QPropertyAnimation, QDir, QTimer
from PySide6.QtWidgets import QMessageBox, QApplication, QMainWindow, QProgressBar, QComboBox, QFileDialog, QLabel, QAbstractItemView, QTreeView, QFileSystemModel, QPushButton, QCalendarWidget, QDockWidget
from google.cloud import vision
from ui_MainWindow import Ui_MainWindow
from SupplyerWindow import SubWindow
from Receipt import Receipt, RotatedRect
import ui_settings
import ImageProc
from ImageProc import SlidersValue
import accCreator
import OCR
from ReceiptManager import ReceiptManager
from OCR import SheetProcessThread, start_async_ocr, tess_OCR, get_tess_command
import util
from util import SaveMode, Point, msgBox, scaled_point_to_original_point as scldToOrg, convert_to_rotated_rect, parse_date_string, set_receipt_info_from_ocr, conv_date_string, BooleanWatcher, print_caller_info, load_json_file, save_json_file, ImageType, MoveTo

setlocale(LC_ALL, 'ja_JP.UTF-8')


class flags:
    FILE_SELECTION = False
    DEBUG_MODE = False
    AUTO_MODE = False


class MainWindow(QMainWindow, Ui_MainWindow):

    original_SheetPixmap = None
    original_receiptPixmap = None

    def __init__(self):
        super(MainWindow, self).__init__()
        self.flags = flags()
        util.set_debug_mode(self.flags.DEBUG_MODE)
        self.script_dir = getcwd()

        if getattr(sys, 'frozen', False):
            log_file = open(os.path.join(self.script_dir, 'error.log'), 'a')
            sys.stdout = log_file
            sys.stderr = log_file

        self.data_dir = load_json_file(os.path.join(self.script_dir, "settings.json"), "Settings file")
        if self.data_dir is None:
            self.data_dir = self.script_dir

        self.installEventFilter(self)
        self.setupUi(self)
        self.sliders_value = SlidersValue(0, 0, 0)
        self.temporary_receipt = None
        self.sheet_process_finished = 0
        self.process_sheet_count = 0
        self.top_sheet_path = None
        self.new_top_sheet_path = None
        self.selected_index = None
        self.receipt_count = 0
        self.sheet_process_thread = []
        self.isShiftPressed = False
        self.dragThreshold = 3
        self.points: list[Point] = []
        self.start_point = None
        self.start_pos = None
        self.click_point = None
        self.isDragMode = False
        self.isSelecting = False
        self.isClickMode = False
        self.releace_point = None
        self.supplyer_edit = False
        self.supplyer_dic = None
        self.current_org_receipts = None
        self.realtime_selected_sheet = None
        self.isOcrOnly = False
        self.selected_sheet_neme = None
        self.sheet_save_status = None
        self.receiptList_model: QStandardItemModel = ui_settings.apply_settings(self)
        self.fileListModel: QFileSystemModel = self.file_TreeView.model()
        self.fileSelectionModel: QItemSelectionModel = self.file_TreeView.selectionModel()
        self.isReceipt_selected_watcher = BooleanWatcher(False, self.Receipt_select)
        self.receipt_manager = ReceiptManager(image=None, image_path="", main_window=self, model=self.receiptList_model)
        self.receipts = self.receipt_manager.receipts
        self.buttons_and_DelButton_switch_to(False)
        self.add_and_update_Button_switch_to(False)
        self.isTemp_selected_watcher = BooleanWatcher(False, self.Temp_select)
        self.after_Rect_selecting = BooleanWatcher(False, self.add_or_update_selecte_rect)
        self.client: vision.ImageAnnotatorClient = OCR.get_service(self.script_dir)

    def closeEvent(self, event):
        # ウィンドウが閉じる時に実行したいコードをここに書く
        save_json_file(os.path.join(self.script_dir, "settings.json"), self.directory_LineEdit.text())
        # イベントを続行する（ウィンドウを閉じる）
        event.accept()

    def eventFilter(self, source, event):
        event_type = event.type()
        event_type_name = self.get_event_type_name(event_type)
        if event_type_name not in ["HoverMove", "NonClientAreaMouseMove", "Paint", "UpdateRequest", "CursorChange"]:
            pass
        if event.type() == QEvent.KeyPress:
            if source == self.receiptList_TreeView:
                if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                    self.amount_LineEdit.setFocus()
            elif source.focusWidget().objectName() == 'file_TreeView':
                if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                    dock: QDockWidget = self.accounting_DockWidget
                    self.receiptList_TreeView.setFocus()
                    if dock.isFloating:
                        self.accounting_DockWidget.activateWindow()

        if event.type() == QEvent.MouseButtonPress:
            treeView: QTreeView = source.parent()
            if treeView is None:
                return super().eventFilter(source, event)
            if treeView.objectName() != 'file_TreeView':
                pass
            if treeView.objectName() != 'receiptList_TreeView':
                return super().eventFilter(source, event)
            index = treeView.indexAt(event.position().toPoint())
            if not index.isValid():
                treeView.clearSelection()
                treeView.selectionModel().setCurrentIndex(QModelIndex(), QItemSelectionModel.Clear)
            if self.isSelecting and not source.objectName() == "sheetImage_Label":
                self.selection_clear()
                self.set_sheet_image(self.receipt_manager.sheet_image)
                self.isTemp_selected_watcher.v = False

            if event.modifiers() & Qt.ShiftModifier:
                self.isShiftPressed = True
            else:
                self.isShiftPressed = False

        return super().eventFilter(source, event)

    def blinking(self):
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(150)  # アニメーションの持続時間をミリ秒で設定
        self.animation.setStartValue(1)  # 開始時の不透明度
        self.animation.setEndValue(0.7)    # 終了時の不透明度
        self.animation.setLoopCount(2)   # ループ回数（点滅回数の2倍を設定）
        self.animation.finished.connect(self.onAnimationFinished)  # アニメーション完了時の処理
        self.animation.start()

    def onAnimationFinished(self):
        self.setWindowOpacity(1)  # 不透明度を元に戻す

    def Receipt_select(self, isReceipt_selected_watcher):
        switch = isReceipt_selected_watcher.v
        self.buttons_and_DelButton_switch_to(switch)

    def Temp_select(self, isTemp_selected_watcher):
        switch = isTemp_selected_watcher.v
        self.add_and_update_Button_switch_to(switch)
        self.buttons_and_DelButton_switch_to(not switch)
        pass

    def add_or_update_selecte_rect(self, switch):
        self.add_and_update_Button_switch_to(switch)

    def add_and_update_Button_switch_to(self, switch: bool):
        add_and_update_Button: list[QPushButton] = [self.add_Button, self.update_Button]
        for button in add_and_update_Button:
            button.setEnabled(switch)

    def buttons_and_DelButton_switch_to(self, switch: bool):
        self.switch_enabled_of_widgets_in_layout(self.Date_Layout, switch)
        self.switch_enabled_of_widgets_in_layout(self.receiptEditor_QVBoxLayout, switch)
        self.switch_enabled_of_widgets_in_layout(self.category_Buttons, switch)
        self.delReceipt_Button.setEnabled(switch)
        if switch is False:
            self.clear_editor()

    def is_sheet_edited(self):
        initial = self.receipt_manager.receipts
        original = self.current_org_receipts
        edited = original != initial

        if edited is True:
            pass
            return edited
        return edited

    def clear_editor(self):
        self.setEditorValueFlag = True
        self.date_lineEdit.setText(util.conv_date_string(datetime.today()))
        self.category_ComboBox.setCurrentText("")
        self.supplyerComboBox.setCurrentText("")
        self.amount_LineEdit.setText("")
        self.ocrString_textBrowser.setText("")
        self.setEditorValueFlag = False

    def clear_image(self, imageType: ImageType = ImageType.Both):
        if imageType == ImageType.Sheet or imageType == ImageType.Both:
            self.sheetImage_Label.original_SheetPixmap = None
            self.sheetImage_Label.setPixmap(QPixmap())
        if imageType == ImageType.Receipt or imageType == ImageType.Both:
            self.receiptImage_Label.original_receiptPix = None
            self.receiptImage_Label.setPixmap(QPixmap())
            if imageType == ImageType.Receipt:
                self.set_sheet_image(self.receipt_manager.sheet_image)

    def clear(self):
        self.buttons_and_DelButton_switch_to(False)
        self.add_and_update_Button_switch_to(False)
        self.clear_editor()
        self.clear_image()

    def switch_enabled_of_widgets_in_layout(self, layout, bool: bool = None):
        if bool is None:
            bool = not layout.isEnabled()
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget is not None:
                boolean = bool if bool is not None else not widget.isEnabled()
                widget.setEnabled(boolean)
            else:
                # レイアウト内のレイアウトに対する処理
                child_layout = layout.itemAt(i).layout()
                if child_layout is not None:
                    self.switch_enabled_of_widgets_in_layout(child_layout, bool)

    def current_row_changed(self):
        index = self.file_TreeView.currentIndex()
        self.file_TreeView.scrollTo(index, QAbstractItemView.EnsureVisible)

    def get_event_type_name(self, event_type):
        for name in dir(QEvent):
            if name.startswith('__'):
                continue
            if getattr(QEvent, name) == event_type:
                return name
        return "Unknown Event"

    def selection_clear(self):
        self.points: list[Point] = []
        self.start_point = None
        self.start_pos = None
        self.click_point = None
        self.isDragMode = False
        self.isSelecting = False
        self.isClickMode = False

    def set_sheet_image(self, image: Any):
        if isinstance(image, np.ndarray):
            pixmap = ImageProc.mat_to_pixmap(image)
        else:
            pixmap = image
        self.sheetImage_Label.original_SheetPixmap = pixmap
        self.original_SheetPixmap = pixmap
        self.sheetImage_Label.adjust_SheetImageSize()
        return

    def on_finished_receipt(self):
        pb: QProgressBar = self.progressBar
        pb.setValue(pb.value() + 1)

    def on_sheet_processing_finished(self, object):
        saved_filename, original_filename = object
        if original_filename == self.top_sheet_path:
            self.new_top_sheet_path = saved_filename
        self.sheet_process_finished += 1
        model: QFileSystemModel = self.file_TreeView.model()
        if self.sheet_process_finished == self.process_sheet_count:
            # すべてのサブスレッドが終了した場合
            self.selected_index = model.index(self.new_top_sheet_path)
            if self.selected_index.isValid():
                model.setRootPath("")
                model.setRootPath(QDir.rootPath())

            def fileSelect_emit():
                model: QFileSystemModel = self.file_TreeView.model()
                tree: QTreeView = self.file_TreeView
                self.selected_index = model.index(self.new_top_sheet_path)
                tree.scrollTo(self.selected_index)
                tree.setCurrentIndex(self.selected_index)
                self.fileSelection_changed()

            QTimer.singleShot(50, fileSelect_emit)
            self.isOcrOnly = False

    def on_sheet_processing_started(self, Object):
        self.receipt_count += Object
        self.progressBar.setMaximum(self.receipt_count)

    def set_receipt_info_for_edit(self, receipt: Receipt):
        print_caller_info()
        self.setEditorValueFlag = True
        self.date_lineEdit.setText(receipt.date)
        calendar_date = parse_date_string(receipt.date)\
            if receipt.date != ""\
            else parse_date_string(self.receipt_manager.sheet_date)\
            if self.receipt_manager.sheet_date != ""\
            else datetime.today()

        self.calendarWidget.setSelectedDate(calendar_date)
        self.amount_LineEdit.setText(str(receipt.amount) if receipt.amount else '')
        self.category_ComboBox.setCurrentText(receipt.item_category.replace('ここっち ', ''))
        self.supplyerComboBox.setCurrentText(receipt.supplyer_name)
        self.ocrString_textBrowser.setText(receipt.ocr_text)
        self.setEditorValueFlag = False

# ------------------- Receipt Area cropping レシート範囲手動切り抜き関連 -------------------

    def sheetImage_mouse_button_pressed(self, event):
        if self.receipt_manager.sheet_image is None:
            return
        if event.button() == Qt.RightButton:
            self.selection_clear()
            self.isTemp_selected_watcher.v = False
            accSelModel: QItemSelectionModel = self.receiptList_TreeView.selectionModel()
            if len(accSelModel.selectedRows()) > 0:
                selectedRow = accSelModel.selectedRows()
                self.set_image_and_editArea(selectedRow)
                self.buttons_and_DelButton_switch_to(True)
                self.isReceipt_selected_watcher.v = True
                return
            self.buttons_and_DelButton_switch_to(False)
            self.set_sheet_image(self.receipt_manager.sheet_image)
            return
        point, isInArea = scldToOrg(self.sheetImage_Label, event)
        if self.isSelecting is False and isInArea is False:
            return
        self.isSelecting = True
        self.click_point = point
        self.start_pos = event.position().toPoint()
        self.releace_point = None

    def sheetImage_mouse_button_released(self, event):
        if self.receipt_manager.sheet_image is None:
            return
        point, _ = scldToOrg(self.sheetImage_Label, event)

        self.releace_point = point
        image = self.receipt_manager.sheet_image.copy()
        if not self.isDragMode:
            if self.isSelecting and not self.isClickMode and len(self.points) == 0:
                self.isClickMode = True
                self.points.append(point)
                self.start_point = point
                image = cv2.line(image, self.points[0].pos(), point.pos(), (0, 0, 255), 2)
                self.buttons_and_DelButton_switch_to(False)
            elif self.isSelecting and self.isClickMode and len(self.points) == 1:
                self.isClickMode = True
                self.points.append(point)
                image = cv2.line(image, self.points[0].pos(), self.points[1].pos(), (0, 0, 255), 2)
            elif self.isSelecting and self.isClickMode and len(self.points) == 2:
                self.isClickMode = True
                rotated_rect = self.points_to_rotated_rect(self.points, self.click_point)
                image = ImageProc.get_rect_draw_image(image, [rotated_rect])
                self.temporary_receipt = Receipt(rotated_rect)
                self.set_receipt_image(self.temporary_receipt)
                self.isTemp_selected_watcher.v = True
                if self.temporary_receipt is None:
                    self.set_sheet_image(self.receipt_manager.sheet_image)
                self.selection_clear()
        elif self.isDragMode:
            image = cv2.rectangle(image, self.start_point.pos(), point.pos(), (0, 0, 255), 2)
            self.set_sheet_image(ImageProc.mat_to_pixmap(image))
            np_points = np.array([self.start_point.pos(), (point.x, self.start_point.y), point.pos(), (self.start_point.x, point.y)])
            rotated_rect = convert_to_rotated_rect(cv2.minAreaRect(np_points))
            self.temporary_receipt = Receipt(rotated_rect)
            self.set_receipt_image(self.temporary_receipt)
            self.isTemp_selected_watcher.v = True
            self.selection_clear()

    def sheetImage_mouse_moved(self, event):
        if self.receipt_manager.sheet_image is None:
            return
        point, _ = scldToOrg(self.sheetImage_Label, event)
        if self.isSelecting:
            if self.isClickMode and not self.isDragMode:
                image = self.receipt_manager.sheet_image.copy()
                if len(self.points) == 1:
                    image = cv2.line(image, self.points[0].pos(), point.pos(), (0, 0, 255), 2)
                    self.set_sheet_image(ImageProc.mat_to_pixmap(image))

                elif len(self.points) == 2:
                    temp_points = self.points.copy()
                    rotated_rect: RotatedRect = self.points_to_rotated_rect(temp_points, point)
                    image = ImageProc.get_rect_draw_image(image, [rotated_rect])
                    self.set_sheet_image(ImageProc.mat_to_pixmap(image))
                return
            if not self.isDragMode and not self.isClickMode and (event.position().toPoint() - self.start_pos).manhattanLength() > self.dragThreshold and not self.releace_point:
                self.start_point = self.click_point
                self.isDragMode = True
                self.isClickMode = False
            if self.isDragMode:
                image = self.receipt_manager.sheet_image.copy()
                image = cv2.rectangle(image, self.start_point.pos(), point.pos(), (0, 0, 255), 2)
                self.set_sheet_image(ImageProc.mat_to_pixmap(image))

    def points_to_rotated_rect(self, points, point):
        # ポイントAとB（numpy配列として）
        pointA = np.array([points[0].x, points[0].y])
        pointB = np.array([points[1].x, points[1].y])
        currentPoint = np.array([point.x, point.y])

        # A-Bベクトルを計算
        vectorAB = pointB - pointA

        # ベクトルABを正規化
        vectorAB_normalized = vectorAB / np.linalg.norm(vectorAB)

        # ベクトルABに垂直なベクトルを作成（ABベクトルを右に90度回転）
        vectorPerpendicular = np.array([-vectorAB_normalized[1], vectorAB_normalized[0]])

        # マウスポインタから辺ABに対して垂直な線上のBからの距離を計算
        vectorMouseB = currentPoint - pointB
        distanceBC = np.dot(vectorMouseB, vectorPerpendicular)

        # 辺BCのC点を計算
        pointC = pointB + vectorPerpendicular * distanceBC

        # 辺ADのD点を計算（A点からC点へのベクトルを引いて）
        pointD = pointA + vectorPerpendicular * distanceBC

        # 結果をリストに追加（QtのQPointに変換が必要な場合は適宜変換してください）
        points.append(Point(int(pointC[0]), int(pointC[1])))
        points.append(Point(int(pointD[0]), int(pointD[1])))
        np_points = np.array([points[0].pos(), points[1].pos(), points[2].pos(), points[3].pos()])
        rotatedrect = cv2.minAreaRect(np.intp(np_points))
        rotated_rect = convert_to_rotated_rect(rotatedrect)

        return rotated_rect

# ------------------- sheetPeocess_DockWIdget 取込処理ドッグウィジェット-------------------

    def update_line_edit(self, value, target):
        target.setText(str(value))
        self.sliders_value.val1 = self.value1_Slider.value()
        self.sliders_value.val2 = self.value2_Slider.value()
        self.sliders_value.val3 = self.value3_Slider.value()

    def update_slider(self, value, target):
        if value:
            # LineEditの値を整数に変換してからスライダーに設定
            target.setValue(int(value))

    @Slot()
    def autoButton_clicked(self, sheetPaths=None):
        # GUIからシート画像のPathリストを取得
        self.flags.AUTO_MODE = True
        # 選択されているファイルのパスリストの作成
        sheet_paths = sheetPaths if sheetPaths is not None else get_selected_sheet_paths()
        self.top_sheet_path = sheet_paths[0]
        self.sheet_process_finished = 0
        self.receipt_count = 0
        self.process_sheet_count = len(sheet_paths)
        self.progressBar.setRange(0, 0)
        self.progressBar.setValue(0)
        self.process_sheet_count = len(sheet_paths)
        for sheet_path in sheet_paths:
            # パスから新たなReceiptManagerインスタンスを作成
            thread = SheetProcessThread(self, sheet_path, self.isOcrOnly)
            thread.finished.connect(self.on_sheet_processing_finished)
            thread.started.connect(self.on_sheet_processing_started)
            thread.on_finished_ocr.connect(self.on_finished_receipt)
            thread.start()
            self.sheet_process_thread.append(thread)

    @Slot()
    def manualButton_clicked(self):
        file_paths = get_selected_sheet_paths()
        for file_path in file_paths:
            if file_path is not None:
                receipts = run(start_async_ocr(image_path=file_path, supplyer_dic=self.supplyer_dic, slider_values=self.sliders_value))
            if receipts is not None:

                pass

    @Slot()
    def testButton_clicked(self):
        # file_TreeViewで選択されているアイテムをfiles変数に格納

        file_path = get_selected_sheet_paths()
        if file_path is not None:
            if isinstance(file_path, list):
                file_path = file_path[0]
            get_proc_image = self.imageCheck_Button.isChecked()
            mat = ImageProc.get_image(file_path, self.sliders_value, get_proc_image)
            # filesのアイテム数を表示
            self.set_sheet_image(mat)
        return

# ------------------- fileList_DockWIdget ファイルリストドッグウィジェット-------------------

    def ask_save(self):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Question)
        msgBox.setText("変更は保存されていません。よろしいですか？")
        msgBox.setWindowTitle("確認")
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)

        # ボタンにラベルを設定する（オプション）
        msgBox.button(QMessageBox.Yes).setText("保存")
        msgBox.button(QMessageBox.No).setText("続行")
        msgBox.button(QMessageBox.Cancel).setText("キャンセル")

        msgBox.setDefaultButton(QMessageBox.No)
        returnValue = msgBox.exec()
        return returnValue

    def save_if_edited(self):
        if self.current_org_receipts is not None and self.sheet_save_status is False:
            answer = self.ask_save()
            if answer == QMessageBox.Yes:
                self.saveButton_clicked()
            if answer != QMessageBox.Cancel:
                self.sheet_save_status = True
            return answer

    @Slot()
    def fileSelection_changed(self):  # 複数選択の場合も最初のアイテムの画像を表示する
        print_caller_info()
        if self.is_sheet_edited():
            if self.save_if_edited() == QMessageBox.Cancel:
                treeView = self.file_TreeView
                treeView.selectionModel().blockSignals(True)
                treeView.setCurrentIndex(treeView.model().index(self.receipt_manager.image_path))
                treeView.selectionModel().blockSignals(False)
                return
        selected_path = self.get_path()
        if selected_path is None:
            return
        elif os.path.isdir(selected_path):
            self.directory_selected(selected_path)
            return
        self.set_sheet_and_receipt(selected_path)
        self.focus_amount_line_edit()

    def set_sheet_and_receipt(self, filepath):
        print_caller_info()
        self.sheet_save_status = False
        self.receipt_manager.sheet_change(filepath)
        self.set_sheet_image(ImageProc.mat_to_pixmap(self.receipt_manager.sheet_image))

        model = self.receipt_manager.receipt_items_model
        self.current_org_receipts = deepcopy(self.receipt_manager.receipts)
        if self.isReceipt_selected_watcher.v is False:
            self.receiptsList_model_update(model)
        self.isReceipt_selected_watcher.v = self.receiptList_TreeView.selectionModel().hasSelection()

    def get_path(self):
        print_caller_info()
        fileListModel: QFileSystemModel = self.fileListModel
        selectionModel: QItemSelectionModel = self.file_TreeView.selectionModel()
        if selectionModel.selectedRows() is None:
            return None
        return_path = next((fileListModel.filePath(path) for path in
                            selectionModel.selectedRows() if os.path.isfile(fileListModel.filePath(path))), None)
        if return_path is None:
            return_path = next((fileListModel.filePath(path) for path in selectionModel.selectedRows() if os.path.isdir(fileListModel.filePath(path))), None)
            if return_path is None:
                return None
        return return_path

    def directory_selected(self, dirPath):
        print_caller_info()
        self.directory_LineEdit.setText(dirPath)
        chdir(self.directory_LineEdit.text())
        self.clear()
        self.receipt_manager.clear()
        self.receipt_manager.receipt_items_model.removeRows(0, self.receipt_manager.receipt_items_model.rowCount())
        self.isReceipt_selected_watcher.v = False
        self.current_org_receipts = None

    def focus_amount_line_edit(self):
        print_caller_info()
        self.amount_LineEdit.setFocus()
        self.amount_LineEdit.selectAll()

    def receiptsList_model_update(self, model: QStandardItemModel):
        print_caller_info()
        if model is not None and self.receipts.__len__() > 0:
            receiptList_model: QItemSelectionModel = self.receiptList_TreeView.selectionModel()
            index = model.index(0, 0)
            self.flags.FILE_SELECTION = True
            receiptList_model.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
            self.receipt_manager.set_current_receipt(0)
            receiptList_model.setCurrentIndex(index, QItemSelectionModel.Current)
            self.flags.FILE_SELECTION = False

    def directory_line_edit_changed(self):
        if not self.directory_LineEdit.text():
            return
        if not os.path.isdir(self.directory_LineEdit.text()):
            msgBox('ディレクトリが存在しません', 'エラー')
            self.directory_LineEdit.setText(getcwd())
            return
        chdir(self.directory_LineEdit.text())
        fileListModel: QFileSystemModel = self.fileListModel
        tree: QTreeView = self.file_TreeView
        current_index = fileListModel.index(self.directory_LineEdit.text())
        tree.setCurrentIndex(current_index)
        tree.scrollTo(current_index)
        tree.setFocus()

    @Slot()
    def folderSelectButton_clicked(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:  # ユーザーがディレクトリを選択した場合
            # self.directory_LineEdit.setText(directory)
            self.directory_line_edit_changed()

    def select_sheet(self, direction: util.MoveTo):
        print_caller_info()
        """
        指定された方向に基づいてシートを選択します。

        Parameters:
        - direction (str): 'prev'  または 'next'  を指定します。
        """
        tree: QTreeView = self.file_TreeView
        current_indexes: QModelIndex = tree.selectionModel().currentIndex()

        if direction == util.MoveTo.Previous:
            index = tree.indexAbove(current_indexes)
        elif direction == util.MoveTo.Next:
            index = tree.indexBelow(current_indexes)
        else:
            raise ValueError("Invalid direction. Must be 'prev' or 'next'.")

        if index.isValid():
            if self.is_sheet_edited():
                if self.save_if_edited() == QMessageBox.Cancel:
                    return
            self.sheet_save_status = True
            tree.selectionModel().select(index, QItemSelectionModel.ClearAndSelect)
            tree.setCurrentIndex(index)
            self.sheet_save_status = False

    @Slot()
    def prevSheetButton_clicked(self):
        self.select_sheet(MoveTo.Previous)

    @Slot()
    def nextSheetButton_clicked(self):
        self.select_sheet(MoveTo.Next)

    @Slot()
    def deleteFileButton_clicked(self):
        file_paths = get_selected_sheet_paths()
        if file_paths is not None:
            files_count = len(file_paths)
            delete = self.isShiftPressed
            msg = '完全に' if delete else ''
            if files_count == 1:
                answer = msgBox(f'{file_paths[0]}を{msg}削除しますか？', '削除', QMessageBox.Question, QMessageBox.Yes | QMessageBox.No)
            elif files_count > 1:
                answer = msgBox(f'{files_count}個のファイルを{msg}削除しますか？', '削除', QMessageBox.Question, QMessageBox.Yes | QMessageBox.No)
            if answer == QMessageBox.No:
                return
            for filePath in file_paths:
                filePath = os.path.normpath(filePath)
                try:
                    if delete:
                        if os.path.isdir(filePath):
                            rmtree(filePath)
                        elif os.path.isfile(filePath):
                            remove(filePath)
                    else:
                        send2trash.send2trash(filePath)
                except Exception as e:
                    print(f"'{filePath}'の削除中にエラーが発生しました: {e}")
            if files_count == 1:
                msgBox(f'{filePath}を{msg}削除しました', '削除')
            elif files_count > 1:
                msgBox(f'{files_count}個のファイルを{msg}削除しました', '削除')
            label: QLabel = self.sheetImage_Label
            label.setPixmap(QPixmap())
            self.receipt_manager.clear()
            self.sheetImage_Label.original_SheetPixmap = None

    @Slot()
    def makeCSVButton_clicked(self):
        acc_creator = accCreator.AccCreator(get_selected_sheet_paths())
        csv_filename, csv_str = acc_creator.accCreate()
        if csv_filename is not None:
            if csv_str is not None:
                msgBox(f'{csv_filename}を作成しました', '作成')
                with open(csv_filename, 'w', encoding='shift_jis') as f:
                    f.write(csv_str)

# ------------------- receiptImage_DockWIdget レシート画像ドッグウィジェット-------------------

    def adjust_ReceiptImageSize(self):
        if self.receiptImage_DockWidget.original_receiptPix:
            resized_pixmap = self.receiptImage_DockWidget.original_receiptPix.scaled(self.receiptImage_Label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.receiptImage_Label.setPixmap(resized_pixmap)

    def set_receipt_image(self, receipt: Receipt):
        pixmap = receipt.get_receipt_image(self.receipt_manager.sheet_image)
        if pixmap is None:
            return
        self.original_receiptPixmap = pixmap
        self.receiptImage_DockWidget.original_receiptPix = pixmap
        self.adjust_ReceiptImageSize()
        return

    @Slot()
    def reOcrButton_clicked(self):
        receipt: Receipt = self.receipt_manager.get_current_receipt()
        if self.original_receiptPixmap:
            image = ImageProc.pixmap_to_mat(self.original_receiptPixmap)
            tess_command = get_tess_command()
            result = tess_OCR(img=image, tess_command=tess_command)
            if result != "":
                receipt.ocr_text = result
                receipt = set_receipt_info_from_ocr(receipt, self.supplyer_dic)
            self.ocrString_textBrowser.setText(result)
            mainWindow.receipt_manager.update_receipt(receipt)
            self.set_receipt_info_for_edit(receipt)

    @Slot()
    def prevReceiptButton_clicked(self):
        self.change_receipt(MoveTo.Previous)

    @Slot()
    def nextReceiptButton_clicked(self):
        self.change_receipt(MoveTo.Next)

    def change_receipt(self, direction: MoveTo):
        if direction not in [MoveTo.Next, MoveTo.Previous]:
            return

        if direction == MoveTo.Previous:
            get_receipt_func = self.receipt_manager.previous_receipt
            def next_index_num(): return len(self.receipt_manager.receipts) - 1
            change_sheet_func = self.prevSheetButton_clicked
        else:
            get_receipt_func = self.receipt_manager.next_receipt
            def next_index_num(): return 0
            change_sheet_func = self.nextSheetButton_clicked

        if len(self.receipt_manager.receipts) > 0:
            index_num, receipt = get_receipt_func()
            if index_num == next_index_num():
                if self.is_sheet_edited():
                    if self.save_if_edited() == QMessageBox.Cancel:
                        index_num = self.receipt_manager.current_index if direction == MoveTo.Next else 0
                        self.update_current_receipt(index_num)
                        return
                change_sheet_func()
                tree = self.receiptList_TreeView
                index_num = next_index_num()
                item = tree.model().index(index_num, 0)
                if not item.isValid():
                    return
                self.update_current_receipt(index_num)
                return

        else:
            change_sheet_func()
            index_num = next_index_num()
            self.update_current_receipt(index_num)
            return

        if index_num is not None:
            self.select_receipt(index_num)

    def update_current_receipt(self, index_num):
        self.receipt_manager.set_current_receipt(index_num)
        self.receipt_manager.current_index = index_num
        self.select_receipt(index_num)

    def select_receipt(self, receipt_index):
        if len(self.receipt_manager.receipts) == 0:
            return
        receipt = self.receipt_manager.receipts[receipt_index]
        self.receipt_manager.set_current_receipt(receipt_index)
        self.set_receipt_info_for_edit(receipt)
        accTree: QTreeView = self.receiptList_TreeView
        model = accTree.model()
        index = model.index(receipt_index, 0)
        accTree.setCurrentIndex(index)

# ------------------- ocrText_DockWIdget OCRテキストドッグウィジェット-------------------

    def debug(self, text: str):
        mainWindow.ocrString_textBrowser.setText(text)
        return

# ------------------- accounting_DockWIdget 記帳ドッグウィジェット-------------------

    @Slot()
    def receiptListSelection_changed(self):
        print_caller_info()
        receiptSelectionModel: QItemSelectionModel = self.receiptList_TreeView.selectionModel()
        if self.receipt_manager.updating_model:
            return
        selected_indexes = receiptSelectionModel.selectedRows()
        if not selected_indexes:
            receiptSelectionModel.clearSelection()
            self.clear_editor()
            self.clear_image(imageType=ImageType.Receipt)
            self.isReceipt_selected_watcher.v = False
            return
        row_index = receiptSelectionModel.currentIndex().row()
        self.receipt_manager.set_current_receipt(row_index)
        self.set_image_and_editArea(selected_indexes)

    def set_image_and_editArea(self, selected_indexes):
        print_caller_info()
        self.isReceipt_selected_watcher.v = True
        index = selected_indexes[0].row()
        receipt = self.receipt_manager.receipts[index]
        if receipt is None:
            return
        self.set_receipt_image(receipt)

        self.receipt_manager.set_current_receipt(index)
        self.set_receipt_info_for_edit(receipt)

        self.updating_model = False
        sheet_image = ImageProc.get_rect_draw_image(self.receipt_manager.sheet_image, [receipt.rect])
        self.set_sheet_image(sheet_image)

    @Slot()
    def calendarClicked(self, value: datetime.date = None):
        if not isinstance(self.receipt_manager, ReceiptManager):
            return
        if len(self.receipt_manager.receipts) == 0:
            return
        calendar: QCalendarWidget = self.calendarWidget
        selected_date: datetime.date = calendar.selectedDate().toPython()
        if value is None:
            value = selected_date
        if selected_date is None:
            return
        self.date_lineEdit.blockSignals(True)
        self.date_lineEdit.setText(util.conv_date_string(selected_date))
        self.date_lineEdit.blockSignals(False)
        self.receipt_manager.set_current_receipt_property("date", self.date_lineEdit.text())

    @Slot()
    def dateLineEedit_value_change_finished(self):

        if self.date_lineEdit.text() == '' or self.setEditorValueFlag:
            return
        text_str = self.date_lineEdit.text()
        date_str = conv_date_string(text_str)
        if date_str is not None:
            self.setEditorValueFlag = True
            date_value = parse_date_string(date_str)
            # 日付として解釈できた場合、カレンダーの日付を更新
            self.calendarWidget.setSelectedDate(date_value)
            self.date_lineEdit.setText(date_str)
            self.receipt_manager.set_current_receipt_property("date", date_str)
            self.amount_LineEdit.setFocus()
        else:
            msgBox('日付のフォーマットが不正です', 'エラー', QMessageBox.Warning)

    @Slot()
    def category_changed(self):
        print_caller_info()
        if self.setEditorValueFlag:
            return
        combo: QComboBox = self.category_ComboBox
        category = combo.currentText()
        self.receipt_manager.set_current_receipt_property("item_category", category)

    @Slot()
    def supplyer_Changed(self):
        print_caller_info()
        if self.setEditorValueFlag:
            return
        self.supplyerComboBox.blockSignals(True)
        supplyer = self.supplyerComboBox.currentText()
        self.receipt_manager.set_current_receipt_property("supplyer_name", supplyer)
        self.supplyerComboBox.blockSignals(False)
        self.amount_LineEdit.setFocus()

    def amountLineEdit_text_changed(self):
        if self.setEditorValueFlag:
            return
        amount = self.amount_LineEdit.text()
        # amountが数値でなければamountを0にする
        if not amount.isnumeric():
            amount = "0"
        self.receipt_manager.set_current_receipt_property('amount', amount)

    @Slot()
    def saveButton_clicked(self):
        saved_Filename = self.receipt_manager.setExif(SaveMode.OVER_WRITE)
        self.blinking()
        self.statusBar.showMessage("上書き保存しました", 5000)
        self.current_org_receipts = deepcopy(self.receipt_manager.receipts)
        return saved_Filename

    @Slot()
    def saveNewButton_clicked(self):
        index = self.file_TreeView.currentIndex()
        saved_Filename = self.receipt_manager.setExif(SaveMode.SAVE_NEW)
        self.blinking()
        self.statusBar.showMessage("新しい名前で保存しました", 5000)
        self.file_TreeView.scrollTo(index, QAbstractItemView.EnsureVisible)
        self.current_org_receipts = deepcopy(self.receipt_manager.receipts)
        return saved_Filename

    @Slot()
    def addButton_clicked(self):
        if isinstance(self.receipt_manager, ReceiptManager):
            if self.temporary_receipt is None:
                self.temporary_receipt = Receipt()
                self.temporary_receipt.rect = cv2.RotatedRect(center=(1, 1), size=(1, 1), angle=0)

            self.temporary_receipt.date = self.receipt_manager.sheet_date if self.receipt_manager.sheet_date != "" else ""
            self.receipt_manager.add_receipt(self.temporary_receipt)
            self.set_receipt_image(self.temporary_receipt)
            self.receipt_manager.renew_model(self.receipt_manager.receipts)
            last_receipt_index = len(self.receipt_manager) - 1
            self.receipt_manager.set_current_receipt(last_receipt_index)
            self.isTemp_selected_watcher.v = False
        pass

    @Slot()
    def delAccButton_clicked(self):
        receipt: Receipt = self.receipt_manager.get_current_receipt()
        index: QModelIndex = self.receiptList_TreeView.currentIndex()
        self.receipt_manager.remove(receipt)
        treeView: QTreeView = self.receiptList_TreeView
        # model = treeView.model()
        if index.isValid():
            treeView.setCurrentIndex(index)
            treeView.selectionModel().setCurrentIndex(index, QItemSelectionModel.SelectionFlag.Select)
        else:
            # Indexが有効でなければ、一つ手前のインデックスを設定
            index = treeView.model().index(treeView.model().rowCount(), 0)
            if index.isValid():
                treeView.setCurrentIndex(index)
                treeView.selectionModel().setCurrentIndex(index)
            else:
                treeView.clearSelection()
                treeView.selectionModel().setCurrentIndex(index, QItemSelectionModel.SelectionFlag.Select)

    def updateButton_clicked(self):
        receipt: Receipt = self.receipt_manager.get_current_receipt()
        if receipt is None:
            return
        rect = self.temporary_receipt.rect

        self.receipt_manager.set_current_receipt_property('rect', rect)
        self.isTemp_selected_watcher.v = False

    @Slot()
    def foodButton_clicked(self):
        self.category_ComboBox.setCurrentText("食材料費")

    @Slot()
    def PetrolButton_clicked(self):
        self.category_ComboBox.setCurrentText("ガソリン代")

    @Slot()
    def supplyButton_clicked(self):
        self.category_ComboBox.setCurrentText("日用品費")

    @Slot()
    def otherButton_clicked(self):
        self.category_ComboBox.setCurrentText("その他")

    @Slot()
    def procTestButton_clicked(self):
        if len(self.receipt_manager.receipts) == 0:
            return
        if len(self.receipt_manager.receiptList_model.selectedRows()) == 0:
            receipt: Receipt = self.receipt_manager.receipts[0]
        elif len(self.receipt_manager.receiptList_model.selectedRows()) >= 1:
            receipt: Receipt = self.receipt_manager.receipts[self.receipt_manager.receiptList_model.selectedRows()[0].row()]

        receipt = util.set_receipt_info_from_ocr(receipt, self.supplyer_dic)
        mainWindow.receipt_manager.update_receipt(receipt)
        self.set_receipt_info_for_edit(receipt)

    def OcrOnlyButton_clicked(self):
        self.isOcrOnly = True
        new_filename = self.saveButton_clicked()
        self.autoButton_clicked(sheetPaths=[new_filename])
        pass

    def OCR_Tesseract_CheckBox_state_changed(self):
        pass

    @Slot()
    def debugMode_Button_clicked(self):
        global DEBUG_MODE
        DEBUG_MODE = self.debug_Mode_Button.isChecked()
        util.set_debug_mode(DEBUG_MODE)

    @Slot()
    def addSupplyerButton_clicked(self):
        self.supplyer_edit = False
        self.openSubWindow()

    @Slot()
    def editSupplyerButton_clicked(self):
        self.supplyer_edit = True
        self.openSubWindow()

    def openSubWindow(self):
        self.subWindow = SubWindow(self)
        self.subWindow.setWindowModality(Qt.ApplicationModal)
        self.subWindow.show()
        pass


def get_selected_sheet_paths():
    sheet_paths = [mainWindow.fileListModel.filePath(index) for index in mainWindow.file_TreeView.selectionModel().selectedRows()]
    if len(sheet_paths) == 0:
        return None
    return sheet_paths


def exception_hook(exctype, value, tb):
    em = ''.join(format_exception(exctype, value, tb))
    error_message = f"エラーが発生しました。\nエラーコード：{exctype}\nエラー内容：{value}\n{em}"
    filepath = os.path.dirname(sys.argv[0])
    errorLogPath = os.path.join(filepath, 'error.log')
    with open(errorLogPath, 'a') as f:
        f.write(error_message)
    print(error_message)
    sys.__excepthook__(exctype, value, tb)


if __name__ == '__main__':
    setlocale(LC_ALL, 'ja_JP.UTF-8')
    sys.excepthook = exception_hook
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec())
