import vlc
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtCore import QTimer

class VideoLyrics(QWidget):
    def __init__(self, video_path, screen_index=1):
        super().__init__()
        
        self.video_path = video_path
        self.screen_index = screen_index
        self.setWindowTitle("Fullscreen Video Test")
        self.resize(800, 600)

        # VLC
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()

        media = self.instance.media_new(self.video_path)
        self.player.set_media(media)

        # Layout obligatorio en una QWidget
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        # Mostrar primero (esto crea windowHandle)
        self.show()

        # Luego movemos la ventana a la pantalla correcta
        QTimer.singleShot(50, self.move_to_screen)

    def move_to_screen(self):
        screens = QApplication.screens()
        print("Pantallas detectadas:", len(screens))

        if self.screen_index >= len(screens):
            print("❌ La pantalla secundaria no existe.")
            return

        target_screen = screens[self.screen_index]

        geo = target_screen.geometry()
        print("✔ Moviendo a:", geo)

        self.setGeometry(geo)
        self.showFullScreen()

        # Ahora sí: windowHandle() existe
        hwnd = int(self.winId())
        print("✔ HWND obtenido:", hwnd)

        self.player.set_hwnd(hwnd)

        #QTimer.singleShot(300, self.start_playback)

    def start_playback(self):
        print("⏯ Reproduciendo video...")
        self.player.play()

    def closeEvent(self, event):
        try:
            self.stop()
            self.player.release()
            self.instance.release()
        except:
            pass
        super().closeEvent(event)