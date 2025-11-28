from PySide6.QtCore import QObject, Signal, Slot
import ffmpeg
import os
import global_state

class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(str)
    result = Signal(str, str)

class AudioExtractWorker(QObject):
    """
    Clase de trabajo que ejecuta la extracción de audio usando FFmpeg
    en un hilo separado (usando QThreadPool o QThread).
    """

    def __init__(self, ruta_video: str, ruta_salida: str = None):
        """
        Inicializa el worker.

        :param ruta_video: La ruta completa del archivo de video.
        :param ruta_salida: La ruta de salida deseada para el archivo WAV.
                            Si es None o una cadena vacía, se calculará automáticamente.
        """
        super().__init__()
        self.ruta_video = ruta_video
        self.ruta_salida = ruta_salida
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        """
        Función principal que se ejecuta en el hilo para realizar la extracción.
        Aplica la lógica de ruta de salida por defecto.
        """
        # 1. Verificar la existencia del archivo de video primero
        if not os.path.exists(self.ruta_video):
            self.signals.error.emit(f"Error: El archivo de video no existe en '{self.ruta_video}'")
            self.signals.finished.emit()
            return

        # 2. Determinar la ruta de audio final
        ruta_audio_final = self.ruta_salida

        # Si no se proveyó una ruta de salida, calcular el valor por defecto
        if not ruta_audio_final:
            # Obtener el directorio del video
            directorio_video = os.path.dirname(self.ruta_video)
            
            # Si os.path.dirname() devuelve una cadena vacía (ej. si solo se pasó un nombre de archivo),
            # usamos el directorio de trabajo actual.
            if not directorio_video:
                directorio_video = os.path.abspath(os.getcwd())

            # Construir la ruta final usando "master.wav" como nombre de archivo
            # Usamos WAV porque el codec 'pcm_s16le' es de audio sin comprimir.
            ruta_audio_final = os.path.join(directorio_video, global_state.MASTER_TRACK)
            
            print(f"Ruta de salida no provista. Usando la ruta por defecto: {ruta_audio_final}")


        # 3. Ejecutar la extracción de audio con FFmpeg
        try:
            (
                ffmpeg
                .input(self.ruta_video)
                .output(
                    ruta_audio_final,  # Usar la ruta de salida final (provista o por defecto)
                    vn=None,           # No video
                    acodec='pcm_s16le', # Codec de audio PCM sin comprimir (16-bit little-endian)
                    ar=44100,          # Frecuencia de muestreo (44.1 kHz)
                    ac=2               # Canales de audio (Estéreo)
                )
                .overwrite_output()    # Sobrescribir el archivo de salida si existe
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            mensaje_exito = f"✅ Extracción de audio completada con éxito. Archivo guardado en: {ruta_audio_final}"
            self.signals.result.emit(mensaje_exito, ruta_audio_final)

        except ffmpeg.Error as e:
            # Manejar errores específicos de FFmpeg y mostrar su salida de error
            error_msg = f"❌ Error al ejecutar FFmpeg:\n{e.stderr.decode('utf8', errors='ignore')}"
            self.signals.error.emit(error_msg)
        
        except FileNotFoundError:
            # Manejar el caso donde el ejecutable de FFmpeg no se encuentra
            error_msg = "❌ Error: Asegúrate de que FFmpeg esté instalado y accesible en el PATH del sistema."
            self.signals.error.emit(error_msg)
            
        finally:
            # Siempre emite 'finished' al terminar.
            self.signals.finished.emit()