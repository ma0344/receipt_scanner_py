# -*- coding: utf-8 -*-

from PySide6 import QtCore, QtWidgets, QtGui
from os import path, getcwd, chdir
from PySide6.QtGui import QStandardItemModel, QIntValidator, QKeySequence, QShortcut
from PySide6.QtCore import Qt, QDir, QEvent
from CustomWidgets import Custom_LineEdit
from PySide6.QtWidgets import QTreeView, QApplication, QMenuBar
from json import load
from PySide6.QtWidgets import QFileSystemModel
from ui_MainWindow import Ui_MainWindow
from ImageProc import SlidersValue


class CustomOutput:
    def __init__(self, textBrowser):
        self.textBrowser = textBrowser

    def write(self, text):
        # QTextBrowserにテキストを追加
        self.textBrowser.append(text)

    def flush(self):
        # flushメソッドはこの例では特に何もしませんが、
        # sys.stdoutとの互換性のために定義しておく必要があります。
        pass


class MenuBarEventFilter(QtCore.QObject):
    def __init__(self, mainWindow: Ui_MainWindow):
        super().__init__()
        self.mainWindow = mainWindow

    def eventFilter(self, watched, event):
        # event_type = event.type()
        # event_type_name = get_event_type_name(event_type)
        # print(f"menuBar Event Type: {event_type}, Name: {event_type_name}, Source: {watched.objectName()}")

        if event.type() == QEvent.ContextMenu or event.type() == QEvent.MouseButtonRelease:
            self.showContextMenu(event.globalPos())
            return True
        return super().eventFilter(watched, event)

    def showContextMenu(self, globalPos):
        contextMenu = QtWidgets.QMenu()

        action1 = QtGui.QAction("ファイルリスト", self)
        action1.setCheckable(True)
        action1.setChecked(self.mainWindow.fileList_DockWidget.isVisible())
        contextMenu.addAction(action1)

        action2 = QtGui.QAction("レシート画像", self)
        action2.setCheckable(True)
        action2.setChecked(self.mainWindow.receiptImage_DockWidget.isVisible())
        contextMenu.addAction(action2)

        action3 = QtGui.QAction("取込処理", self)
        action3.setCheckable(True)
        action3.setChecked(self.mainWindow.sheetProcess_DockWidget.isVisible())
        contextMenu.addAction(action3)

        action4 = QtGui.QAction("記帳", self)
        action4.setCheckable(True)
        action4.setChecked(self.mainWindow.accounting_DockWidget.isVisible())
        contextMenu.addAction(action4)

        action5 = QtGui.QAction("OCR結果", self)
        action5.setCheckable(True)
        action5.setChecked(self.mainWindow.ocrText_DockWidget.isVisible())
        contextMenu.addAction(action5)

        # コンテキストメニューの表示とアクションの実行
        action = contextMenu.exec_(globalPos)

        # アクションの処理
        if action == action1:
            self.mainWindow.fileList_DockWidget.setVisible(not self.mainWindow.fileList_DockWidget.isVisible())
        elif action == action2:
            self.mainWindow.receiptImage_DockWidget.setVisible(not self.mainWindow.receiptImage_DockWidget.isVisible())
        elif action == action3:
            self.mainWindow.sheetProcess_DockWidget.setVisible(not self.mainWindow.sheetProcess_DockWidget.isVisible())
        elif action == action4:
            self.mainWindow.accounting_DockWidget.setVisible(not self.mainWindow.accounting_DockWidget.isVisible())
        elif action == action5:
            self.mainWindow.ocrText_DockWidget.setVisible(not self.mainWindow.ocrText_DockWidget.isVisible())


def get_event_type_name(event_type):
    for name in dir(QEvent):
        if name.startswith('__'):
            continue
        if getattr(QEvent, name) == event_type:
            return name
    return "Unknown Event"


def file_TreeView_Initialize(self: Ui_MainWindow, first_init=False):

    model = QFileSystemModel()
    model.setRootPath(QDir.rootPath())
    model.setNameFilters(['*.jpg', '*.jpeg'])

    model.setNameFilterDisables(False)
    model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)
    tree: QTreeView = self.file_TreeView
    tree.setModel(model)
    tree.setRootIndex(model.index(QDir.rootPath()))
    tree.setColumnHidden(1, True)
    tree.setColumnHidden(2, True)
    tree.setColumnHidden(3, True)
    tree.setColumnWidth(0, 200)
    model.sort(0, Qt.AscendingOrder)
    self.fileListModel = model
    current_Index = model.index(self.data_dir)
    tree.scrollTo(current_Index)
    tree.expand(current_Index)
    tree.setCurrentIndex(current_Index)
    if self.data_dir == '':
        self.data_dir = getcwd()
    chdir(self.data_dir)

    tree.selectionModel().selectionChanged.connect(self.fileSelection_changed)
