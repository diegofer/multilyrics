import vlc
import platform
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtCore import QTimer, Slot

from core.global_state import app_state
from core.logger import get_logger
from core.error_handler import safe_operation

logger = get_logger(__name__)

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
        
        # Detectar SO
        self.system = platform.system()
        logger.debug(f"SO detectado: {self.system}")

        # VLC  
        vlc_args = ['--quiet', '--no-video-title-show', '--log-verbose=2']
        self.instance = vlc.Instance(vlc_args)
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
            logger.debug("Reproductor detenido") 
        
        media = self.instance.media_new(video_path)
        self.player.set_media(media)
        media.release()

    def move_to_screen(self):
        """Mover ventana a pantalla secundaria."""
        screens = QApplication.screens()
        logger.debug(f"Pantallas detectadas: {len(screens)}")
        for i, screen in enumerate(screens):
            logger.debug(f"  [{i}] {screen.name()}")

        if self.screen_index >= len(screens):
            logger.error("La pantalla secundaria no existe.")
            return

        target_screen = screens[self.screen_index]
        geo = target_screen.geometry()
        logger.debug(f"Moviendo a: {geo}")

        self.setGeometry(geo)
        self.showFullScreen()

        # Obtener window ID según el SO
        if self.system == "Windows":
            hwnd = int(self.winId())
            logger.debug(f"HWND obtenido: {hwnd}")
            self.player.set_hwnd(hwnd)
        elif self.system == "Linux":
            xid = int(self.winId())
            logger.debug(f"XWindow ID obtenido: {xid}")
            self.player.set_xwindow(xid)
        elif self.system == "Darwin":  # macOS
            logger.warning("macOS detectado - usando configuración estándar de VLC")
            try:
                self.player.set_nsobject(self.winId())
            except:
                logger.warning("set_nsobject no disponible, usando configuración por defecto")
        else:
            logger.warning(f"SO desconocido: {self.system}, usando configuración por defecto")

    def start_playback(self):
        """Iniciar reproducción y sincronización."""
        logger.debug("⏯ Reproduciendo video...")
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

    def seek_seconds(self, seconds: float):
        """Seek the video player to the specified time in seconds."""
        if self.player is None:
            return
        ms = int(seconds * 1000)
        with safe_operation(f"Seeking video to {seconds:.2f}s", silent=True):
            self.player.set_time(ms)

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
            logger.debug(f"[SOFT] diff={diff_ms}ms adj={adjustment_ms}ms → {new_time_ms}ms")
        
        elif corr_type == 'hard':
            diff_ms = correction.get('diff_ms', 0)
            self.player.set_time(int(new_time_ms))
            logger.debug(f"[HARD] diff={diff_ms}ms salto directo → {new_time_ms}ms")

    def closeEvent(self, event):
        """Limpiar recursos al cerrar."""
        with safe_operation("Cleaning up video player resources", silent=True):
            self.stop()
            self.position_timer.stop()
            app_state.video_is_playing = False
            self.player.release()
            self.instance.release()
        super().closeEvent(event)