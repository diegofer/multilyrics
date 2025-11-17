# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'shell.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QMainWindow, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(800, 600)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.frame = QFrame(self.centralwidget)
        self.frame.setObjectName(u"frame")
        self.frame.setStyleSheet(u"QFrame{\n"
"	background-color: rgb(29,35,67);\n"
"}")
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)

        self.verticalLayout.addWidget(self.frame)

        self.frame_2 = QFrame(self.centralwidget)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setStyleSheet(u"QFrame{\n"
"	background-color: rgb(43,52,95);\n"
"}")
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)

        self.verticalLayout.addWidget(self.frame_2)

        self.frame_3 = QFrame(self.centralwidget)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setStyleSheet(u"QFrame{\n"
"	background-color: rgb(29,35,67);\n"
"}")
        self.frame_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Shadow.Raised)

        self.verticalLayout.addWidget(self.frame_3)

        self.frame_4 = QFrame(self.centralwidget)
        self.frame_4.setObjectName(u"frame_4")
        self.frame_4.setStyleSheet(u"QFrame{\n"
"	background-color: rgb(43,52,95);\n"
"}")
        self.frame_4.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_4.setFrameShadow(QFrame.Shadow.Raised)

        self.verticalLayout.addWidget(self.frame_4)

        self.verticalLayout.setStretch(0, 1)
        self.verticalLayout.setStretch(1, 2)
        self.verticalLayout.setStretch(2, 5)
        self.verticalLayout.setStretch(3, 1)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
    # retranslateUi

