from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QMovie

class SpinnerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.setAttribute(Qt.WA_TranslucentBackground)

        layout = QVBoxLayout(self)

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)

        self.movie = QMovie("assets/img/loading_128.gif")
        self.label.setMovie(self.movie)
        self.movie.start()

        layout.addWidget(self.label)
        self.setFixedSize(120, 120)
