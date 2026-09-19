from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> repository root. Resolved from the module rather than
# the working directory: the container runs uvicorn from /workspace/backend, while a
# developer runs it from the checkout root.
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPOSITORY_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TramFlow API"
    app_env: str = "development"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://tramflow:tramflow_local@localhost:5432/tramflow"
    backend_cors_origins: list[AnyHttpUrl] = Field(
        default_factory=lambda: [
            AnyHttpUrl("http://localhost:5173"),
            AnyHttpUrl("http://localhost:8080"),
        ]
    )

    # The tram graph is a static committed asset, regenerated wholesale by
    # scripts/fetch_tram_graph.py -- see docs/decisions/0003-tram-graph-file-repository.md.
    tram_graph_json: Path = DATA_DIR / "tram_graph.json"
    tram_graph_geojson: Path = DATA_DIR / "tram_graph.geojson"

    # Self-hosted Overpass instance; HTTP only, no auth (docs/overpass-api.md).
    overpass_url: str = "http://204.168.155.177/api/interpreter"
    overpass_status_url: str | None = None
    overpass_timeout: float = Field(default=60.0, gt=0)
    overpass_health_timeout: float = Field(default=3.0, gt=0)
    overpass_max_query_chars: int = Field(default=8000, gt=0)

    @property
    def resolved_overpass_status_url(self) -> str:
        """`/api/status` sits beside `/api/interpreter` unless overridden explicitly."""
        if self.overpass_status_url:
            return self.overpass_status_url
        suffix = "/interpreter"
        if self.overpass_url.endswith(suffix):
            return f"{self.overpass_url[: -len(suffix)]}/status"
        return self.overpass_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