#    self.file_TreeView.selectionChanged().connect(self.selection_changed_wrapper(current_Index))

    model.directoryLoaded.connect(lambda path: dirLoaded(self, path))

    # 初期フォルダの選択と展開
    tree.expand(current_Index)


def dirLoaded(self, dir):
    # 現在選択中のインデックスのディレクトリがロードされたか確認
    if dir == self.fileListModel.filePath(self.file_TreeView.currentIndex()):
        QApplication.sendPostedEvents()  # 保留中のイベントを処理
        self.file_TreeView.scrollTo(self.file_TreeView.currentIndex(), QTreeView.PositionAtTop)


def receiptList_TreeView_Initialize(self):

    # main_window内のreceiptList_TreeViewにヘッダーを作成
    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(['適用', '仕入先', '金額'])
    # main_windowのreceiptList_TreeViewにリストアップしたファイルを表示
    tree_view: QTreeView = self.receiptList_TreeView
    tree_view.setModel(model)
    tree_view.setColumnWidth(0, 139)
    tree_view.setColumnWidth(1, 139)
    tree_view.setColumnWidth(2, 120)
    # tree_view.clicked.connect(self.receiptListSelection_changed)
    tree_view.selectionModel().selectionChanged.connect(self.receiptListSelection_changed)
    tree_view.installEventFilter(self)
    tree_view.viewport().installEventFilter(self)

    header = tree_view.header()
    header.setDefaultAlignment(QtCore.Qt.AlignCenter)
    return model


def calendar_Initialize(self):
    # main_windowのcalendarWedgetに今日の日付を設定
    calendar: QtWidgets.QCalendarWidget = self.calendarWidget
    calendar.selectionChanged.connect(self.calendarClicked)
    calendar.setSelectedDate(self.calendarWidget.selectedDate())
    # main_windowのdate_LineEditに今日の日付を設定
    self.date_lineEdit.setText(calendar.selectedDate().toString('yyyy年MM月dd日'))


def slider_and_value_Initialize(self: Ui_MainWindow):
    self.value1_Slider.setValue(20)
    self.value2_Slider.setValue(80)
    self.value3_Slider.setValue(190)
    self.Value1_LineEdit.setText(str(self.value1_Slider.value()))
    self.Value2_LineEdit.setText(str(self.value2_Slider.value()))
    self.Value3_LineEdit.setText(str(self.value3_Slider.value()))
    self.Value1_LineEdit.setValidator(QIntValidator(0, 255, self))
    self.Value2_LineEdit.setValidator(QIntValidator(0, 255, self))
    self.Value3_LineEdit.setValidator(QIntValidator(0, 255, self))
    self.sliders_value.val1 = self.value1_Slider.value()
    self.sliders_value.val2 = self.value2_Slider.value()
    self.sliders_value.val3 = self.value3_Slider.value()


def supplyer_combo_box_Initialize(self: Ui_MainWindow):
    jsonPath = path.join(self.script_dir, 'SupplyerDictionary.json')
    with open(jsonPath, 'r', encoding='utf-8') as file:
        self.supplyer_dic = load(file)
    keys_list = list(self.supplyer_dic.keys())
    self.supplyerComboBox.addItem("")
    self.supplyerComboBox.addItems(keys_list)


