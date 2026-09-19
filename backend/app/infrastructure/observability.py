from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    """Emit stable, machine-readable application logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("request_id", "method", "path", "status_code", "duration_ms"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_http_logger(level: str) -> logging.Logger:
    logger = logging.getLogger("tramflow.http")
    logger.setLevel(level.upper())
    logger.propagate = False
    if not any(getattr(handler, "_tramflow_json", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        handler._tramflow_json = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    return logger
