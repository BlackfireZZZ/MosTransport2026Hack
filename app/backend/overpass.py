"""Thin client for the upstream Overpass API.

Overpass has five response shapes and only one is the obvious one, so nothing here
calls .json() directly:

  * success                      200, application/json
  * parse or static error        400, an HTML error page
  * dispatcher shed              504, an HTML error page
  * query hit its own [timeout:] 200, valid JSON carrying a "remark" key
  * output not JSON              200, application/osm3s+xml

The HTML pages arrive under 400 and 504, so raise_for_status() fires before anything
reads the body -- hence run_query unwraps the message in that branch too. The
"remark" shape is the dangerous one: it is a successful-looking response holding a
partial result. It is passed through rather than raised on, because a partial answer
is sometimes what the caller wants; callers must check for the key themselves.
See docs/overpass-api.md.
"""

from __future__ import annotations

import html
import json
import os
import re

import httpx

DEFAULT_URL = "http://204.168.155.177/api/interpreter"


class OverpassError(RuntimeError):
    pass


def interpreter_url() -> str:
    return os.getenv("OVERPASS_URL", DEFAULT_URL)


def status_url() -> str:
    explicit = os.getenv("OVERPASS_STATUS_URL")
    if explicit:
        return explicit
    url = interpreter_url()
    return url[: -len("/interpreter")] + "/status" if url.endswith("/interpreter") else url


def query_timeout() -> float:
    return float(os.getenv("OVERPASS_TIMEOUT", "60"))


def health_timeout() -> float:
    return float(os.getenv("OVERPASS_HEALTH_TIMEOUT", "3"))


def max_query_chars() -> int:
    return int(os.getenv("OVERPASS_MAX_QUERY_CHARS", "8000"))


def client(timeout: float) -> httpx.AsyncClient:
    """Indirection so tests can swap in an httpx.MockTransport."""
    return httpx.AsyncClient(timeout=timeout)


# Overpass error pages are HTML, and the message is split across tags: the word
# "Error" sits inside a <strong>, the text that matters comes after the closing
# tag. Anything that matches around the markup collapses to "Error", so strip the
# markup first and match against the resulting text instead.
_BLOCK_BREAK_RE = re.compile(r"</(?:p|div|li|tr|h[1-6]|pre)\s*>|<br\s*/?>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]*>")
_ERROR_LINE_RE = re.compile(r"error", re.IGNORECASE)
MAX_MESSAGE_CHARS = 500


def html_to_lines(body: str) -> list[str]:
    """The visible text of an HTML error page, one entry per block element."""
    text = _BLOCK_BREAK_RE.sub("\n", body)
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    return [" ".join(line.split()) for line in text.splitlines() if line.strip()]


def error_message(body: str) -> str:
    """Every distinct error line on the page, in order.

    A single page can carry a parse error and a runtime error at once -- keeping
    only the first one throws away half of what went wrong.
    """
    lines = html_to_lines(body)
    seen: list[str] = []
    for line in lines:
        if _ERROR_LINE_RE.search(line) and line not in seen:
            seen.append(line)
    message = "; ".join(seen) if seen else " ".join(" ".join(lines).split())
    return message[:MAX_MESSAGE_CHARS] if message else body.strip()[:MAX_MESSAGE_CHARS]


def parse_response(body: str) -> dict:
    if not body.lstrip().startswith("{"):
        raise OverpassError(error_message(body))
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise OverpassError(f"upstream returned unparseable JSON: {exc}") from exc


async def run_query(ql: str) -> dict:
    timeout = query_timeout()
    async with client(timeout + 30) as http:
        try:
            resp = await http.post(interpreter_url(), data={"data": ql})
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Parse and static errors come back as HTTP 400 with the same HTML
            # error page, so the message is in the body raise_for_status just
            # discarded. docs/overpass-api.md only documents the HTTP 200 case.
            detail = error_message(exc.response.text)
            raise OverpassError(
                f"upstream returned HTTP {exc.response.status_code}"
                + (f": {detail}" if detail else "")
            ) from exc
        except httpx.HTTPError as exc:
            raise OverpassError(f"could not reach {interpreter_url()}: {exc}") from exc
        return parse_response(resp.text)


async def check_status() -> tuple[bool, str | None]:
    """Short-timeout probe of /api/status. Never raises -- a dead upstream is a
    fact to report in /api/health, not a failure of the endpoint."""
    url = status_url()
    try:
        async with client(health_timeout()) as http:
            resp = await http.get(url)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        return False, f"{type(exc).__name__}: {exc}"
    except Exception as exc:  # a broken env var, a bad URL -- still not a 500
        return False, f"{type(exc).__name__}: {exc}"
    return True, None
