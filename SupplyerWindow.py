# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QMainWindow, QMessageBox
from PySide6 import QtCore, QtWidgets
from ui_SubWindow import Ui_SubWindow
import json
from util import msgBox
import os


class SubWindow(QMainWindow, Ui_SubWindow):
    def __init__(self, mainWindow):
        super().__init__()
        self.setupUi(self)
        self.mainWindow = mainWindow
        self.supplyer_dic = self.mainWindow.supplyer_dic
        self.ProcessButton.clicked.connect(self.save_data)
        self.CloseButton.clicked.connect(self.close)
        self.DeleteButton.clicked.connect(self.delete_supplyer)
        self.MultiRadioButton.setChecked(True)
        self.editMode = self.mainWindow.supplyer_edit
        self.layout: QtWidgets.QGridLayout = self.gridLayout_2
        self.originalWidget = None
        self.script_dir = self.mainWindow.script_dir
        self.mainWindow_supplyer_combobox = self.mainWindow.supplyerComboBox

        if self.editMode:
            self.originalWidget = self.findChild(QtWidgets.QLineEdit, "supplyerNameWidget")
            self.setWindowTitle("編集")
            self.ProcessButton.setText("SAVE")
            new_widget = QtWidgets.QComboBox(self.centralwidget)
            new_widget.setStyleSheet("QComboBox { padding: 0px 20px; font: 15pt \"MS UI Gothic\"; }")
            self.set_supplyer_combobox(new_widget)
            new_widget.currentIndexChanged.connect(self.change_supplyer)
            new_widget.setMinimumSize(QtCore.QSize(0, 40))
            new_widget.setObjectName("supplyerNameWidget")
            self.layout.removeWidget(self.originalWidget)
            self.originalWidget.deleteLater()
            self.layout.addWidget(new_widget, 1, 0, 1, 1)
            self.supplyerNameWidget = new_widget
            self.DeleteButton.setEnabled(True)
            self.supplyerNameWidget.setCurrentText(self.mainWindow.supplyerComboBox.currentText())
        else:
            self.setWindowTitle("新規登録")
            self.ProcessButton.setText("ADD")
            self.DeleteButton.setEnabled(False)

    def set_supplyer_combobox(self, widget, index=0):
        self.clear_TextEdit()
        widget.clear()
        keys_list = list(self.supplyer_dic.keys())
        widget.addItem("")
        widget.addItems(keys_list)
        widget.setCurrentIndex(index)

    def clear_TextEdit(self):
        self.supplyerKeyWordPlainTextEdit.clear()
        self.amountKeyWordPlainTextEdit.clear()

    def save_data(self, isDelete=False):
        nameWidget: QtWidgets.QComboBox = self.supplyerNameWidget
        if self.editMode is False:
            supplyer, arr = self.make_Arr()
            self.supplyer_dic[supplyer] = arr
            self.mainWindow_supplyer_combobox.addItem(supplyer)
            self.set_supplyer_combobox(self.mainWindow_supplyer_combobox, len(self.mainWindow_supplyer_combobox) - 1)
        elif self.editMode is True:
            supplyer, arr = self.make_Arr()
            self.supplyer_dic[supplyer] = arr
            index = 0 if isDelete else nameWidget.currentIndex()
            self.set_supplyer_combobox(self.supplyerNameWidget, index)
        jsonPath = os.path.join(self.script_dir, 'SupplyerDictionary.json')
        with open(jsonPath, 'w', encoding='utf-8') as f:
            json.dump(self.supplyer_dic, f, ensure_ascii=False, indent=4)
        msgBox('SupplyerDictionary.json を保存しました', '保存')

    def make_Arr(self):
        supplyer_name = self.supplyerNameWidget.currentText() if self.editMode else self.supplyerNameWidget.text()
        Values = self.supplyerKeyWordPlainTextEdit.toPlainText().split('\n')
        CalculationLabels = self.amountKeyWordPlainTextEdit.toPlainText().split('\n')
        if self.MultiRadioButton.isChecked():
            CalculationMethod = "Sum"
        elif self.DirectRadioButton.isChecked():
            CalculationMethod = "Direct"
        return_arr = {}
        return_arr['Values'] = Values
        return_arr['CalculationMethod'] = CalculationMethod
        return_arr['CalculationLabels'] = CalculationLabels
        return (supplyer_name, return_arr)

    def delete_supplyer(self):

        supplyer_name = self.supplyerNameWidget.currentText()
        answer = msgBox(f"{supplyer_name} を削除します", "削除", QMessageBox.Question, QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            del self.supplyer_dic[supplyer_name]
            self.save_data(isDelete=True)
            msgBox(f'{supplyer_name}を削除しました', '削除')

    def change_supplyer(self):
        supplyer_name = self.supplyerNameWidget.currentText()
        if supplyer_name == "":
            self.clear_TextEdit()
            return
        supplyer_data = self.supplyer_dic[supplyer_name]
        supplyerKeyWord = '\n'.join(supplyer_data['Values'])
        self.supplyerKeyWordPlainTextEdit.setPlainText(supplyerKeyWord)
        calcurationKeyWord_data = supplyer_data['CalculationLabels']
        calcurationKeyWord = '\n'.join(calcurationKeyWord_data)
        self.amountKeyWordPlainTextEdit.setPlainText(calcurationKeyWord)
        ocrTextBrowser: QtWidgets.QTextBrowser = self.mainWindow.ocrString_textBrowser
        ocrText = ocrTextBrowser.toPlainText()
        self.OCRPlainTextEdit.setPlainText(ocrText)
        CalculationMethod = supplyer_data['CalculationMethod']
        if CalculationMethod == "Sum":
            self.MultiRadioButton.isChecked()
        elif CalculationMethod == "Direct":
            self.DirectRadioButton.isChecked()

    def closeEvent(self, event):
        mw = self.mainWindow
        rm = mw.receipt_manager
        cb: QtWidgets.QComboBox = mw.supplyerComboBox
        mw.supplyer_edit = False
        if rm.sheet_image is not None:
            if not cb.currentText() in self.supplyer_dic:
                self.set_supplyer_combobox(cb)

        event.accept()
