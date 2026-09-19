FROM python:3.13-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /workspace

COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml ./backend/pyproject.toml
COPY ml/pyproject.toml ./ml/pyproject.toml
RUN uv sync --frozen --package tramflow-backend --no-dev --no-install-workspace

COPY backend ./backend
RUN uv sync --locked --package tramflow-backend --no-dev --no-editable

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /workspace
USER appuser

WORKDIR /workspace/backend
EXPOSE 8000
CMD ["/workspace/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
