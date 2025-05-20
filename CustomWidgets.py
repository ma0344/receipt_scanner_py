from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QObject, Signal, QEvent
from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtWidgets import QDockWidget, QLabel, QPushButton
focus_style = """
QComboBox:focus, QPushButton:focus, QLineEdit:focus {
    border: 2px solid #3daee9;
}
"""


class Custom_Button(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyle()  # カスタムスタイルを適用するメソッド

    def setStyle(self):
        # フォーカスが当たったときのスタイルを設定
        self.setStyleSheet(focus_style)


class Custom_ComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyle()  # カスタムスタイルを適用するメソッド

    def setStyle(self):
        # フォーカスが当たったときのスタイルを設定
        self.setStyleSheet(focus_style)


class Custom_LineEdit(QtWidgets.QLineEdit):
    """
    フォーカスイン時にテキストをすべて選択するLineEdit
    """

    def __init__(self, parent=None, mainWindow=None):
        super().__init__(parent)
        self.mainWindow = mainWindow
        self.installEventFilter(self)
        self.setStyle()  # カスタムスタイルを適用するメソッド

    def eventFilter(self, obj, event):
        # フォーカスインイベントを捕捉
        if event.type() == QEvent.FocusIn:
            self.selectAll()  # テキストをすべて選択
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        # キー入力イベントを捕捉
        # キーがマイナス、プラス、numエンター、リターン
        if (event.key() in [QtCore.Qt.Key_Minus, QtCore.Qt.Key_Plus, QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return, QtCore.Qt.Key_Tab]) and self.objectName() != 'date_lineEdit':
            match event.key():
                case QtCore.Qt.Key_Enter | QtCore.Qt.Key_Return | QtCore.Qt.Key_Plus:
                    # self.mainWindow.save_Button.setFocus()
                    # キー押下げ時のカレント位置により処理を分岐
                    # next_index = (self.mainWindow.receipt_manager.current_index + 1) % len(self.mainWindow.receipt_manager.receipts)
                    # # 最終行で入力終了時
                    # if next_index == 0:
                    #     self.mainWindow.nextSheetButton_clicked()
                    #     self.selectAll()
                    # else:
                    self.mainWindow.nextReceiptButton_clicked()
                    # LineEditのテキストをすべて選択状態に
                    self.selectAll()

                case QtCore.Qt.Key_Minus:
                    self.mainWindow.prevReceiptButton_clicked()
                    # LineEditのテキストをすべて選択状態に
                    self.selectAll()
        else:
            super().keyPressEvent(event)

    def setStyle(self):
        # フォーカスが当たったときのスタイルを設定
        self.setStyleSheet(focus_style)


class Custom_widget(QDockWidget):
    original_receiptPix = None

    def __init__(self, parent=None):
        super(Custom_widget, self).__init__(parent)
        # self.contents = self.findChildren(QWidget, "receiptImage_DockWidgetContents")

    def resizeEvent(self, event):
        # ここにリサイズ時の処理を記述
        super(Custom_widget, self).resizeEvent(event)
        self.adjust_ReceiptImageSize()

    def adjust_ReceiptImageSize(self):
        if self.original_receiptPix:
            label = self.findChild(QLabel, "receiptImage_Label")
            resized_pixmap = self.original_receiptPix.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(resized_pixmap)


class Custum_Label(QLabel, QObject):
    clicked = Signal(object)
    dragged = Signal(object)
    released = Signal(object)
    moved = Signal(object)

    def __init__(self, parent=None):
        super(Custum_Label, self).__init__(parent)
        self.setMouseTracking(True)
        self.original_SheetPixmap: QPixmap = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_SheetImageSize()

    def adjust_SheetImageSize(self):
        if self.original_SheetPixmap:
            resized_pixmap = self.original_SheetPixmap.scaled(self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(resized_pixmap)

    def mousePressEvent(self, event):
        self.clicked.emit(event)

    def mouseMoveEvent(self, event):
        self.moved.emit(event)

    def mouseReleaseEvent(self, event):
        self.released.emit(event)
