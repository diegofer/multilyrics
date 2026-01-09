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
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QMainWindow,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(971, 705)
        self.central_widget = QWidget(MainWindow)
        self.central_widget.setObjectName(u"central_widget")
        self.central_widget_layout = QVBoxLayout(self.central_widget)
        self.central_widget_layout.setSpacing(6)
        self.central_widget_layout.setObjectName(u"central_widget_layout")
        self.central_widget_layout.setContentsMargins(0, 0, 0, 0)
        self.frame_playlist = QFrame(self.central_widget)
        self.frame_playlist.setObjectName(u"frame_playlist")
        self.frame_playlist.setStyleSheet(u"")
        self.frame_playlist.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_playlist.setFrameShadow(QFrame.Shadow.Raised)
        self.playlist_layout = QHBoxLayout(self.frame_playlist)
        self.playlist_layout.setObjectName(u"playlist_layout")
        self.playlist_layout.setContentsMargins(9, 9, 9, 0)

        self.central_widget_layout.addWidget(self.frame_playlist)

        self.frame_timeline = QFrame(self.central_widget)
        self.frame_timeline.setObjectName(u"frame_timeline")
        self.frame_timeline.setStyleSheet(u"")
        self.frame_timeline.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_timeline.setFrameShadow(QFrame.Shadow.Raised)
        self.timeline_layout = QVBoxLayout(self.frame_timeline)
        self.timeline_layout.setObjectName(u"timeline_layout")
        self.timeline_layout.setContentsMargins(9, 0, 9, 0)

        self.central_widget_layout.addWidget(self.frame_timeline)

        self.frame_mixer = QFrame(self.central_widget)
        self.frame_mixer.setObjectName(u"frame_mixer")
        self.frame_mixer.setStyleSheet(u"")
        self.frame_mixer.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_mixer.setFrameShadow(QFrame.Shadow.Raised)
        self.mixer_layout = QHBoxLayout(self.frame_mixer)
        self.mixer_layout.setObjectName(u"mixer_layout")
        self.mixer_layout.setContentsMargins(9, 0, 9, 0)
        self.frame_mixer_tracks = QFrame(self.frame_mixer)
        self.frame_mixer_tracks.setObjectName(u"frame_mixer_tracks")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame_mixer_tracks.sizePolicy().hasHeightForWidth())
        self.frame_mixer_tracks.setSizePolicy(sizePolicy)
        self.frame_mixer_tracks.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_mixer_tracks.setFrameShadow(QFrame.Shadow.Raised)
        self.mixer_tracks_layout = QHBoxLayout(self.frame_mixer_tracks)
        self.mixer_tracks_layout.setSpacing(6)
        self.mixer_tracks_layout.setObjectName(u"mixer_tracks_layout")
        self.mixer_tracks_layout.setContentsMargins(0, 0, 0, 0)

        self.mixer_layout.addWidget(self.frame_mixer_tracks)

        self.frame_mixer_master = QFrame(self.frame_mixer)
        self.frame_mixer_master.setObjectName(u"frame_mixer_master")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.frame_mixer_master.sizePolicy().hasHeightForWidth())
        self.frame_mixer_master.setSizePolicy(sizePolicy1)
        self.frame_mixer_master.setStyleSheet(u"")
        self.frame_mixer_master.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_mixer_master.setFrameShadow(QFrame.Shadow.Raised)
        self.mixer_master_layout = QHBoxLayout(self.frame_mixer_master)
        self.mixer_master_layout.setObjectName(u"mixer_master_layout")
        self.mixer_master_layout.setContentsMargins(0, 0, 0, 0)

        self.mixer_layout.addWidget(self.frame_mixer_master)


        self.central_widget_layout.addWidget(self.frame_mixer)

        self.frame_controls = QFrame(self.central_widget)
        self.frame_controls.setObjectName(u"frame_controls")
        self.frame_controls.setStyleSheet(u"")
        self.frame_controls.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_controls.setFrameShadow(QFrame.Shadow.Raised)
        self.controls_layout = QHBoxLayout(self.frame_controls)
        self.controls_layout.setObjectName(u"controls_layout")
        self.controls_layout.setContentsMargins(9, 0, 9, 9)

        self.central_widget_layout.addWidget(self.frame_controls)

        self.central_widget_layout.setStretch(0, 1)
        self.central_widget_layout.setStretch(1, 2)
        self.central_widget_layout.setStretch(2, 5)
        self.central_widget_layout.setStretch(3, 1)
        MainWindow.setCentralWidget(self.central_widget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
    # retranslateUi

