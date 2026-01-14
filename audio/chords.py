# crear clase ChordExtractorWorker con madmom
from madmom.features.chords import CRFChordRecognitionProcessor, CNNChordFeatureProcessor
from madmom.features.key import CNNKeyRecognitionProcessor, key_prediction_to_label
from PySide6.QtCore import QObject, Signal, Slot
import warnings
from pathlib import Path

from core import global_state
from models.meta import MetaJson
from core.logger import get_logger
from core.workers import WorkerSignals

logger = get_logger(__name__)


class ChordExtractorWorker(QObject):
    """Worker class for extracting chords from audio using madmom."""
    def __init__(self, audio_path: str = None):
        """
        Initializes the worker.

        :param audio_path: The full path to the audio file to analyze.
        """
        super().__init__()
        self.audio_path = audio_path
        self.signals = WorkerSignals()

    @Slot()
    def run(self, audio_path: str = None):
        """
        Main function that runs in the thread to perform chord extraction.
        """
        if audio_path is not None:
            self.audio_path = audio_path

        try:
            # Disable madmom warnings
            warnings.filterwarnings("ignore", category=UserWarning, module='madmom')

            # Initialize the key recognition processors
            key_proc = CNNKeyRecognitionProcessor()
            key_feats = key_proc(self.audio_path)
            key_label = key_prediction_to_label(key_feats)
            logger.info(f"Clave extraída: {key_label}")

            # Initialize the chord recognition processor
            feat_proc = CNNChordFeatureProcessor()
            decode_proc = CRFChordRecognitionProcessor()
            feats = feat_proc(self.audio_path)
            chords = decode_proc(feats)
            logger.info(f"Acordes extraídos: {len(chords)} cambios")

            # Clean and format chords for metadata Quitar ':maj' y cambiar ':min' por 'm'
            chord_list = []
            for start, end, label in chords:
                start_c = round(start, 3)
                end_c = round(end, 3)
                chord_clean = self.clean_chord_label(label)
                chord_list.append((start_c, end_c, chord_clean))

            logger.debug(f"Acordes formateados: {len(chord_list)} progresiones")
            meta_json = MetaJson(Path(self.audio_path).with_name(global_state.META_FILE_PATH))
            meta_json.update_meta({
                "key": key_label,
                "chords": chord_list
            })

            # Emit the result signal with the audio path for chaining
            self.signals.result.emit(str(self.audio_path))

        except Exception as e:
            # Emit the error signal if an exception occurs
            self.signals.error.emit(str(e))
        finally:
            # Emit the finished signal when done
            self.signals.finished.emit()

    def clean_chord_label(self, label):
        """
        Convierte la nomenclatura de Madmom a formato de cancionero estándar.
        """
        if label == "N":
            return "" # O podrías dejar "N" si prefieres marcar el silencio

        # 1. Manejo de Menores (A:min -> Am)
        label = label.replace(':min', 'm')
        
        # 2. Manejo de Mayores (C:maj -> C)
        label = label.replace(':maj', '')
        
        # 3. Manejo de Semidisminuidos (ej. B:hdim7 -> Bm7b5)
        # Madmom a veces usa 'hdim7' para half-diminished
        label = label.replace(':hdim7', 'm7b5')
        
        # 4. Manejo de Disminuidos (B:dim -> Bdim)
        label = label.replace(':dim', 'dim')
        
        # 5. Limpieza de colon (:) para séptimas y otras tensiones
        # Ej: G:7 -> G7, C:maj7 -> Cmaj7 (o C7 si ya quitaste maj)
        label = label.replace(':', '')
        
        return label

# Example usage
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QThread
    import sys  
    app = QApplication(sys.argv)
    audio_path = "example.wav"  # Replace with a valid audio file
    def print_chords(chord_data):
        logger.info(f"Extracted Chords: {chord_data}")
    def print_error(msg):
        logger.error(f"Error: {msg}")
    worker = ChordExtractorWorker(audio_path)
    worker.signals.result.connect(print_chords)
    worker.signals.error.connect(print_error)
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.signals.finished.connect(thread.quit)
    worker.signals.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.start()
    sys.exit(app.exec())

