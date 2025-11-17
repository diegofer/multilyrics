from PySide6.QtWidgets import QApplication, QMainWindow, QLayout, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QWidget, QFrame
from PySide6.QtCore import Qt
from shell import Ui_MainWindow
from waveform import WaveformWidget
from controls_widget import ControlsWidget
from qt_utils import add_widget_to_frame

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Estilo para los QLabel de tiempo
        # Ajustar el formato inicial del label
        self.time_label_style = "QLabel { color: white; font-size: 14px; font-weight: bold; background: transparent; padding: 5px; }"
        
        # Contenedor para la barra de tiempo y controles (frame_2)
        wave_container = QWidget()
        wave_container.setLayout(QVBoxLayout())
        wave_container.layout().setContentsMargins(4,4,4,4)
        wave_container.layout().setSpacing(4)
        
        # Reemplazar el frame_2 por el contenedor
        self.ui.verticalLayout.replaceWidget(self.ui.frame_2, wave_container)
        self.ui.frame_2.deleteLater() # Borrar el widget original

        # Waveform widget
        # ASUME QUE TIENES UN ARCHIVO example.wav EN EL MISMO DIRECTORIO
        self.waveform = WaveformWidget("example.wav")
        wave_container.layout().addWidget(self.waveform)

        # ----------- Controles de reproducción -----------
        controls_layout = QHBoxLayout()

        # Etiqueta para mostrar el tiempo
        self.time_label = QLabel("00:00 / 00:00") # Etiqueta inicial simplificada
        self.time_label.setStyleSheet(self.time_label_style)
        self.time_label.setAlignment(Qt.AlignCenter)        

        controls_layout.addWidget(self.time_label) # Añadir el label

        wave_container.layout().addLayout(controls_layout)

        # load ControlsWidget en Frame de la UI
        self.controls = add_widget_to_frame(ControlsWidget, self.ui.frame_4, QHBoxLayout)
        self.controls.play_clicked.connect(self.on_play)
        self.controls.stop_clicked.connect(self.on_stop)
        
        # CONEXIÓN CRUCIAL: Conectar la señal de tiempo del widget a la función de actualización
        self.waveform.time_updated.connect(self.update_time_label)


    def _format_time(self, seconds):
        """Convierte segundos a formato MM:SS."""
        if seconds is None or seconds < 0:
            return "00:00"
            
        # Redondear al segundo más cercano
        total_seconds = int(round(seconds))
        
        minutes = total_seconds // 60
        secs = total_seconds % 60
        
        return f"{minutes:02d}:{secs:02d}"

    def update_time_label(self, current_time_sec: float, total_duration_sec: float):
        """Actualiza el QLabel con el tiempo transcurrido y la duración total."""
        current_time_str = self._format_time(current_time_sec)
        total_duration_str = self._format_time(total_duration_sec)
        self.time_label.setText(f"{current_time_str} / {total_duration_str}")

    def on_play(self):
        self.waveform.start_play()

    def on_stop(self):
        self.waveform.stop_play()


if __name__ == "__main__":
    import sys
    # Se necesita un archivo de audio WAV llamado "example.wav" en el mismo directorio.
    # Si no tienes uno, puedes usar un script de Python simple para crearlo:
    # import soundfile as sf
    # import numpy as np
    # sf.write('example.wav', np.random.uniform(-1, 1, 44100 * 5), 44100) # 5 segundos de ruido

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())