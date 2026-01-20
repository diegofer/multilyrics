import platform

import vlc
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from core.constants import app_state
from utils.error_handler import safe_operation
from utils.logger import get_logger

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

        # Detectar hardware antiguo y determinar si video debe estar deshabilitado
        self._is_legacy_hardware = self._detect_legacy_hardware()
        self._video_auto_disabled = self._is_legacy_hardware

        if self._video_auto_disabled:
            logger.warning(
                "⚠️ Hardware antiguo detectado - Video deshabilitado por defecto para prevenir stuttering. "
                "Puede habilitarlo manualmente si lo desea."
            )

        # VLC con optimizaciones para hardware antiguo si es necesario
        # Restricción vital: forzar '--no-audio' para que VLC nunca emita sonido; el AudioEngine es el único dueño del audio
        vlc_args = ['--quiet', '--no-video-title-show', '--log-verbose=2', '--no-audio']

        if self._is_legacy_hardware:
            # Optimizaciones para CPUs antiguas
            vlc_args.extend([
                '--avcodec-hurry-up',         # Skip frames si CPU lenta
                '--avcodec-skiploopfilter=4', # Saltear deblocking (menos CPU)
                '--avcodec-threads=2',        # Limitar threads (dejar para audio)
                '--file-caching=1000',        # Buffer más grande (menos picos)
            ])
            logger.info("🔧 VLC configurado con optimizaciones para hardware antiguo")

        self.instance = vlc.Instance(vlc_args)
        self.player = self.instance.media_player_new()
        self.player.audio_set_mute(True)

        # Layout obligatorio en una QWidget
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        # No mostrar por defecto - se mostrará cuando el usuario haga click en el botón
        # Creamos la ventana pero permanece oculta
        self.hide()

        # Flag para saber si ya se inicializó la ventana en la pantalla correcta
        self._window_initialized = False
        # Referencia a pantalla objetivo
        self._target_screen = None

        # Timer para reportar posición periodicamente
        self.position_timer = QTimer()
        self.position_timer.setInterval(50)  # cada 50ms
        self.position_timer.timeout.connect(self._report_position)

        # Referencia a SyncController (se asigna desde main.py)
        self.sync_controller = None

    def _detect_legacy_hardware(self) -> bool:
        """Detectar si el sistema es hardware antiguo que puede tener problemas con video 1080p.

        Criterios conservadores (solo marca como legacy si detecta señales claras):
        - CPUs Intel Sandy Bridge o anteriores (2011 y más antiguos)
        - CPUs AMD pre-2013
        - RAM < 6GB

        Returns:
            bool: True si es hardware legacy, False si es moderno o no se puede determinar
        """
        try:
            if self.system == "Linux":
                # Leer info de CPU desde /proc/cpuinfo
                try:
                    with open("/proc/cpuinfo", "r") as f:
                        cpuinfo = f.read().lower()

                        # CPUs específicas conocidas por tener problemas
                        legacy_cpu_markers = [
                            "i5-2410m",  # Sandy Bridge (2011) - el caso del usuario
                            "i3-2",      # Sandy Bridge i3
                            "i5-2",      # Sandy Bridge i5
                            "i7-2",      # Sandy Bridge i7
                            "core(tm)2 duo",  # Core 2 Duo (2006-2009)
                            "core(tm)2 quad", # Core 2 Quad (2007-2009)
                            "pentium(r) dual", # Pentium Dual Core
                        ]

                        for marker in legacy_cpu_markers:
                            if marker in cpuinfo:
                                logger.info(f"🔍 CPU Legacy detectada: {marker}")
                                return True

                except FileNotFoundError:
                    logger.debug("/proc/cpuinfo no encontrado - asumiendo hardware moderno")
                except Exception as e:
                    logger.debug(f"Error leyendo cpuinfo: {e}")

            # Detección de RAM baja (cross-platform con psutil si está disponible)
            try:
                import psutil
                ram_gb = psutil.virtual_memory().total / (1024**3)
                if ram_gb < 6:
                    logger.info(f"🔍 RAM limitada detectada: {ram_gb:.1f}GB < 6GB")
                    return True
            except ImportError:
                logger.debug("psutil no disponible - saltando detección de RAM")
            except Exception as e:
                logger.debug(f"Error detectando RAM: {e}")

        except Exception as e:
            logger.warning(f"Error en detección de hardware: {e}")

        # Por defecto, asumir hardware moderno (enfoque conservador)
        logger.info("✅ Hardware moderno detectado o no pudo determinarse - video habilitado")
        return False

    def is_video_enabled(self) -> bool:
        """Verificar si video está habilitado (automático o manual).

        Returns:
            bool: True si video puede reproducirse, False si está deshabilitado
        """
        return not self._video_auto_disabled

    def enable_video(self, enable: bool = True):
        """Habilitar o deshabilitar video manualmente (override de detección automática).

        Args:
            enable: True para habilitar video, False para deshabilitar
        """
        self._video_auto_disabled = not enable

        if enable:
            logger.info("📹 Video habilitado manualmente")
        else:
            logger.info("🚫 Video deshabilitado manualmente")
            # Si estaba reproduciendo, detener
            if self.player.is_playing():
                self.stop()

    def set_media(self, video_path):
        """Cargar un archivo de video (solo si está habilitado)."""
        # Si video está deshabilitado, no cargar nada pero no fallar
        if self._video_auto_disabled:
            logger.info(f"📹 Video deshabilitado - omitiendo carga de {video_path}")
            logger.info("💡 Puede habilitar video manualmente con enable_video() si su hardware lo soporta")
            return

        if self.player.is_playing():
            self.player.stop()
            app_state.video_is_playing = False
            logger.debug("Reproductor detenido")

        media = self.instance.media_new(video_path)
        # Deshabilitar audio del video - el audio será controlado por el AudioEngine
        media.add_option("--no-audio")
        self.player.set_media(media)
        media.release()
        logger.debug(f"📹 Video cargado: {video_path}")

    def show_window(self):
        """Mostrar la ventana de video en la pantalla secundaria.

        Inicializa la ventana en la pantalla correcta la primera vez,
        luego simplemente muestra/oculta según sea necesario.
        VLC permanece adjunto al window handle durante todo el ciclo de vida.
        """
        if not self._window_initialized:
            # Primera vez: inicializar ventana y adjuntar VLC
            logger.debug("Inicializando ventana de video por primera vez")
            self.show()  # Crear windowHandle
            QTimer.singleShot(50, self._initialize_window)
        else:
            # Ya inicializada: simplemente mostrar
            logger.debug("Mostrando ventana de video")
            self.showFullScreen()

    def hide_window(self):
        """Ocultar la ventana de video sin destruir el player VLC.

        La ventana permanece oculta pero VLC mantiene su adjunto al window handle,
        evitando bugs de reinicialización.
        """
        logger.debug("Ocultando ventana de video")
        self.hide()

    def _initialize_window(self):
        """Inicializar la ventana en la pantalla correcta y adjuntar VLC.

        Llamado solo la primera vez que se muestra la ventana.
        """
        self.move_to_screen()
        self._window_initialized = True
        logger.debug("Ventana de video inicializada")

    def move_to_screen(self):
        """Mover ventana a pantalla secundaria y adjuntar VLC."""
        screens = QApplication.screens()
        logger.info(f"📺 Pantallas detectadas: {len(screens)}")
        for i, screen in enumerate(screens):
            dpi = screen.logicalDotsPerInch()
            size = screen.geometry()
            logger.info(f"  [{i}] {screen.name()} - Resolución: {size.width()}x{size.height()} @ {dpi} DPI")

        if self.screen_index >= len(screens):
            logger.error(f"❌ Pantalla {self.screen_index} no existe (solo hay {len(screens)})")
            return

        target_screen = screens[self.screen_index]
        self._target_screen = target_screen
        geo = target_screen.geometry()
        logger.info(f"✓ Moviendo ventana a pantalla {self.screen_index}: {geo.x()},{geo.y()} {geo.width()}x{geo.height()}")

        # Asegurar que la ventana se mueve ANTES de adjuntar VLC
        # Forzar ventana nativa para obtener handle
        if self.windowHandle() is None:
            self.setAttribute(Qt.WA_NativeWindow, True)
        handle = self.windowHandle()
        if handle is not None:
            try:
                handle.setScreen(target_screen)
                logger.info(f"✓ Screen asignada vía windowHandle: {target_screen.name()}")
            except Exception as e:
                logger.warning(f"⚠ No se pudo asignar pantalla vía windowHandle: {e}")
        else:
            logger.warning("⚠ windowHandle() no disponible; continuando con setGeometry")

        self.setGeometry(geo)
        self.show()  # Llamar show() antes de showFullScreen() para asegurar winId() válido
        QTimer.singleShot(100, self._attach_vlc_to_window)

    def _attach_vlc_to_window(self):
        """Adjuntar VLC a la ventana después de que está completamente inicializada."""
        try:
            # Reafirmar pantalla objetivo antes de adjuntar/entrar a fullscreen
            handle = self.windowHandle()
            if handle is not None and self._target_screen is not None:
                try:
                    handle.setScreen(self._target_screen)
                    logger.info(f"✓ Screen reafirmada: {self._target_screen.name()}")
                except Exception as e:
                    logger.warning(f"⚠ No se pudo reafirmar pantalla: {e}")

            if self.system == "Windows":
                hwnd = int(self.winId())
                logger.info(f"✓ HWND obtenido: {hwnd}")
                self.player.set_hwnd(hwnd)

            elif self.system == "Linux":
                # En Linux, necesitamos asegurar que la ventana está mapeada
                if not self.isVisible():
                    logger.warning("⚠ Ventana no visible antes de set_xwindow()")
                    self.show()

                xid = int(self.winId())
                if xid == 0:
                    logger.error("❌ winId() retornó 0 - ventana no inicializada correctamente")
                    return

                logger.info(f"✓ XWindow ID obtenido: {xid}")
                self.player.set_xwindow(xid)
                logger.info("✓ VLC adjuntado correctamente a ventana X11")

            elif self.system == "Darwin":  # macOS
                logger.info("🍎 macOS detectado - intentando set_nsobject()")
                try:
                    self.player.set_nsobject(self.winId())
                    logger.info("✓ VLC adjuntado a ventana macOS")
                except Exception as e:
                    logger.warning(f"⚠ set_nsobject falló: {e}, usando configuración por defecto")
            else:
                logger.warning(f"⚠ SO desconocido: {self.system}, VLC usará configuración por defecto")

            # Finalmente, entrar a fullscreen (en pantalla objetivo)
            handle = self.windowHandle()
            if handle is not None and self._target_screen is not None:
                try:
                    handle.setScreen(self._target_screen)
                except Exception:
                    pass
            self.showFullScreen()
            logger.info("✓ Ventana en fullscreen")

        except Exception as e:
            logger.error(f"❌ Error al adjuntar VLC: {e}", exc_info=True)

    def start_playback(self, audio_time_seconds: float = 0.0, offset_seconds: float = 0.0):
        """Iniciar reproducción y sincronización con offset inicial.

        Args:
            audio_time_seconds: Tiempo actual del audio (para seeks/resume)
            offset_seconds: Offset de metadata (video_offset_seconds)
                          Positivo = video empieza después del audio
                          Negativo = video empieza antes del audio
        """
        if self._video_auto_disabled:
            logger.debug("📹 Video deshabilitado - saltando reproducción")
            return

        # Solo reproducir si la ventana está visible (usuario activó show_video_btn)
        if not self.isVisible():
            logger.debug("📹 Ventana de video oculta - saltando reproducción de video (audio continuará)")
            return

        # Calcular tiempo inicial del video con offset
        video_start_time = audio_time_seconds + offset_seconds

        # CRÍTICO: Seek ANTES de play() para arranque determinista
        if abs(video_start_time) > 0.001:  # Solo si es significativo (>1ms)
            video_ms = max(0, int(video_start_time * 1000))  # Clamp negativo a 0
            self.player.set_time(video_ms)
            logger.info(
                f"[VIDEO_OFFSET] audio={audio_time_seconds:.3f}s "
                f"offset={offset_seconds:+.3f}s → video_start={video_start_time:.3f}s ({video_ms}ms)"
            )

        # Log initial state for diagnosis
        initial_time_ms = self.player.get_time()
        logger.info(f"[VIDEO_START] t={initial_time_ms}ms state={self.player.get_state()}")

        logger.debug("⏯ Reproduciendo video...")
        self.player.play()
        self.player.audio_set_mute(True)  # Asegurar que audio está muteado antes de reproducir
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

        Preserves pause state: if paused before seek, remains paused after.
        """
        if self.player is None:
            return

        ms = int(seconds * 1000)
        current_time_ms = self.player.get_time()

        with safe_operation(f"Seeking video to {seconds:.2f}s", silent=True):
            # Log seek for diagnosis
            logger.info(f"[VIDEO_SEEK] from={current_time_ms}ms to={ms}ms delta={ms - current_time_ms:+d}ms")

            # CRITICAL: Check playback state BEFORE seek
            was_playing = self.player.is_playing()  # ← Mover ANTES de state check
            state = self.player.get_state()

            # If video ended, need to stop() and play() to fully reset
            if state == vlc.State.Ended:
                logger.debug("Video ended, performing full reset before seek")
                self.player.stop()
                QTimer.singleShot(50, lambda: self._restart_and_seek(ms, was_playing))
                return

            # Normal seek (not ended)
            self.player.set_time(ms)

            # CRITICAL: Preserve pause state after seek
            if not was_playing:
                # VLC sometimes auto-resumes after set_time() - force pause
                QTimer.singleShot(50, self._ensure_paused)  # ← Nuevo método
                logger.debug("Video was paused - preserving pause state after seek")

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

    def _ensure_paused(self):
        """Ensure player remains paused after seek.

        VLC sometimes auto-resumes after set_time() on certain platforms.
        This method enforces pause state to prevent unwanted playback.
        """
        if self.player is not None and self.player.is_playing():
            self.player.pause()
            logger.debug("Enforced pause state after seek (VLC auto-resumed)")

    def _report_position(self):
        """
        Reportar posición actual al SyncController.
        Se llama periodicamente durante la reproducción.

        FASE 5.1: No reporta si video está deshabilitado.
        """
        # Skip if video is disabled
        if self._video_auto_disabled:
            return

        if self.player.is_playing() and self.sync_controller:
            video_ms = self.player.get_time()
            video_seconds = video_ms / 1000.0
            self.sync_controller.on_video_position_updated(video_seconds)

    @Slot(dict)
    def apply_correction(self, correction: dict):
        """
        Ejecutar corrección de sincronización emitida por SyncController.

        Args:
            correction: dict con 'type' y parámetros según tipo:
                - 'elastic': new_rate (playback rate adjustment)
                - 'rate_reset': new_rate (reset to 1.0)
                - 'hard': new_time_ms (seek directo)

        FASE 5.1: No ejecuta si video está deshabilitado.
        """
        # FASE 5.1: Skip if video is disabled
        if self._video_auto_disabled:
            return

        if not self.player.is_playing():
            return

        corr_type = correction.get('type')
        drift_ms = correction.get('drift_ms', 0)

        if corr_type == 'elastic':
            # Elastic correction: Adjust playback rate
            new_rate = correction.get('new_rate', 1.0)
            current_rate = correction.get('current_rate', 1.0)
            self.player.set_rate(new_rate)
            logger.debug(
                f"[ELASTIC] drift={drift_ms:+d}ms "
                f"rate: {current_rate:.3f} → {new_rate:.3f}"
            )

        elif corr_type == 'rate_reset':
            # Reset rate to normal
            self.player.set_rate(1.0)
            logger.debug(f"[RATE_RESET] drift={drift_ms:+d}ms → rate=1.0")

        elif corr_type == 'hard':
            # Hard correction: Seek directo
            new_time_ms = correction.get('new_time_ms')
            self.player.set_time(int(new_time_ms))
            # Reset rate after hard seek
            if correction.get('reset_rate', False):
                self.player.set_rate(1.0)
            logger.debug(f"[HARD] drift={drift_ms:+d}ms → seek to {new_time_ms}ms")

        elif corr_type == 'soft':
            # Legacy soft correction (deprecated, kept for compatibility)
            new_time_ms = correction.get('new_time_ms')
            adjustment_ms = correction.get('adjustment_ms', 0)
            self.player.set_time(int(new_time_ms))
            logger.debug(f"[SOFT] diff={drift_ms}ms adj={adjustment_ms}ms → {new_time_ms}ms")

    def closeEvent(self, event):
        """Limpiar recursos al cerrar."""
        with safe_operation("Cleaning up video player resources", silent=True):
            self.stop()
            self.position_timer.stop()
            app_state.video_is_playing = False
            self.player.release()
            self.instance.release()
        super().closeEvent(event)
