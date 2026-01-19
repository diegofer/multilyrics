from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QPushButton,
                               QStackedWidget, QVBoxLayout)

from .drop_widget import DropWidget
from .search_widget import SearchWidget


class AddDialog(QDialog):
    # TODO: Bug conocido en Intel HD 3000 + Ubuntu 22.04 - múltiples instancias visuales
    # Ver docs/KNOWN_ISSUES.md para investigación futura

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Agregar Multi")
        self.setModal(True)
        self.setFixedSize(300, 400)

        mainLayout = QVBoxLayout()

        self.stackedWidget = QStackedWidget()

        # add SearchWidget
        self.search_widget = SearchWidget()
        self.search_widget.multi_selected.connect(self.close_modal)
        self.stackedWidget.addWidget(self.search_widget)

        # add DropWidget
        self.drop_widget = DropWidget()
        self.drop_widget.file_imported.connect(self.close_modal)
        self.stackedWidget.addWidget(self.drop_widget)

        buttonPrevious = QPushButton('Buscar')
        buttonPrevious.clicked.connect(self.previousWidget)

        buttonNext = QPushButton('Crear')
        buttonNext.clicked.connect(self.nextWidget)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(buttonPrevious)
        buttonLayout.addWidget(buttonNext)

        mainLayout.addLayout(buttonLayout)
        mainLayout.addWidget(self.stackedWidget)

        self.setLayout(mainLayout)

    def nextWidget(self):
        self.stackedWidget.setCurrentIndex((self.stackedWidget.currentIndex() + 1) % 3)

    def previousWidget(self):
        self.stackedWidget.setCurrentIndex((self.stackedWidget.currentIndex() - 1) % 3)

    @Slot()
    def close_modal(self, path):
        self.accept()





