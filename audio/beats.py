from PySide6.QtCore import QObject, Signal, Slot
import warnings, json
import numpy as np
from pathlib import Path

from madmom.features.downbeats import RNNDownBeatProcessor, DBNDownBeatTrackingProcessor
from madmom.features.tempo import TempoEstimationProcessor

from .meta import MetaJson
from core import global_state
from core.logger import get_logger
from core.workers import WorkerSignals

logger = get_logger(__name__)

class BeatsExtractorWorker(QObject):
    """
    Clase de trabajo que ejecuta el análisis de tempo usando madmom
    en un hilo separado (usando QThreadPool o QThread).
    """

    def __init__(self, audio_path: str = None):
        """
        Inicializa el worker.

        :param audio_path: La ruta completa del archivo de audio a analizar.
        """
        super().__init__()
        self.audio_path = audio_path
        self.signals = WorkerSignals()

    @Slot()
    def run(self, audio_path: str = None):
        """
        Función principal que se ejecuta en el hilo para realizar el análisis de tempo.
        """
        if audio_path is not None:
            self.audio_path = audio_path
    
        try:
            # Desactivar warnings de madmom
            warnings.filterwarnings("ignore", category=UserWarning, module='madmom')

            # 1. Cargamos el procesador de beats y downbeats (basado en Redes Neuronales)
            # Este procesador analiza la fuerza de los pulsos.
            proc = RNNDownBeatProcessor()

            # 2. Cargamos el decodificador (Dynamic Bayesian Network)
            # Este paso "limpia" la señal y decide qué pulsos son downbeats basándose en compases de 3 o 4 tiempos.
            post_proc = DBNDownBeatTrackingProcessor(beats_per_bar=[3, 4], fps=100)

            activations = proc(self.audio_path)
            beats_info = post_proc(activations)

            # 4. Separamos los resultados
            all_beats = beats_info[:, 0]  # Tiempos de todos los pulsos
            #downbeats = beats_info[beats_info[:, 1] == 1][:, 0]  # Tiempos donde la posición es '1'
            #print(f"[INFO] Pulsos detectados: {len(all_beats)}, Downbeats detectados: {len(downbeats)}")
            #print(f"[DEBUG] Primeros 5 pulsos: {all_beats[:5]}")
            #print(f"[DEBUG] Primeros 5 downbeats: {downbeats[:5]}")

            # 5. Estimamos el tempo promedio de los pulsos
            if len(all_beats) < 2:
                raise ValueError("No hay suficientes pulsos para estimar el tempo.")

            # Calcular intervalos entre beats
            intervals = np.diff(all_beats)
            avg_interval = np.mean(intervals)
            estimated_tempo = 60 / avg_interval if avg_interval > 0 else 0

            #calcular compass de 4/4 o 3/4 basado en la mediana de los intervalos
            median_interval = np.median(intervals)
            if 0.45 <= median_interval <= 0.55:
                compass = "4/4"
            elif 0.65 <= median_interval <= 0.75:
                compass = "3/4"
            else:
                compass = "?/?"

            # 6. Escribir a meta.json beats_info y tempo estimado
            meta_json = MetaJson(Path(self.audio_path).with_name(global_state.META_FILE_PATH))
            meta_json.update_meta({
                "tempo": estimated_tempo,
                "compass": compass,
                "beats": beats_info.tolist()
            })
      
            # Emitir el resultado
            self.signals.result.emit(self.audio_path)

        except Exception as e:
            # Emitir cualquier error que ocurra durante el proceso
            self.signals.error.emit(str(e))
            logger.error(f"Error en BeatsExtractorWorker: {e}", exc_info=True)
        finally:
            # Señalar que el trabajo ha terminado
            self.signals.finished.emit()

# Example usage
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QThread
    import sys

    app = QApplication(sys.argv)

    def print_tempo(bpm):
        logger.info(f"Estimated Tempo: {bpm} BPM")

    def print_error(msg):
        logger.error(f"Error: {msg}")

    worker = BeatsExtractorWorker("example.wav")
    worker.result.connect(print_tempo)
    worker.error.connect(print_error)

    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    thread.start()
    sys.exit(app.exec())