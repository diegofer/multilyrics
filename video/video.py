import vlc
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtCore import QTimer, Slot

from core.global_state import app_state

class VideoLyrics(QWidget):
    """
    Reproductor de video VLC con sincronización pasiva.
    
    Responsabilidades:
    - Reproducir video en pantalla secundaria
    - Reportar su posición a SyncController
    - Ejecutar correcciones de sincronización cuando se lo indica SyncController
    
    SyncController es responsable de todo el cálculo de sincronización.
    """
    
    def __init__(self, screen_index=1):
        super().__init__()
        
        self.screen_index = screen_index
        self.setWindowTitle("VideoLyrics")
        self.resize(800, 600)

        # VLC
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.player.audio_set_mute(True)

        # Layout obligatorio en una QWidget
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        # Mostrar primero (esto crea windowHandle)
        self.show()

        # Luego movemos la ventana a la pantalla correcta
        QTimer.singleShot(50, self.move_to_screen)
        
        # Timer para reportar posición periodicamente
        self.position_timer = QTimer()
        self.position_timer.setInterval(50)  # cada 50ms
        self.position_timer.timeout.connect(self._report_position)
        
        # Referencia a SyncController (se asigna desde main.py)
        self.sync_controller = None

    def set_media(self, video_path):
        """Cargar un archivo de video."""
        if self.player.is_playing():
            self.player.stop()
            app_state.video_is_playing = False
            print("[INFO] Reproductor detenido.") 
        
        media = self.instance.media_new(video_path)
        self.player.set_media(media)
        media.release()

    def move_to_screen(self):
        """Mover ventana a pantalla secundaria."""
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

    def start_playback(self):
        """Iniciar reproducción y sincronización."""
        print("⏯ Reproduciendo video...")
        self.player.play()
        app_state.video_is_playing = True
        
        # Habilitar sincronización
        if self.sync_controller:
            self.sync_controller.start_sync()
            self.position_timer.start()
    
    def stop(self):
        """Detener reproducción y sincronización."""
        app_state.video_is_playing = False
        self.player.stop()
        self.position_timer.stop()
        if self.sync_controller:
            self.sync_controller.stop_sync()
    
    def pause(self):
        """Pausar reproducción."""
        app_state.video_is_playing = False
        self.player.pause()
        self.position_timer.stop()
        if self.sync_controller:
            self.sync_controller.stop_sync()

    def _report_position(self):
        """
        Reportar posición actual al SyncController.
        Se llama periodicamente durante la reproducción.
        """
        if self.player.is_playing() and self.sync_controller:
            video_ms = self.player.get_time()
            video_seconds = video_ms / 1000.0
            self.sync_controller.on_video_position_updated(video_seconds)

    @Slot(dict)
    def apply_correction(self, correction: dict):
        """
        Ejecutar corrección de sincronización emitida por SyncController.
        
        Args:
            correction: dict con 'type', 'new_time_ms', y opcionalmente 'adjustment_ms'
        """
        if not self.player.is_playing():
            return
        
        corr_type = correction.get('type')
        new_time_ms = correction.get('new_time_ms')
        
        if corr_type == 'soft':
            adjustment_ms = correction.get('adjustment_ms', 0)
            diff_ms = correction.get('diff_ms', 0)
            self.player.set_time(int(new_time_ms))
            print(f"[SOFT] diff={diff_ms}ms adj={adjustment_ms}ms → {new_time_ms}ms")
        
        elif corr_type == 'hard':
            diff_ms = correction.get('diff_ms', 0)
            self.player.set_time(int(new_time_ms))
            print(f"[HARD] diff={diff_ms}ms salto directo → {new_time_ms}ms")

    def closeEvent(self, event):
        """Limpiar recursos al cerrar."""
        try:
            self.stop()
            self.position_timer.stop()
            app_state.video_is_playing = False
            self.player.release()
            self.instance.release()
        except:
            pass
        super().closeEvent(event)