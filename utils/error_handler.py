"""Error handling utilities for Multi Lyrics.

Provides context managers and decorators for consistent error handling
with automatic logging and optional error propagation.

Usage:
    # Context manager for safe operations
    with safe_operation("Loading audio file"):
        audio_player.load(path)
    
    # Silent operations (logs but doesn't raise)
    with safe_operation("Optional metadata update", silent=True):
        update_metadata()
    
    # Decorator for methods
    @safe_method("Playback operation")
    def play(self):
        self.audio_player.start()
"""

from contextlib import contextmanager
from functools import wraps
from typing import Optional, Callable, Any
import traceback

from core.logger import get_logger

logger = get_logger(__name__)


@contextmanager
def safe_operation(
    operation_name: str, 
    silent: bool = False,
    log_level: str = "warning",
    return_on_error: Any = None
):
    """Context manager for safe operations with automatic error logging.
    
    Captures exceptions, logs them with context, and optionally suppresses propagation.
    Useful for operations where failures should be logged but not crash the application.
    
    Args:
        operation_name: Human-readable description of the operation
        silent: If True, suppresses exception propagation (default: False)
        log_level: Logging level for errors - "debug", "info", "warning", "error" (default: "warning")
        return_on_error: Value to return if exception occurs (only relevant for silent mode)
    
    Yields:
        None
    
    Raises:
        Exception: Re-raises caught exception if silent=False
    
    Examples:
        >>> with safe_operation("Updating UI component"):
        ...     widget.update_value(new_val)  # Logs and raises on error
        
        >>> with safe_operation("Saving preferences", silent=True):
        ...     save_user_prefs()  # Logs but doesn't raise on error
    """
    try:
        yield
    except Exception as e:
        # Get the appropriate logger method based on log_level
        log_func = getattr(logger, log_level, logger.warning)
        
        # Log with full traceback for debugging
        log_func(
            f"Error during {operation_name}: {type(e).__name__}: {e}",
            exc_info=True
        )
        
        if not silent:
            raise


def safe_call(
    func: Callable,
    *args,
    operation_name: Optional[str] = None,
    silent: bool = True,
    default_return: Any = None,
    **kwargs
) -> Any:
    """Safely call a function with error handling.
    
    Wrapper function that executes a callable with automatic error handling.
    Useful for calling functions that might fail without crashing the caller.
    
    Args:
        func: Callable to execute
        *args: Positional arguments to pass to func
        operation_name: Description for logging (defaults to func.__name__)
        silent: If True, returns default_return on error; if False, re-raises
        default_return: Value to return if function fails and silent=True
        **kwargs: Keyword arguments to pass to func
    
    Returns:
        Result of func() if successful, or default_return if error and silent=True
    
    Raises:
        Exception: Re-raises if silent=False
    
    Examples:
        >>> result = safe_call(risky_function, arg1, arg2, default_return=[])
        >>> # Returns [] if risky_function fails
        
        >>> safe_call(player.seek, 10.5, operation_name="Seeking playback")
    """
    op_name = operation_name or f"calling {func.__name__}"
    
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.warning(
            f"Error during {op_name}: {type(e).__name__}: {e}",
            exc_info=True
        )
        if not silent:
            raise
        return default_return


def safe_method(operation_name: Optional[str] = None, silent: bool = True):
    """Decorator for methods with automatic error handling.
    
    Wraps instance methods with error handling and logging. Useful for
    methods where failures should be logged but not crash the application.
    
    Args:
        operation_name: Description for logging (defaults to method name)
        silent: If True, suppresses exceptions; if False, re-raises them
    
    Returns:
        Decorated function
    
    Examples:
        >>> class Player:
        ...     @safe_method("Audio playback")
        ...     def play(self):
        ...         self.audio.start()
        
        >>> class Widget:
        ...     @safe_method()  # Uses method name as operation_name
        ...     def update_display(self):
        ...         self.refresh()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__name__}"
            with safe_operation(op_name, silent=silent):
                return func(*args, **kwargs)
        return wrapper
    return decorator


@contextmanager
def suppress_and_log(*exception_types, operation_name: str = "operation"):
    """Context manager that suppresses specific exception types and logs them.
    
    Similar to contextlib.suppress but adds logging. Useful for operations
    where specific exceptions are expected and should be handled gracefully.
    
    Args:
        *exception_types: Exception classes to suppress (e.g., FileNotFoundError, ValueError)
        operation_name: Description for logging
    
    Yields:
        None
    
    Examples:
        >>> with suppress_and_log(FileNotFoundError, operation_name="Loading config"):
        ...     config = load_config("optional_config.json")
        ...     # FileNotFoundError is logged but not raised
        
        >>> with suppress_and_log(ValueError, KeyError, operation_name="Parsing metadata"):
        ...     parse_user_metadata(data)
    """
    try:
        yield
    except exception_types as e:
        logger.info(
            f"Suppressed {type(e).__name__} during {operation_name}: {e}"
        )


def log_exception(
    exception: Exception,
    context: str = "",
    level: str = "error",
    include_traceback: bool = True
):
    """Log an exception with optional context.
    
    Utility function for explicit exception logging when you want to handle
    the exception yourself but still log it properly.
    
    Args:
        exception: The exception to log
        context: Additional context description
        level: Log level - "debug", "info", "warning", "error", "critical"
        include_traceback: Whether to include full traceback
    
    Examples:
        >>> try:
        ...     risky_operation()
        ... except ValueError as e:
        ...     log_exception(e, "During data validation", level="warning")
        ...     use_default_value()
    """
    log_func = getattr(logger, level, logger.error)
    
    prefix = f"{context}: " if context else ""
    message = f"{prefix}{type(exception).__name__}: {exception}"
    
    if include_traceback:
        log_func(message, exc_info=True)
    else:
        log_func(message)


class ErrorAccumulator:
    """Accumulates errors during batch operations.
    
    Useful when processing multiple items where you want to collect all errors
    instead of failing on the first one.
    
    Examples:
        >>> errors = ErrorAccumulator()
        >>> for file in files:
        ...     with errors.catch(f"Processing {file}"):
        ...         process_file(file)
        >>> 
        >>> if errors.has_errors():
        ...     print(f"Failed: {errors.count()} / {len(files)}")
        ...     errors.log_all()
    """
    
    def __init__(self):
        self.errors: list[tuple[str, Exception]] = []
    
    @contextmanager
    def catch(self, operation_name: str):
        """Context manager to catch and store errors."""
        try:
            yield
        except Exception as e:
            self.errors.append((operation_name, e))
            logger.debug(f"Error caught during {operation_name}: {e}")
    
    def has_errors(self) -> bool:
        """Check if any errors were caught."""
        return len(self.errors) > 0
    
    def count(self) -> int:
        """Return number of errors caught."""
        return len(self.errors)
    
    def log_all(self, level: str = "warning"):
        """Log all accumulated errors."""
        if not self.errors:
            return
        
        log_func = getattr(logger, level, logger.warning)
        log_func(f"Accumulated {len(self.errors)} errors:")
        for operation, error in self.errors:
            log_func(f"  - {operation}: {type(error).__name__}: {error}")
    
    def clear(self):
        """Clear all accumulated errors."""
        self.errors.clear()
    
    def get_errors(self) -> list[tuple[str, Exception]]:
        """Get list of (operation_name, exception) tuples."""
        return self.errors.copy()
