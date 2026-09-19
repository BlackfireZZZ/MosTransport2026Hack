"""JSON responses for failures FastAPI does not already serialise.

FastAPI answers HTTPException and request validation with JSON, but an
unhandled exception falls through to Starlette's ServerErrorMiddleware, which
replies `text/plain` with the body `Internal Server Error`. A client that calls
.json() on every response then fails while decoding instead of surfacing the
error, which is how a backend fault turns into a confusing frontend crash.

The body deliberately carries no exception detail. The message and traceback go
to the log; the client gets the request id, which is the key into that log.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.constants import REQUEST_ID_HEADER

_logger = logging.getLogger("tramflow.http")


def request_id_of(request: Request) -> str | None:
    """The id ObservabilityMiddleware assigned, if it ran before the failure."""
    return getattr(request.state, "request_id", None)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = request_id_of(request)
    # exc_info, not str(exc): the traceback belongs in the log, never in the body.
    _logger.exception(
        "request_failed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
        },
    )
    body: dict[str, str | None] = {"detail": "Internal Server Error"}
    headers = {}
    if request_id is not None:
        body["request_id"] = request_id
        headers[REQUEST_ID_HEADER] = request_id
    return JSONResponse(status_code=500, content=body, headers=headers)


def register_exception_handlers(application: FastAPI) -> None:
    # Handling bare Exception routes ServerErrorMiddleware through this instead
    # of its plain-text default. HTTPException and RequestValidationError keep
    # FastAPI's own handlers, which already return the {"detail": ...} shape
    # recorded in contracts/openapi.json.
    application.add_exception_handler(Exception, unhandled_exception_handler)
