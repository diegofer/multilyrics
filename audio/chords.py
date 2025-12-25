# crear clase ChordExtractorWorker con madmom
from madmom.features.chords import CRFChordRecognitionProcessor, CNNChordFeatureProcessor
from PySide6.QtCore import QObject, Signal, Slot
import warnings
from pathlib import Path

from core import global_state
from .meta import MetaJson


class WorkerChordsSignals(QObject):
    finished = Signal()
    error = Signal(str)
    result = Signal(str)
class ChordExtractorWorker(QObject):
    """Worker class for extracting chords from audio using madmom."""
    def __init__(self, audio_path: str = None):
        """
        Initializes the worker.

        :param audio_path: The full path to the audio file to analyze.
        """
        super().__init__()
        self.audio_path = audio_path
        self.signals = WorkerChordsSignals()

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

            # Initialize the chord recognition processor
            feat_proc = CNNChordFeatureProcessor()
            decode_proc = CRFChordRecognitionProcessor()
            feats = feat_proc(self.audio_path)
            chords = decode_proc(feats)
            print(f"[INFO] Chords extracted: {chords}")

            # Clean and format chords for metadata Quitar ':maj' y cambiar ':min' por 'm'
            chord_list = []
            for start, end, label in chords:
                start_c = round(start, 3)
                end_c = round(end, 3)
                clean_label = label.replace(':maj', '').replace(':min', 'm')
                chord_list.append((start_c, end_c, clean_label))

            print(f"[DEBUG] Formatted chords: {chord_list}")
            meta_json = MetaJson(Path(self.audio_path).with_name(global_state.META_FILE_PATH))
            meta_json.update_meta({
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

# Example usage
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QThread
    import sys  
    app = QApplication(sys.argv)
    audio_path = "example.wav"  # Replace with a valid audio file
    def print_chords(chord_data):
        print(f"Extracted Chords: {chord_data}")
    def print_error(msg):
        print(f"Error: {msg}")
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

