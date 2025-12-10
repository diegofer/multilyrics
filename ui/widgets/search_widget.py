from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QVBoxLayout, QListWidgetItem, QLineEdit, 
                               QWidget, QListWidget)
from core import global_state
from core.utils import get_multis_list

class SearchWidget(QWidget):

    multi_selected = Signal(str)

    def __init__(self):
        super().__init__()

        # Lista completa de canciones
        self.multis_list = []

        layout = QVBoxLayout()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Buscar")
        self.search_box.textChanged.connect(self.filtrar_canciones)

        # Lista para mostrar canciones filtradas
        self.resultados_lista = QListWidget()
        self.resultados_lista.itemClicked.connect(self.procesar_seleccion) 

        layout.addWidget(self.search_box)
        layout.addWidget(self.resultados_lista)
        self.setLayout(layout)

        self.get_fresh_multis_list()

    def get_fresh_multis_list(self):
        self.multis_list = get_multis_list(global_state.MULTIS_PATH)
        self.actualizar_lista(self.multis_list) # actualizar QListWidget

    def filtrar_canciones(self, texto):
        """Filtra las canciones según el texto ingresado en la caja de búsqueda."""
        texto = texto.lower()
        canciones_filtradas = [
            (titulo, ruta) for titulo, ruta in self.multis_list if texto in titulo.lower()
        ]
        self.actualizar_lista(canciones_filtradas)

    def actualizar_lista(self, canciones):
        """Actualiza la lista de resultados."""
        self.resultados_lista.clear()
        for titulo, ruta in canciones:
            item = QListWidgetItem(titulo)  # Mostrar solo el título
            item.setData(Qt.ItemDataRole.UserRole, ruta)  # Almacenar la ruta como dato oculto
            self.resultados_lista.addItem(item)
    
    def procesar_seleccion(self, item):
        ruta = item.data(Qt.ItemDataRole.UserRole)
        self.multi_selected.emit(ruta)