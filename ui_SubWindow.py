# -*- coding: utf-8 -*-

################################################################################
# Form generated from reading UI file 'ui_SubWindow.ui'
##
# Created by: Qt User Interface Compiler version 6.6.1
##
# WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
                            QMetaObject, QObject, QPoint, QRect,
                            QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
                           QFont, QFontDatabase, QGradient, QIcon,
                           QImage, QKeySequence, QLinearGradient, QPainter,
                           QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QMainWindow, QPlainTextEdit, QPushButton,
                               QRadioButton, QSizePolicy, QVBoxLayout, QWidget)


class Ui_SubWindow(object):
    def setupUi(self, SubWindow):
        if not SubWindow.objectName():
            SubWindow.setObjectName(u"SubWindow")
        SubWindow.resize(886, 702)
        self.centralwidget = QWidget(SubWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setVerticalSpacing(0)
        self.supplyerNameWidget = QLineEdit(self.centralwidget)
        self.supplyerNameWidget.setObjectName(u"supplyerNameWidget")
        self.supplyerNameWidget.setMinimumSize(QSize(0, 40))

        self.gridLayout_2.addWidget(self.supplyerNameWidget, 1, 0, 1, 1)

        self.label_2 = QLabel(self.centralwidget)
        self.label_2.setObjectName(u"label_2")
        font = QFont()
        font.setPointSize(10)
        self.label_2.setFont(font)
        self.label_2.setAlignment(Qt.AlignBottom | Qt.AlignLeading | Qt.AlignLeft)
        self.label_2.setIndent(10)

        self.gridLayout_2.addWidget(self.label_2, 2, 0, 1, 1)

        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")
        font1 = QFont()
        font1.setPointSize(12)
        self.label.setFont(font1)
        self.label.setIndent(10)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.horizontalLayout_3.addLayout(self.gridLayout_2)

        self.gridLayout_3 = QGridLayout()
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setVerticalSpacing(0)
        self.label_3 = QLabel(self.centralwidget)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setFont(font)
        self.label_3.setAlignment(Qt.AlignBottom | Qt.AlignLeading | Qt.AlignLeft)
        self.label_3.setIndent(10)

        self.gridLayout_3.addWidget(self.label_3, 2, 0, 1, 1)

        self.MultiRadioButton = QRadioButton(self.centralwidget)
        self.MultiRadioButton.setObjectName(u"MultiRadioButton")
        self.MultiRadioButton.setFont(font1)

        self.gridLayout_3.addWidget(self.MultiRadioButton, 0, 0, 1, 1)

        self.DirectRadioButton = QRadioButton(self.centralwidget)
        self.DirectRadioButton.setObjectName(u"DirectRadioButton")
        self.DirectRadioButton.setFont(font1)

        self.gridLayout_3.addWidget(self.DirectRadioButton, 1, 0, 1, 1)

        self.gridLayout_3.setRowMinimumHeight(0, 40)
        self.gridLayout_3.setRowMinimumHeight(1, 40)
        self.gridLayout_3.setRowMinimumHeight(2, 40)

        self.horizontalLayout_3.addLayout(self.gridLayout_3)

        self.gridLayout_4 = QGridLayout()
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setVerticalSpacing(0)
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(30)
        self.gridLayout.setContentsMargins(20, -1, 20, -1)
        self.CloseButton = QPushButton(self.centralwidget)
        self.CloseButton.setObjectName(u"CloseButton")
        self.CloseButton.setMinimumSize(QSize(0, 30))
        self.CloseButton.setFont(font1)

        self.gridLayout.addWidget(self.CloseButton, 1, 1, 1, 1)

        self.DeleteButton = QPushButton(self.centralwidget)
        self.DeleteButton.setObjectName(u"DeleteButton")
        self.DeleteButton.setEnabled(False)
        self.DeleteButton.setMinimumSize(QSize(0, 30))
        self.DeleteButton.setFont(font1)

        self.gridLayout.addWidget(self.DeleteButton, 0, 1, 1, 1)

        self.ProcessButton = QPushButton(self.centralwidget)
        self.ProcessButton.setObjectName(u"ProcessButton")
        self.ProcessButton.setMaximumSize(QSize(300, 16777215))
        self.ProcessButton.setFont(font1)
        self.ProcessButton.setStyleSheet(u"")

        self.gridLayout.addWidget(self.ProcessButton, 0, 0, 1, 1)

        self.gridLayout_4.addLayout(self.gridLayout, 1, 0, 1, 1)

        self.label_4 = QLabel(self.centralwidget)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setFont(font)
        self.label_4.setAlignment(Qt.AlignBottom | Qt.AlignLeading | Qt.AlignLeft)
        self.label_4.setIndent(10)

        self.gridLayout_4.addWidget(self.label_4, 4, 0, 1, 1)

        self.horizontalLayout_3.addLayout(self.gridLayout_4)

        self.horizontalLayout_3.setStretch(0, 5)
        self.horizontalLayout_3.setStretch(1, 5)
        self.horizontalLayout_3.setStretch(2, 5)

        self.verticalLayout_4.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.supplyerKeyWordPlainTextEdit = QPlainTextEdit(self.centralwidget)
        self.supplyerKeyWordPlainTextEdit.setObjectName(u"supplyerKeyWordPlainTextEdit")

        self.horizontalLayout_2.addWidget(self.supplyerKeyWordPlainTextEdit)

        self.amountKeyWordPlainTextEdit = QPlainTextEdit(self.centralwidget)
        self.amountKeyWordPlainTextEdit.setObjectName(u"amountKeyWordPlainTextEdit")

        self.horizontalLayout_2.addWidget(self.amountKeyWordPlainTextEdit)

        self.OCRPlainTextEdit = QPlainTextEdit(self.centralwidget)
        self.OCRPlainTextEdit.setObjectName(u"OCRPlainTextEdit")

        self.horizontalLayout_2.addWidget(self.OCRPlainTextEdit)

        self.verticalLayout_4.addLayout(self.horizontalLayout_2)

        self.horizontalLayout.addLayout(self.verticalLayout_4)

        SubWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(SubWindow)

        QMetaObject.connectSlotsByName(SubWindow)
    # setupUi

    def retranslateUi(self, SubWindow):
        SubWindow.setWindowTitle(QCoreApplication.translate("SubWindow", u"MainWindow", None))
        self.label_2.setText(QCoreApplication.translate("SubWindow", u"\u5e97\u8217\u540d\u691c\u51fa\u30ad\u30fc\u30ef\u30fc\u30c9\uff08\u6539\u884c\u3067\u8907\u6570\u6307\u5b9a\u53ef\uff09", None))
        self.label.setText(QCoreApplication.translate("SubWindow", u"\u5e97\u8217\u540d", None))
        self.label_3.setText(QCoreApplication.translate("SubWindow", u"\u91d1\u984d\u691c\u51fa\u30ad\u30fc\u30ef\u30fc\u30c9\uff08\u8907\u6570\u9805\u76ee\u306e\u5834\u5408\u6539\u884c\u3067\u8907\u6570\u6307\u5b9a\u53ef\uff09", None))
        self.MultiRadioButton.setText(QCoreApplication.translate("SubWindow", u"\u8907\u6570\u9805\u76ee\u304b\u3089\u7b97\u51fa", None))
        self.DirectRadioButton.setText(QCoreApplication.translate("SubWindow", u"\u7279\u5b9a\u9805\u76ee\u3092\u6307\u5b9a", None))
        self.CloseButton.setText(QCoreApplication.translate("SubWindow", u"Close", None))
        self.DeleteButton.setText(QCoreApplication.translate("SubWindow", u"Delete", None))
        self.ProcessButton.setText(QCoreApplication.translate("SubWindow", u"ADD", None))
        self.label_4.setText(QCoreApplication.translate("SubWindow", u"OCR\u30c6\u30ad\u30b9\u30c8", None))
    # retranslateUi
