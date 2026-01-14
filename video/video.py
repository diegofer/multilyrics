import vlc
import platform
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtCore import QTimer, Slot

from core.constants import app_state
from utils.logger import get_logger
from utils.error_handler import safe_operation

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
        """Seek the video player to the specified time in seconds.
        
        Handles edge cases like seeking after video has ended by ensuring
        the player is in a valid state and forcing a frame update.
        """
        if self.player is None:
            return
        
        ms = int(seconds * 1000)
        
        with safe_operation(f"Seeking video to {seconds:.2f}s", silent=True):
            # Check if video has ended (VLC state 6 = Ended)
            state = self.player.get_state()
            was_playing = self.player.is_playing()
            
            # If video ended, need to stop() and play() to fully reset
            if state == vlc.State.Ended:
                logger.debug("Video ended, performing full reset before seek")
                # Stop completely to reset VLC state
                self.player.stop()
                # Wait for stop to complete
                QTimer.singleShot(50, lambda: self._restart_and_seek(ms, was_playing))
                return
            
            # Normal seek (not ended)
            self.player.set_time(ms)
            
            # Force frame update if not playing
            if not was_playing:
                # Pause to show the frame at seek position
                self.player.pause()
    
    def _restart_and_seek(self, ms: int, was_playing: bool):
        """Restart player after stop and seek to position.
        
        Called after stop() completes to fully reset from ended state.
        """
        if self.player is None:
            return
        
        with safe_operation("Restarting player and seeking", silent=True):
            # Play to restart from beginning
            self.player.play()
            # Wait for play to start
            QTimer.singleShot(150, lambda: self._complete_seek_after_restart(ms, was_playing))
    
    def _complete_seek_after_restart(self, ms: int, was_playing: bool):
        """Complete seek operation after restarting.
        
        Called after play() completes to perform actual seek.
        """
        if self.player is None:
            return
        
        with safe_operation("Completing seek after restart", silent=True):
            # Now do the actual seek
            self.player.set_time(ms)
            
            # If wasn't playing before, pause to show frame
            if not was_playing:
                # Wait for seek to complete, then pause
                QTimer.singleShot(100, lambda: self._pause_and_show_frame())
    
    def _pause_and_show_frame(self):
        """Pause player to display current frame.
        
        Called after seek completes to ensure frame is visible.
        """
        if self.player is not None:
            self.player.pause()
            logger.debug("Video paused to show frame after seek")

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