from __future__ import annotations

import logging
import sys
from typing import Any

from app.core.config import settings


_request_id_var = None


def set_request_id_var(var) -> None:
    global _request_id_var
    _request_id_var = var


class RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if _request_id_var is not None:
            record.request_id = _request_id_var.get() or "-"
        else:
            record.request_id = "-"
        return True


def _sanitize_value(value: Any, max_length: int = 200) -> str:
    if value is None:
        return "None"
    
    str_value = str(value)
    if len(str_value) > max_length:
        return f"{str_value[:max_length]}... (truncated, {len(str_value)} chars)"
    lower_value = str_value.lower()
    if any(keyword in lower_value for keyword in ["password", "secret", "api_key", "token"]):
        return "[REDACTED]"
    
    return str_value


def configure_logging() -> None:
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] [request_id=%(request_id)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestIDFilter())
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
