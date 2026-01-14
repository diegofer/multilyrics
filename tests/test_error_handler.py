"""Tests for core/error_handler.py

Tests for error handling utilities including context managers,
decorators, and error accumulation.
"""

import pytest
from utils.error_handler import (
    safe_operation,
    safe_call,
    safe_method,
    suppress_and_log,
    log_exception,
    ErrorAccumulator
)


class TestSafeOperation:
    """Tests for safe_operation context manager."""
    
    def test_safe_operation_success(self):
        """Test that safe_operation allows successful operations to complete."""
        result = []
        with safe_operation("Test operation"):
            result.append(1)
        assert result == [1]
    
    def test_safe_operation_raises_by_default(self):
        """Test that safe_operation raises exceptions by default (silent=False)."""
        with pytest.raises(ValueError):
            with safe_operation("Test operation"):
                raise ValueError("Test error")
    
    def test_safe_operation_silent_suppresses(self, caplog):
        """Test that safe_operation with silent=True suppresses exceptions."""
        result = []
        with safe_operation("Test operation", silent=True):
            raise ValueError("Test error")
        # No exception raised
        # Check that error was logged
        assert "Test operation" in caplog.text
        assert "ValueError" in caplog.text
    
    def test_safe_operation_log_level(self, caplog):
        """Test that safe_operation respects log_level parameter."""
        with caplog.at_level("ERROR"):
            with safe_operation("Test operation", silent=True, log_level="error"):
                raise ValueError("Test error")
        assert "ERROR" in caplog.text
        assert "Test operation" in caplog.text


class TestSafeCall:
    """Tests for safe_call function."""
    
    def test_safe_call_success(self):
        """Test that safe_call returns result on success."""
        def my_func(x, y):
            return x + y
        result = safe_call(my_func, 2, 3)
        assert result == 5
    
    def test_safe_call_returns_default_on_error(self):
        """Test that safe_call returns default_return on error when silent=True."""
        def failing_func():
            raise ValueError("Error")
        result = safe_call(failing_func, default_return="default", silent=True)
        assert result == "default"
    
    def test_safe_call_raises_when_not_silent(self):
        """Test that safe_call raises when silent=False."""
        def failing_func():
            raise ValueError("Error")
        with pytest.raises(ValueError):
            safe_call(failing_func, silent=False)
    
    def test_safe_call_with_kwargs(self):
        """Test that safe_call passes kwargs correctly."""
        def my_func(x, y=10):
            return x + y
        result = safe_call(my_func, 5, y=20)
        assert result == 25


class TestSafeMethod:
    """Tests for safe_method decorator."""
    
    def test_safe_method_success(self):
        """Test that safe_method allows successful methods to run."""
        class MyClass:
            @safe_method()
            def my_method(self):
                return "success"
        
        obj = MyClass()
        assert obj.my_method() == "success"
    
    def test_safe_method_suppresses_error(self, caplog):
        """Test that safe_method suppresses exceptions when silent=True (default)."""
        class MyClass:
            @safe_method()
            def failing_method(self):
                raise ValueError("Error")
        
        obj = MyClass()
        result = obj.failing_method()  # Should not raise
        assert result is None
        assert "failing_method" in caplog.text
    
    def test_safe_method_raises_when_not_silent(self):
        """Test that safe_method raises when silent=False."""
        class MyClass:
            @safe_method(silent=False)
            def failing_method(self):
                raise ValueError("Error")
        
        obj = MyClass()
        with pytest.raises(ValueError):
            obj.failing_method()
    
    def test_safe_method_custom_operation_name(self, caplog):
        """Test that safe_method respects custom operation_name."""
        class MyClass:
            @safe_method(operation_name="Custom operation")
            def my_method(self):
                raise ValueError("Error")
        
        obj = MyClass()
        obj.my_method()
        assert "Custom operation" in caplog.text


