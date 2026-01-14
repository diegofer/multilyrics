"""Extraction orchestrator for coordinating multi-stage audio processing.

Manages the complete pipeline of video-to-multi conversion:
1. Audio extraction (FFmpeg)
2. Beat/downbeat detection (madmom)
3. Chord recognition (madmom)
4. Lyrics search

Provides clean separation of concerns and thread management for
long-running audio analysis tasks.
"""

from typing import Callable, Optional
from pathlib import Path
from PySide6.QtCore import QObject, QThread, Signal, Slot

from core.extract import AudioExtractWorker
from core.beats import BeatsExtractorWorker
from core.chords import ChordExtractorWorker
from utils.logger import get_logger

logger = get_logger(__name__)


class ExtractionOrchestrator(QObject):
    """Coordinates the multi-stage extraction and analysis pipeline.
    
    This class encapsulates the complexity of managing multiple sequential
    worker threads (extraction → beats → chords) with proper signal routing,
    error handling, and resource cleanup.
    
    Signals:
        extraction_started: Emitted when extraction pipeline begins
        stage_changed: Emitted with stage name when moving to next stage
        extraction_completed: Emitted when full pipeline completes successfully (audio_path)
        extraction_error: Emitted when any stage fails (error_message)
    
    Usage:
        >>> orchestrator = ExtractionOrchestrator(parent)
        >>> orchestrator.extraction_completed.connect(on_complete)
        >>> orchestrator.extraction_error.connect(on_error)
        >>> orchestrator.start_extraction(video_path)
    """
    
    # Signals for external monitoring
    extraction_started = Signal()
    stage_changed = Signal(str)  # Stage name: "audio", "beats", "chords", "lyrics"
    extraction_completed = Signal(str)  # Final audio path
    extraction_error = Signal(str)  # Error message
    
    def __init__(self, 
                 status_callback: Optional[Callable[[str], None]] = None,
                 parent: QObject = None):
        """Initialize the orchestrator.
        
        Args:
            status_callback: Optional callback for status updates (e.g., StatusBar)
            parent: Parent QObject for Qt hierarchy
        """
        super().__init__(parent)
        
        self.status_callback = status_callback
        
        # Thread and worker references (managed lifecycle)
        self.thread: Optional[QThread] = None
        self.extract_worker: Optional[AudioExtractWorker] = None
        self.beats_worker: Optional[BeatsExtractorWorker] = None
        self.chords_worker: Optional[ChordExtractorWorker] = None
        
        self._is_running = False
    
    def start_extraction(self, video_path: str) -> None:
        """Start the extraction pipeline for a video file.
        
        Creates workers, configures signal routing, and starts the thread.
        Safe to call multiple times (cleans up previous extraction if running).
        
        Args:
            video_path: Absolute path to video file (.mp4, etc.)
        
        Raises:
            ValueError: If video_path is empty or None
        """
        if not video_path:
            raise ValueError("video_path cannot be empty")
        
        # Clean up any existing extraction
        if self._is_running:
            logger.warning("Extraction already running, stopping previous extraction")
            self.stop_extraction()
        
        logger.info(f"Iniciando extracción: {video_path}")
        self._is_running = True
        self.extraction_started.emit()
        
        # Create thread and workers
        self.thread = QThread()
        self.extract_worker = AudioExtractWorker(video_path)
        self.beats_worker = BeatsExtractorWorker()
        self.chords_worker = ChordExtractorWorker()
        
        # Move workers to thread
        self.extract_worker.moveToThread(self.thread)
        self.beats_worker.moveToThread(self.thread)
        self.chords_worker.moveToThread(self.thread)
        
        # Connect pipeline: extract → beats → chords
        self._connect_pipeline_signals()
        
        # Connect error handling
        self._connect_error_signals()
        
        # Connect cleanup signals
        self._connect_cleanup_signals()
        
        # Update status
        self._update_status("Procesando archivo: extrayendo audio...")
        
        # Start the thread (extract_worker.run will be called first)
        self.thread.start()
    
    def stop_extraction(self) -> None:
        """Stop ongoing extraction and clean up resources.
        
        Safe to call even if no extraction is running.
        """
        if not self._is_running:
            return
        
        logger.info("Deteniendo extracción...")
        
        # Request thread interruption
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait(2000)  # Wait up to 2 seconds
        
        self._cleanup()
        self._is_running = False
    
    def is_running(self) -> bool:
        """Check if extraction is currently running."""
        return self._is_running
    
    def _connect_pipeline_signals(self) -> None:
        """Configure sequential pipeline: extract → beats → chords."""
        # Start extraction when thread starts
        self.thread.started.connect(self.extract_worker.run)
        
        # Chain workers DIRECTLY: result of one triggers next IN THE WORKER THREAD
        self.extract_worker.signals.result.connect(self.beats_worker.run)
        self.beats_worker.signals.result.connect(self.chords_worker.run)
        
        # Status updates from orchestrator (safe - just emit signals, no blocking work)
        self.extract_worker.signals.result.connect(self._on_audio_extracted)
        self.beats_worker.signals.result.connect(self._on_beats_extracted)
        self.chords_worker.signals.result.connect(self._on_chords_extracted)
        
        # Log completion of each stage
        self.extract_worker.signals.finished.connect(
            lambda: logger.debug("Extracción de audio completada")
        )
        self.beats_worker.signals.finished.connect(
            lambda: logger.debug("Análisis de beats completado")
        )
        self.chords_worker.signals.finished.connect(
            lambda: logger.debug("Análisis de acordes completado")
        )
    
    def _connect_error_signals(self) -> None:
        """Connect error handlers for all workers."""
        self.extract_worker.signals.error.connect(self._on_worker_error)
        self.beats_worker.signals.error.connect(self._on_worker_error)
        self.chords_worker.signals.error.connect(self._on_worker_error)
    
    def _connect_cleanup_signals(self) -> None:
        """Configure resource cleanup when pipeline finishes."""
        # Quit thread when final worker finishes
        self.chords_worker.signals.finished.connect(self.thread.quit)
        
        # Delete workers when finished
        self.chords_worker.signals.finished.connect(self.chords_worker.deleteLater)
        self.beats_worker.signals.finished.connect(self.beats_worker.deleteLater)
        self.extract_worker.signals.finished.connect(self.extract_worker.deleteLater)
        
        # Delete thread when it finishes
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._on_thread_finished)
    
    @Slot(str)
    def _on_audio_extracted(self, audio_path: str) -> None:
        """Audio extraction completed - update UI status only."""
        self.stage_changed.emit("beats")
        self._update_status("Analizando beats y tempo...")
    
    @Slot(str)
    def _on_beats_extracted(self, audio_path: str) -> None:
        """Beat detection completed - update UI status only."""
        self.stage_changed.emit("chords")
        self._update_status("Detectando acordes...")
    
    @Slot(str)
    def _on_chords_extracted(self, audio_path: str) -> None:
        """Chord recognition completed - pipeline finished."""
        self.stage_changed.emit("lyrics")
        self._update_status("Buscando letras...")
        logger.info(f"Pipeline completado: {audio_path}")
        self.extraction_completed.emit(audio_path)
    
    @Slot(str)
    def _on_worker_error(self, error_message: str) -> None:
        """Handle error from any worker."""
        logger.error(f"Error en pipeline de extracción: {error_message}")
        self.extraction_error.emit(error_message)
        self._cleanup()
        self._is_running = False
    
    @Slot()
    def _on_thread_finished(self) -> None:
        """Thread finished, final cleanup."""
        logger.debug("Thread de extracción finalizado")
        self._is_running = False
    
    def _update_status(self, message: str) -> None:
        """Update status via callback if provided."""
        if self.status_callback:
            self.status_callback(message)
    
    def _cleanup(self) -> None:
        """Internal cleanup of references."""
        self.thread = None
        self.extract_worker = None
        self.beats_worker = None
        self.chords_worker = None
