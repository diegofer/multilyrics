"""Base classes for worker threads in Multi Lyrics.

Provides common infrastructure for QThread-based workers that perform
long-running tasks (audio extraction, beat detection, chord recognition, etc.)
in background threads to keep the UI responsive.

Usage:
    class MyWorker(QObject):
        def __init__(self, input_path: str):
            super().__init__()
            self.input_path = input_path
            self.signals = WorkerSignals()
        
        @Slot()
        def run(self):
            try:
                result = process_data(self.input_path)
                self.signals.result.emit(result)
            except Exception as e:
                self.signals.error.emit(str(e))
            finally:
                self.signals.finished.emit()
"""

from PySide6.QtCore import QObject, Signal, Slot


class WorkerSignals(QObject):
    """Standard signal set for background worker threads.
    
    This class provides a consistent interface for all worker threads,
    simplifying thread management and error handling.
    
    Signals:
        finished: Emitted when the worker completes (success or failure)
        error: Emitted when an error occurs, passes error message string
        result: Emitted on successful completion, passes result data
        progress: Optional progress updates (value, max_value, message)
    
    Examples:
        >>> class AudioWorker(QObject):
        ...     def __init__(self):
        ...         super().__init__()
        ...         self.signals = WorkerSignals()
        ...
        ...     def run(self):
        ...         try:
        ...             data = load_audio()
        ...             self.signals.result.emit(data)
        ...         except Exception as e:
        ...             self.signals.error.emit(str(e))
        ...         finally:
        ...             self.signals.finished.emit()
    """
    
    # Emitted when worker finishes (regardless of success/failure)
    finished = Signal()
    
    # Emitted on error with error message
    error = Signal(str)
    
    # Emitted on success with result data (typically a string path)
    result = Signal(str)
    
    # Optional: progress updates (current, total, message)
    progress = Signal(int, int, str)


class BaseWorker(QObject):
    """Optional base class for workers with common functionality.
    
    Provides a structured pattern for worker implementation with
    automatic signal management and error handling.
    
    Subclasses should override the `do_work()` method to implement
    their specific task logic.
    
    Attributes:
        signals: WorkerSignals instance for communication
    
    Examples:
        >>> class DataProcessor(BaseWorker):
        ...     def __init__(self, data_path: str):
        ...         super().__init__()
        ...         self.data_path = data_path
        ...
        ...     def do_work(self) -> str:
        ...         # Process data and return result
        ...         processed = process(self.data_path)
        ...         return processed
    """
    
    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()
    
    @Slot()
    def run(self):
        """Execute the worker task with automatic error handling.
        
        This method wraps the subclass's `do_work()` method with
        proper signal emission and error handling. Subclasses should
        not override this method directly.
        """
        try:
            result = self.do_work()
            if result is not None:
                self.signals.result.emit(str(result))
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()
    
    def do_work(self) -> str:
        """Perform the worker's task and return result.
        
        Subclasses must override this method to implement their
        specific processing logic.
        
        Returns:
            Result data as string (typically a file path)
        
        Raises:
            Exception: Any error during processing
        """
        raise NotImplementedError("Subclasses must implement do_work()")
    
    def emit_progress(self, current: int, total: int, message: str = ""):
        """Helper to emit progress updates.
        
        Args:
            current: Current progress value
            total: Maximum progress value
            message: Optional progress message
        """
        self.signals.progress.emit(current, total, message)