def apply_settings(self: Ui_MainWindow):

    file_TreeView_Initialize(self, True)
    model = receiptList_TreeView_Initialize(self)
    calendar_Initialize(self)
    slider_and_value_Initialize(self)
    supplyer_combo_box_Initialize(self)
    # custom_sheet_label_Initialize(self)
    self.receiptImage_DockWidget.parent = self
    menubar: QMenuBar = self.menuBar
    self.menuBarEventFilter = MenuBarEventFilter(self)
    menubar.installEventFilter(self.menuBarEventFilter)
    self.statusBar.addPermanentWidget(self.progressBar)
    # スライダーの値が変わったときにLineEditを更新
    self.value1_Slider.valueChanged.connect(lambda value: self.update_line_edit(value, self.Value1_LineEdit))
    self.value2_Slider.valueChanged.connect(lambda value: self.update_line_edit(value, self.Value2_LineEdit))
    self.value3_Slider.valueChanged.connect(lambda value: self.update_line_edit(value, self.Value3_LineEdit))

    # LineEditの値が変わったときにスライダーの値を更新
    self.Value1_LineEdit.textChanged.connect(lambda value: self.update_slider(value, self.value1_Slider))
    self.Value2_LineEdit.textChanged.connect(lambda value: self.update_slider(value, self.value2_Slider))
    self.Value3_LineEdit.textChanged.connect(lambda value: self.update_slider(value, self.value3_Slider))
    self.auto_Button.clicked.connect(lambda: self.autoButton_clicked(sheetPaths=None))
    self.manual_Button.clicked.connect(self.manualButton_clicked)
    self.test_Button.clicked.connect(self.testButton_clicked)

    self.directory_LineEdit.setText(getcwd())
    self.directory_LineEdit.editingFinished.connect(self.directory_line_edit_changed)

    self.shortcut_prevSheet = QShortcut(QKeySequence(Qt.Key.Key_PageUp), self)
    self.shortcut_prevSheet.activated.connect(self.prevSheetButton_clicked)
    self.prevSheet_Button.clicked.connect(self.prevSheetButton_clicked)

    self.shortcut_nextSheet = QShortcut(QKeySequence(Qt.Key.Key_PageDown), self)
    self.shortcut_nextSheet.activated.connect(self.nextSheetButton_clicked)
    self.nextSheet_Button.clicked.connect(self.nextSheetButton_clicked)

    self.deleteFile_Button.clicked.connect(self.deleteFileButton_clicked)

    self.deleteFile_Button.installEventFilter(self)
    self.makeCSV_Button.clicked.connect(self.makeCSVButton_clicked)
    self.folderSelect_Button.clicked.connect(self.folderSelectButton_clicked)

    self.shortcut_prevReceipt = QShortcut(QKeySequence(Qt.Key.Key_Minus), self)
    self.shortcut_prevReceipt.activated.connect(self.prevReceiptButton_clicked)
    self.prevReceipt_Button.clicked.connect(self.prevReceiptButton_clicked)

    self.reOcr_Button.clicked.connect(self.reOcrButton_clicked)

    self.shortcut_nextReceipt = QShortcut(QKeySequence(Qt.Key.Key_Plus), self)
    self.shortcut_nextReceipt.activated.connect(self.nextReceiptButton_clicked)
    self.nextReceipt_Button.clicked.connect(self.nextReceiptButton_clicked)

    self.date_lineEdit.editingFinished.connect(self.dateLineEedit_value_change_finished)
    self.category_ComboBox.currentIndexChanged.connect(self.category_changed)
    self.supplyerComboBox.currentIndexChanged.connect(self.supplyer_Changed)

    amountLineEdit: Custom_LineEdit = self.findChild(Custom_LineEdit, "amount_LineEdit")
    amountLineEdit.textEdited.connect(self.amountLineEdit_text_changed)
    amountLineEdit.mainWindow = self

    self.shortcut_saveButton = QShortcut(QKeySequence('Ctrl+S'), self)
    self.shortcut_saveButton.activated.connect(self.saveButton_clicked)
    self.save_Button.clicked.connect(self.saveButton_clicked)

    self.shortcut_overWriteButton = QShortcut(QKeySequence('Ctrl+Shift+S'), self)
    self.shortcut_overWriteButton.activated.connect(self.saveNewButton_clicked)
    self.saveNew_Button.clicked.connect(self.saveNewButton_clicked)

    self.shortcut_addReceipt = QShortcut(QKeySequence(Qt.Key.Key_Insert), self)
    self.shortcut_addReceipt.activated.connect(self.addButton_clicked)
    self.add_Button.clicked.connect(self.addButton_clicked)

    self.shortcut_delReceipt = QShortcut(QKeySequence('Ctrl+Delete'), self)
    self.shortcut_delReceipt.activated.connect(self.delAccButton_clicked)
    self.delReceipt_Button.clicked.connect(self.delAccButton_clicked)

    self.update_Button.clicked.connect(self.updateButton_clicked)

    self.food_Button.clicked.connect(self.foodButton_clicked)
    self.Petrol_Button.clicked.connect(self.PetrolButton_clicked)
    self.supply_Button.clicked.connect(self.supplyButton_clicked)
    self.other_Button.clicked.connect(self.otherButton_clicked)

    self.OcrOnly_Button.clicked.connect(self.OcrOnlyButton_clicked)
    checkbox: QtWidgets.QCheckBox = self.OCR_Tesseract_CheckBox
    checkbox.stateChanged.connect(self.OCR_Tesseract_CheckBox_state_changed)
    self.procTest_Button.clicked.connect(self.procTestButton_clicked)
    self.debug_Mode_Button.clicked.connect(self.debugMode_Button_clicked)
    self.addSupplyer_Button.clicked.connect(self.addSupplyerButton_clicked)
    self.editSupplyer_Button.clicked.connect(self.editSupplyerButton_clicked)

    self.splitDockWidget(self.sheetProcess_DockWidget, self.receiptImage_DockWidget, Qt.Vertical)
    self.splitDockWidget(self.receiptImage_DockWidget, self.accounting_DockWidget, Qt.Vertical)
    self.splitDockWidget(self.receiptImage_DockWidget, self.ocrText_DockWidget, Qt.Horizontal)

    self.sheetImage_Label.clicked.connect(self.sheetImage_mouse_button_pressed)
    self.sheetImage_Label.released.connect(self.sheetImage_mouse_button_released)
    self.sheetImage_Label.moved.connect(self.sheetImage_mouse_moved)

    self.file_TreeView.scrollTo(self.fileListModel.index(getcwd()))

    return model
