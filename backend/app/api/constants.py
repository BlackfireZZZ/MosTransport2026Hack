"""Names shared across the HTTP layer.

`REQUEST_ID_HEADER` is used by the middleware that assigns the id and by the
error handler that echoes it back. Neither owns the other, so the name lives
here rather than making error handling import from observability.
"""

from __future__ import annotations

REQUEST_ID_HEADER = "X-Request-ID"
