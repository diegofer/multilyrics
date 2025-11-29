from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QStackedWidget, QVBoxLayout,QHBoxLayout, QLineEdit, 
                               QDialog, QWidget, QPushButton)

from search_widget import SearchWidget

class WidgetLineEdits(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        for i in range(4):
            layout.addWidget(QLineEdit(f'LineEdit #{i}'))

        self.setLayout(layout)



class AddDialog(QDialog):


    def __init__(self):
        super().__init__()

        self.setWindowTitle("Agregar Multi")
        self.setModal(True)  # Establecer la ventana como modal
        self.setFixedSize(300, 400)  # Tamaño fijo para la ventana

        mainLayout = QVBoxLayout() 

        self.stackedWidget = QStackedWidget()

        # add SearchWidget
        self.search_widget = SearchWidget()
        self.search_widget.multi_selected.connect(self.on_multi_selected)
        self.stackedWidget.addWidget(self.search_widget)

        # add DropWidget
        self.stackedWidget.addWidget(WidgetLineEdits())

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

    def on_multi_selected(self, ruta):
        print(ruta)
        self.accept()


        
