from PySide6.QtCore import QObject, Signal, Slot
import ffmpeg
from pathlib import Path
from core import global_state
from utils.logger import get_logger
from core.workers import WorkerSignals

from models.meta import MetaJson

logger = get_logger(__name__)

class AudioExtractWorker(QObject):
    """
    Clase de trabajo que ejecuta la extracción de audio usando FFmpeg
    en un hilo separado (usando QThreadPool o QThread).
    """

    def __init__(self, video_path: str):
        """
        Inicializa el worker.

        :param ruta_video: La ruta completa del archivo de video.
        :param ruta_salida: La ruta de salida deseada para el archivo WAV.
                            Si es None o una cadena vacía, se calculará automáticamente.
        """
        super().__init__()
        self.video_path = video_path
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        logger.info("Iniciando extracción de audio en worker...")
        # 1. Verificar la existencia del archivo de video primero
        if not Path(self.video_path).exists():
            self.signals.error.emit(f"Error: El archivo de video no existe en '{self.video_path}'")
            self.signals.finished.emit()
            return

        # 2. Determinar rutas de salida
        master_track_path = Path(self.video_path).with_name(global_state.MASTER_TRACK)
        meta_file_path = Path(self.video_path).with_name(global_state.META_FILE_PATH)
 
        # 3. Ejecutar la extracción de audio con FFmpeg
        try:
            (
                ffmpeg
                .input(self.video_path)
                .output(
                    filename=master_track_path,  # Usar la ruta de salida final determinada
                    vn=None,           # No video
                    acodec='pcm_s16le', # Codec de audio PCM sin comprimir (16-bit little-endian)
                    ar=44100,          # Frecuencia de muestreo (44.1 kHz)
                    ac=2               # Canales de audio (Estéreo)
                )
                .overwrite_output()    # Sobrescribir el archivo de salida si existe
                .run(capture_stdout=True, capture_stderr=True)
            )

            metadatos = self._extract_metadata()
            logger.debug(f"Metadatos extraídos: {metadatos}")
           
            # Crear o actualizar el archivo meta.json
            meta_json = MetaJson(meta_file_path)
            meta_json.update_meta(metadatos)

            logger.info(f"Extracción completada: audio={master_track_path}, metadata={meta_file_path}")
            self.signals.result.emit(str(master_track_path))

        except ffmpeg.Error as e:
            # Manejar errores específicos de FFmpeg y mostrar su salida de error
            error_msg = f"Error al ejecutar FFmpeg:\n{e.stderr.decode('utf8', errors='ignore')}"
            logger.error(error_msg)
            self.signals.error.emit(error_msg)
        
        except FileNotFoundError:
            # Manejar el caso donde el ejecutable de FFmpeg no se encuentra
            error_msg = "Error: Asegúrate de que FFmpeg esté instalado y accesible en el PATH del sistema."
            logger.error(error_msg)
            self.signals.error.emit(error_msg)
            
        finally:
            # Siempre emite 'finished' al terminar.
            self.signals.finished.emit()


    def _extract_metadata(self):
        """
        Extrae metadatos del archivo de video usando ffmpeg.probe.

        :return: Diccionario con metadatos extraídos (título, artista).
        """
        try:
            probe = ffmpeg.probe(self.video_path)
            tags = probe.get('format', {}).get('tags', {})
            title = tags.get('title') or tags.get('TITLE') or "Desconocido"
            artist = tags.get('artist') or tags.get('ARTIST') or "Desconocido"
            year = tags.get('date') or tags.get('DATE') or ""
            duration = round(float(probe.get('format', {}).get('duration', 0.0)), 2)  # Round to 2 decimals

            metadatos = {
                "title": title,  # Legacy
                "artist": artist,  # Legacy
                "track_name": title,  # Original for search (immutable)
                "artist_name": artist,  # Original for search (immutable)
                "track_name_display": title,  # Clean display (starts same, user can edit)
                "artist_name_display": artist,  # Clean display (starts same, user can edit)
                "year": year,
                "duration": duration,  # Legacy
                "duration_seconds": duration  # Normalized
            }

            return metadatos

        except ffmpeg.Error as e:
            error_msg = f"❌ Error al extraer metadatos con FFmpeg:\n{e.stderr.decode('utf8', errors='ignore')}"
            self.signals.error.emit(error_msg)
            return {}
        except Exception as e:
            self.signals.error.emit(f"❌ Error inesperado al extraer metadatos: {str(e)}")
            return {}