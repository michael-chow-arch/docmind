"""
Test logging configuration and request ID functionality.
"""
from __future__ import annotations

import logging
from unittest.mock import patch, MagicMock
from contextvars import ContextVar

from app.core.logging import configure_logging, get_logger, RequestIDFilter, set_request_id_var


class TestLoggingConfiguration:
    """Test logging configuration."""

    def test_configure_logging_sets_up_handlers(self):
        """Verify logging configuration sets up handlers correctly."""
        with patch("app.core.logging.settings") as mock_settings:
            mock_settings.LOG_LEVEL = "INFO"
            
            configure_logging()
            
            root_logger = logging.getLogger()
            assert len(root_logger.handlers) > 0
            assert root_logger.level == logging.INFO

    def test_get_logger_returns_logger(self):
        """Verify get_logger returns a logger instance."""
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_request_id_filter_adds_request_id(self):
        """Verify RequestIDFilter adds request_id to log records."""
        request_id_var = ContextVar("request_id", default=None)
        set_request_id_var(request_id_var)
        
        filter_obj = RequestIDFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )
        
        # Test without request ID
        result = filter_obj.filter(record)
        assert result is True
        assert hasattr(record, "request_id")
        assert record.request_id == "-"
        
        # Test with request ID
        request_id_var.set("test-request-123")
        record2 = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )
        filter_obj.filter(record2)
        assert record2.request_id == "test-request-123"