class TestSuppressAndLog:
    """Tests for suppress_and_log context manager."""
    
    def test_suppress_and_log_suppresses_specified_exceptions(self, caplog):
        """Test that suppress_and_log suppresses specified exception types."""
        with suppress_and_log(ValueError, operation_name="Test op"):
            raise ValueError("Test error")
        # No exception raised
        assert "Test op" in caplog.text
        assert "ValueError" in caplog.text
    
    def test_suppress_and_log_does_not_suppress_other_exceptions(self):
        """Test that suppress_and_log does not suppress other exception types."""
        with pytest.raises(TypeError):
            with suppress_and_log(ValueError, operation_name="Test op"):
                raise TypeError("Different error")
    
    def test_suppress_and_log_multiple_types(self, caplog):
        """Test that suppress_and_log handles multiple exception types."""
        with suppress_and_log(ValueError, KeyError, operation_name="Multi op"):
            raise KeyError("Key error")
        assert "Multi op" in caplog.text
        assert "KeyError" in caplog.text


class TestLogException:
    """Tests for log_exception function."""
    
    def test_log_exception_basic(self, caplog):
        """Test basic exception logging."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            log_exception(e, "During test")
        
        assert "During test" in caplog.text
        assert "ValueError" in caplog.text
        assert "Test error" in caplog.text
    
    def test_log_exception_without_context(self, caplog):
        """Test exception logging without context."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            log_exception(e)
        
        assert "ValueError" in caplog.text
        assert "Test error" in caplog.text
    
    def test_log_exception_custom_level(self, caplog):
        """Test exception logging with custom log level."""
        with caplog.at_level("WARNING"):
            try:
                raise ValueError("Test error")
            except ValueError as e:
                log_exception(e, level="warning")
        
        assert "WARNING" in caplog.text


class TestErrorAccumulator:
    """Tests for ErrorAccumulator class."""
    
    def test_error_accumulator_catches_errors(self):
        """Test that ErrorAccumulator catches and stores errors."""
        acc = ErrorAccumulator()
        
        with acc.catch("Operation 1"):
            raise ValueError("Error 1")
        
        with acc.catch("Operation 2"):
            raise KeyError("Error 2")
        
        assert acc.has_errors()
        assert acc.count() == 2
    
    def test_error_accumulator_continues_after_error(self):
        """Test that ErrorAccumulator allows execution to continue after errors."""
        acc = ErrorAccumulator()
        results = []
        
        with acc.catch("Op 1"):
            results.append(1)
            raise ValueError("Error")
        
        # Execution continues
        with acc.catch("Op 2"):
            results.append(2)
        
        assert results == [1, 2]
        assert acc.count() == 1
    
    def test_error_accumulator_get_errors(self):
        """Test that get_errors returns list of (operation, exception) tuples."""
        acc = ErrorAccumulator()
        
        with acc.catch("Op 1"):
            raise ValueError("Error 1")
        
        errors = acc.get_errors()
        assert len(errors) == 1
        assert errors[0][0] == "Op 1"
        assert isinstance(errors[0][1], ValueError)
        assert str(errors[0][1]) == "Error 1"
    
    def test_error_accumulator_clear(self):
        """Test that clear() removes all accumulated errors."""
        acc = ErrorAccumulator()
        
        with acc.catch("Op 1"):
            raise ValueError("Error")
        
        assert acc.has_errors()
        acc.clear()
        assert not acc.has_errors()
        assert acc.count() == 0
    
    def test_error_accumulator_log_all(self, caplog):
        """Test that log_all() logs all accumulated errors."""
        acc = ErrorAccumulator()
        
        with acc.catch("Op 1"):
            raise ValueError("Error 1")
        
        with acc.catch("Op 2"):
            raise KeyError("Error 2")
        
        acc.log_all()
        
        assert "Accumulated 2 errors" in caplog.text
        assert "Op 1" in caplog.text
        assert "ValueError" in caplog.text
        assert "Op 2" in caplog.text
        assert "KeyError" in caplog.text
    
    def test_error_accumulator_no_errors(self, caplog):
        """Test ErrorAccumulator behavior when no errors occur."""
        acc = ErrorAccumulator()
        
        with acc.catch("Op 1"):
            pass  # No error
        
        assert not acc.has_errors()
        assert acc.count() == 0
        
        acc.log_all()
        assert "Accumulated" not in caplog.text
