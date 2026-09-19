# Two stages: node builds the React bundle, python serves it alongside the API.
# The runtime image carries no node and no toolchain -- only the built assets.

# ---------- stage 1: build the frontend ----------
FROM node:22-alpine AS frontend

WORKDIR /build

# Manifests first, so a source-only edit does not re-run the install layer.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
# vite.config.ts copies the maplibre worker pair out of node_modules into
# dist/maplibre/. They must stay adjacent -- the worker imports its shared chunk
# relatively -- and they must not be hashed, because setWorkerUrl names the path.
RUN npm run build


# ---------- stage 2: runtime ----------
FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    # The graph is mounted at /data rather than sitting inside the image, so the
    # extraction can be re-run without a rebuild.
    TRAM_GRAPH_JSON=/data/tram_graph.json \
    TRAM_GRAPH_GEOJSON=/data/tram_graph.geojson

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
# main.py resolves the mount as <parent of backend>/frontend/dist, so the build
# output has to land at exactly this path for the SPA to be served.
COPY --from=frontend /build/dist ./frontend/dist

# Drop privileges: nothing here needs to write to the image.
# --system would force a uid below SYS_UID_MAX (999); the uid is pinned explicitly
# instead, so a bind-mounted volume's ownership is predictable across hosts.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Bind to 0.0.0.0 -- the container's loopback is not reachable from the host.
# No --reload: it watches files and leaks memory in a long-running container.
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "backend"]
