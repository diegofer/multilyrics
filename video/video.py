import vlc
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtCore import QTimer

from core.global_state import app_state

class VideoLyrics(QWidget):
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

        # umbrales de sincronización
        self.SOFT_THRESHOLD = 80     # ms
        self.HARD_THRESHOLD = 300    # ms
        self.CORR_MAX_MS = 20        # ms por frame (micro-correcciones)

    def set_media(self, video_path):
        if self.player.is_playing():
            self.player.stop()
            app_state.video_is_playing = False
            print("[INFO] Reproductor detenido.") 
        
        media = self.instance.media_new(video_path)
        self.player.set_media(media)
        media.release()

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

    def start_playback(self):
        print("⏯ Reproduciendo video...")
        self.player.play()
        app_state.video_is_playing = True
    
    def stop(self):
        app_state.video_is_playing = False
        self.player.stop()
    
    def pause(self):
        app_state.video_is_playing = False
        self.player.pause()

    def closeEvent(self, event):
        try:
            self.stop()
            app_state.video_is_playing = False
            self.player.release()
            self.instance.release()
        except:
            pass
        super().closeEvent(event)

    # --------------------------------------------------------------------
    #   ALGORITMO CPU-FRIENDLY DE SINCRONIZACIÓN TIPO PLL
    # --------------------------------------------------------------------
    def sync_player(self, audio_time_seconds):
        print("SINCRONIZADOR EJECUTADO")
        audio_ms = int(audio_time_seconds * 1000)
        video_ms = self.player.get_time()

        diff = audio_ms - video_ms  # positivo → video atrasado

        # -------------------------
        #   CORRECCIÓN SUAVE
        # -------------------------
        if abs(diff) > self.SOFT_THRESHOLD and abs(diff) < self.HARD_THRESHOLD:
            correction = max(-self.CORR_MAX_MS,
                             min(self.CORR_MAX_MS, diff // 5))
            new_time = video_ms + correction
            self.player.set_time(new_time)
            print(f"[SOFT] diff={diff}ms corr={correction}ms → {new_time}")

        # -------------------------
        #   CORRECCIÓN DURA
        # -------------------------
        elif abs(diff) >= self.HARD_THRESHOLD:
            self.player.set_time(audio_ms)
            print(f"[HARD] salto directo → {audio_ms}")

        # Debug opcional
        else:
            print(f"[OK] diff={diff}ms (dentro del rango)")