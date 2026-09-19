from __future__ import annotations

import logging
import re
from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._logger = logging.getLogger("tramflow.http")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        supplied_id = request.headers.get("x-request-id", "")
        request_id = supplied_id if _SAFE_REQUEST_ID.fullmatch(supplied_id) else uuid4().hex
        started_at = perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration_seconds = perf_counter() - started_at
            self._logger.info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": round(duration_seconds * 1000, 3),
                },
            )
