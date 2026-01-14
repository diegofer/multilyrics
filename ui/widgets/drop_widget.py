import shutil
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QPoint, Signal, QTimer
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent
from core import constants


class DropWidget(QWidget):

    file_imported = Signal(str)

    def __init__(self):
        super().__init__()

        # QDialog sin bordes y draggable
        #self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)

        # Aceptar drag & drop
        self.setAcceptDrops(True)

        # Layout principal
        layout = QVBoxLayout(self)

        # --- ÍCONO GRANDE ---
        self.icon_label = QLabel()
        pix = QPixmap( "assets/img/media-video-plus.svg" )  # <--- reemplaza por tu ícono
        if pix.isNull():                  # Si no encuentra icono, dibuja uno por defecto
            pix = QPixmap(128, 128)
            pix.fill(Qt.lightGray)

        self.icon_label.setPixmap(pix.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.icon_label.setAlignment(Qt.AlignCenter)

        # --- TEXTO ---
        self.text_label = QLabel("Arrastra aquí\nMP4", self)
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setStyleSheet("font-size: 18px; color: white;")

        # Fondo de la ventana
        self.setStyleSheet("""
            background-color: #2d2d2d;
            border-radius: 10px;
        """)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)

        self.dragPos = QPoint()

    # ----------------------------
    # Ventana Draggable
    # ----------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            diff = event.globalPosition().toPoint() - self.dragPos
            self.move(self.pos() + diff)
            self.dragPos = event.globalPosition().toPoint()

    # ----------------------------
    # Drag & Drop File
    # ----------------------------
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        multis_folder = Path(constants.MULTIS_PATH)
        multis_folder.mkdir(exist_ok=True)

        valid_ext = {".mp4"}
        copied = 0
        last_path = None

        for url in event.mimeData().urls():
            file_path = Path(url.toLocalFile())      

            if file_path.suffix.lower() in valid_ext:

                folder_name = file_path.stem  #tomamos el nombre del archivo y se lo ponemos al folder
                target_folder = multis_folder / folder_name

                target_folder.mkdir(exist_ok=True)
                NEW_FILE_NAME = constants.VIDEO_FILE + file_path.suffix.lower() # ej.video.mp4
                final_path = target_folder / NEW_FILE_NAME
                shutil.copy(file_path, final_path)
                copied += 1
                last_path = final_path

        if copied > 0:
            self.text_label.setText(f"¡{copied} archivo(s) copiado(s)!")
        else:
            self.text_label.setText("Formato no permitido")

        event.acceptProposedAction()

        if last_path:
            QTimer.singleShot(  #usamos singleShot para evitar fallo critico al cerrar modal 
                0,
                lambda p=str(last_path): self.file_imported.emit(p)
            )


