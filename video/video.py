import platform
from pathlib import Path

import vlc
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from core.config_manager import ConfigManager
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

    # Signal emitida cuando la ventana se cierra con el botón X
    window_closed = Signal()

    def __init__(self, screen_index=1):
        super().__init__()

        self.screen_index = screen_index
        self.setWindowTitle("VideoLyrics")
        self.resize(800, 600)

        # Detectar SO
        self.system = platform.system()
        logger.debug(f"SO detectado: {self.system}")

        # STEP 3: Initialize with video mode from ConfigManager
        config = ConfigManager.get_instance()
        self._video_mode = config.get("video.mode", "full")  # "full" | "loop" | "static" | "none"
        logger.info(f"🎬 VideoLyrics initialized with mode: {self._video_mode}")

        # Legacy hardware detection (kept for future use)
        self._is_legacy_hardware = self._detect_legacy_hardware()
        if self._is_legacy_hardware:
            logger.warning(
                "⚠️ Hardware antiguo detectado. "
                "Modo de video configurado en Settings puede afectar rendimiento."
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

        # STEP 5: Setup event callback for detecting when video ends
        event_manager = self.player.event_manager()
        event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_video_end)

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
        # Flag para modo fallback (ventana 16:9 en pantalla primaria)
        self._is_fallback_mode = False

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
        """Verificar si el video está habilitado (backward compatibility).

        Returns:
            bool: True si video puede reproducirse (no es mode 'none')
        """
        return self._video_mode != "none"

    def get_video_mode(self) -> str:
        """Get current video mode.

        Returns:
            str: Current mode ("full" | "loop" | "static" | "none")
        """
        return self._video_mode

    def set_video_mode(self, mode: str):
        """Set video playback mode.

        Args:
            mode: Video mode ("full" | "loop" | "static" | "none")
        """
        if mode not in ["full", "loop", "static", "none"]:
            logger.error(f"❌ Invalid video mode: {mode}. Using 'full' as fallback.")
            mode = "full"

        old_mode = self._video_mode
        self._video_mode = mode
        logger.info(f"🎬 Video mode changed: {old_mode} → {mode}")

        # Stop playback if switching to 'none'
        if mode == "none" and self.player.is_playing():
            self.stop()

    def enable_video(self, enable: bool = True):
        """DEPRECATED: Use set_video_mode() or ConfigManager instead.

        This method is kept for backward compatibility but will be removed
        in a future version. Use ConfigManager.set("video.mode", "none")
        to disable video, or set_video_mode() for fine-grained control.

        Args:
            enable: True para habilitar video, False para deshabilitar
        """
        import warnings
        warnings.warn(
            "enable_video() is deprecated. Use set_video_mode() or ConfigManager instead.",
            DeprecationWarning,
            stacklevel=2
        )

        # Map to video modes for backward compatibility
        if enable:
            # Re-enable: restore to previous mode or use recommended
            if self._video_mode == "none":
                config = ConfigManager.get_instance()
                restored_mode = config.get("video.mode", "full")
                self.set_video_mode(restored_mode)
        else:
            # Disable: switch to 'none' mode
            self.set_video_mode("none")

    def set_media(self, video_path):
        """Cargar un archivo de video respetando el modo configurado."""
        # STEP 6: Always sync mode from config before loading media
        # This ensures changes in Settings are respected when loading new songs
        current_mode = ConfigManager.get_instance().get("video.mode", "full")
        if current_mode and current_mode != self._video_mode:
            logger.info(f"📹 Updating video mode from settings: {self._video_mode} → {current_mode}")
            self._video_mode = current_mode

        # STEP 4: Si mode es 'none', no cargar nada
        if self._video_mode == "none":
            logger.info("📹 Video mode is 'none' - skipping video load")
            return

        # STEP 4: Si mode es 'loop', siempre usar loop (ignorar video del multi)
        if self._video_mode == "loop":
            config = ConfigManager.get_instance()
            loop_path = config.get("video.loop_video_path", "assets/loops/default.mp4")
            video_path = loop_path
            logger.info(f"📹 Loop mode active - using loop video: {video_path}")

        # STEP 4: Si mode es 'static', usar video del multi o fallback a loop
        elif self._video_mode == "static":
            if video_path is None or not Path(video_path).exists():
                logger.warning(f"📹 No video file for static mode: {video_path}")
                config = ConfigManager.get_instance()
                loop_path = config.get("video.loop_video_path", "assets/loops/default.mp4")
                video_path = loop_path
                logger.info(f"📹 Fallback to loop for static frame: {video_path}")

        # STEP 4: Si mode es 'full', usar video del multi o fallback a loop
        elif self._video_mode == "full":
            if video_path is None or not Path(video_path).exists():
                logger.warning(f"📹 Multi has no video file: {video_path}")
                logger.info("🔄 Switching to 'loop' mode and loading default loop")
                self._video_mode = "loop"
                config = ConfigManager.get_instance()
                loop_path = config.get("video.loop_video_path", "assets/loops/default.mp4")
                video_path = loop_path
                logger.info(f"📹 Using loop video: {video_path}")

        if self.player.is_playing():
            self.player.stop()
            app_state.video_is_playing = False
            logger.debug("Reproductor detenido")

        media = self.instance.media_new(str(video_path))
        # Deshabilitar audio del video - el audio será controlado por el AudioEngine
        media.add_option("--no-audio")

        self.player.set_media(media)
        media.release()
        logger.debug(f"📹 Video cargado: {video_path} (mode: {self._video_mode})")

        # STEP 5: Log loop mode activation for debugging
        if self._video_mode == "loop":
            logger.info("🔄 Loop mode: Will use timer-based loop boundary detection")

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
            if self._is_fallback_mode:
                # Modo ventana: mostrar normal (no fullscreen)
                self.showNormal()
            else:
                # Modo pantalla secundaria: fullscreen
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
        """Mover ventana a pantalla secundaria y adjuntar VLC.

        Si la pantalla secundaria no existe, hace fallback automático a modo ventana
        16:9 en la pantalla primaria.
        """
        screens = QApplication.screens()
        logger.info(f"📺 Pantallas detectadas: {len(screens)}")
        for i, screen in enumerate(screens):
            dpi = screen.logicalDotsPerInch()
            size = screen.geometry()
            logger.info(f"  [{i}] {screen.name()} - Resolución: {size.width()}x{size.height()} @ {dpi} DPI")

        # FALLBACK: Si pantalla secundaria no existe, usar primaria en modo ventana
        if self.screen_index >= len(screens):
            logger.warning(
                f"⚠️ Pantalla {self.screen_index} no disponible (solo hay {len(screens)}). "
                f"Usando modo ventana 16:9 en pantalla primaria."
            )
            self._is_fallback_mode = True
            target_screen = screens[0]  # Pantalla primaria

            # Calcular geometría 16:9 centrada (80% del ancho de pantalla)
            primary_geo = target_screen.geometry()
            video_width = int(primary_geo.width() * 0.8)
            video_height = int(video_width * 9 / 16)  # Relación 16:9

            # Centrar en pantalla primaria
            x = primary_geo.x() + (primary_geo.width() - video_width) // 2
            y = primary_geo.y() + (primary_geo.height() - video_height) // 2

            logger.info(
                f"📐 Modo ventana: {video_width}x{video_height} @ ({x},{y}) "
                f"en {target_screen.name()}"
            )

            self._target_screen = target_screen

            # Configurar ventana en modo normal (no fullscreen)
            if self.windowHandle() is None:
                self.setAttribute(Qt.WA_NativeWindow, True)
            handle = self.windowHandle()
            if handle is not None:
                try:
                    handle.setScreen(target_screen)
                    logger.info(f"✓ Screen asignada vía windowHandle: {target_screen.name()}")
                except Exception as e:
                    logger.warning(f"⚠ No se pudo asignar pantalla vía windowHandle: {e}")

            self.setGeometry(x, y, video_width, video_height)
            self.show()
            QTimer.singleShot(100, self._attach_vlc_to_window)
            return

        # NORMAL: Pantalla secundaria existe, usar fullscreen
        self._is_fallback_mode = False
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

            # Finalmente, mostrar ventana (fullscreen solo si NO es modo fallback)
            handle = self.windowHandle()
            if handle is not None and self._target_screen is not None:
                try:
                    handle.setScreen(self._target_screen)
                except Exception:
                    pass

            if self._is_fallback_mode:
                # Modo ventana: NO entrar en fullscreen
                self.showNormal()
                logger.info("✓ Ventana en modo normal 16:9 (fallback)")
            else:
                # Pantalla secundaria: fullscreen
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
        # STEP 3: Handle different video modes
        if self._video_mode == "none":
            logger.debug("📹 Video mode is 'none' - skipping playback")
            return

        # Solo reproducir si la ventana está visible (usuario activó show_video_btn)
        if not self.isVisible():
            logger.debug("📹 Ventana de video oculta - saltando reproducción de video (audio continuará)")
            return

        logger.debug(f"⏯ Starting video playback in '{self._video_mode}' mode...")
        self.player.audio_set_mute(True)  # Asegurar que audio está muteado

        if self._video_mode == "full":
            # Full mode: Sync with audio + elastic corrections
            video_start_time = audio_time_seconds + offset_seconds
            if abs(video_start_time) > 0.001:
                video_ms = max(0, int(video_start_time * 1000))
                self.player.set_time(video_ms)
                logger.info(
                    f"[FULL] audio={audio_time_seconds:.3f}s "
                    f"offset={offset_seconds:+.3f}s → video_start={video_start_time:.3f}s"
                )
            self.player.play()
            self.position_timer.start()  # Report position for sync

        elif self._video_mode == "loop":
            # Loop mode: Play without sync, loop at boundaries
            self.player.set_time(0)  # Always start at beginning
            self.player.play()
            logger.info("[LOOP] Starting loop playback from 0s (no audio sync)")
            # Start loop boundary timer (1 Hz check)
            if not hasattr(self, '_loop_boundary_timer'):
                self._loop_boundary_timer = QTimer()
                self._loop_boundary_timer.setInterval(1000)  # 1 Hz
                self._loop_boundary_timer.timeout.connect(self._check_loop_boundary)
            self._loop_boundary_timer.start()

        elif self._video_mode == "static":
            # Static mode: Seek to frame and pause
            static_frame = 0  # TODO: Load from meta.json in Phase 2
            self.player.set_time(int(static_frame * 1000))
            self.player.play()
            # Pause after short delay to ensure frame is loaded
            QTimer.singleShot(100, lambda: self._ensure_static_frame())
            logger.info(f"[STATIC] Freezing at frame {static_frame}s")

        app_state.video_is_playing = True

        # Habilitar sincronización
        if self.sync_controller:
            self.sync_controller.start_sync()
            self.position_timer.start()

    def stop(self):
        """Detener reproducción y sincronización.

        STEP 5: Stop loop boundary timer if running.
        """
        app_state.video_is_playing = False
        self.player.stop()
        self.position_timer.stop()

        # STEP 5: Stop loop boundary timer if exists
        if hasattr(self, '_loop_boundary_timer') and self._loop_boundary_timer.isActive():
            self._loop_boundary_timer.stop()
            logger.debug("🔄 Loop boundary timer stopped")

        if self.sync_controller:
            self.sync_controller.stop_sync()

    def pause(self):
        """Pausar reproducción.

        STEP 5: Pause also stops loop boundary timer.
        """
        app_state.video_is_playing = False
        self.player.pause()
        self.position_timer.stop()

        # STEP 5: Stop loop boundary timer when paused
        if hasattr(self, '_loop_boundary_timer') and self._loop_boundary_timer.isActive():
            self._loop_boundary_timer.stop()

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

    def _check_loop_boundary(self):
        """Check if video reached end and restart loop (with hysteresis)."""
        # Always check if we're in loop mode
        if self._video_mode != "loop":
            return

        # Check player state
        if not self.player.is_playing():
            logger.debug("[LOOP] Player stopped - restarting loop")
            self.player.set_time(0)
            self.player.play()
            return

        video_ms = self.player.get_time()
        duration_ms = self.player.get_length()

        logger.debug(f"[LOOP_CHECK] video_ms={video_ms}, duration_ms={duration_ms}, mode={self._video_mode}")

        if duration_ms <= 0:
            logger.debug("[LOOP] Invalid duration, skipping")
            return  # Invalid duration

        # STEP 5: Restart if video is at or past 95% of duration
        # This is more reliable than checking exact end
        boundary_threshold = int(duration_ms * 0.95)
        if video_ms >= boundary_threshold:
            logger.info(f"[LOOP] Boundary reached ({video_ms}ms >= {boundary_threshold}ms) - scheduling restart")
            # Use Qt event loop to restart to avoid blocking
            QTimer.singleShot(0, self._restart_loop)


    def _ensure_static_frame(self):
        """Ensure video is paused for static mode."""
        if self._video_mode == "static":
            self.player.pause()
            logger.debug("[STATIC] Frame frozen")

    def _on_video_end(self, event):
        """Callback when VLC player reaches end of media.

        STEP 5: Handle loop mode automatically when video ends.
        """
        logger.info(f"[VLC_EVENT] Video ended (mode: {self._video_mode})")

        if self._video_mode == "loop":
            logger.info("[LOOP] VLC EndReached event - scheduling restart")
            # Run restart on Qt event loop to avoid VLC thread issues
            QTimer.singleShot(0, self._restart_loop)
        # For other modes, let VLC handle it naturally

    def _restart_loop(self):
        """Restart loop playback safely on the Qt event loop."""
        if self._video_mode != "loop":
            return
        try:
            self.player.set_time(0)
            self.player.play()
            logger.debug("[LOOP] Restarted from 0ms")
        except Exception as exc:
            logger.warning(f"[LOOP] Failed to restart loop: {exc}")

    def _report_position(self):
        """
        Reportar posición actual al SyncController.
        Se llama periodicamente durante la reproducción.

        STEP 3: Only report for 'full' mode (loop/static don't need sync).
        """
        # Only report position in full mode (needs sync corrections)
        if self._video_mode != "full":
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

        STEP 3: Only applies corrections in 'full' mode.
        """
        # STEP 3: Only apply corrections in full mode (loop/static don't sync)
        if self._video_mode != "full":
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
        """Interceptar cierre de ventana para prevenir destrucción de recursos.

        En lugar de cerrar, simplemente ocultamos la ventana y notificamos
        a main.py para sincronizar el estado del botón show_video_btn.

        IMPORTANTE: No pausamos ni detenemos el video porque el audio engine
        sigue corriendo y la timeline necesita actualizaciones de posición.
        """
        logger.debug("🚪 Interceptando cierre de ventana (botón X) - ocultando sin detener")

        # Emitir señal para sincronizar botón
        self.window_closed.emit()

        # Simplemente ocultar ventana sin tocar el playback
        # El video sigue reproduciéndose en segundo plano
        # El position_timer sigue activo para actualizar timeline
        self.hide()

        # IMPORTANTE: Ignorar el evento de cierre para prevenir destrucción
        event.ignore()
