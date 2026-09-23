# Backend: local rules

Authoritative product requirements: [../docs/product/TASK.md](../docs/product/TASK.md). Prioritize tram passenger-flow forecasts for day/month/year, route/stop/time aggregation, and an updating Moscow map. OD, multimodal modeling, and what-if are optional team extensions.

The root `AGENTS.md` is mandatory. This file only adds rules specific to `backend/`.

## Boundaries

- Dependencies flow `api → application → domain`; `infrastructure` implements application/domain ports and is wired in the composition root.
- Pydantic schemas define the HTTP contract and SQLAlchemy models define persistence. Do not use either as domain types.
- An endpoint validates the request, invokes a use case, and maps the result or error. SQL and business decisions are forbidden in handlers.
- Change the database schema only through a new Alembic migration. Never rewrite a migration that may already have been applied.
- New production dependencies, breaking API changes, and destructive migrations are large tasks.

## Verification

Run the closest test for the changed use case or endpoint first, then:

```bash
uv run --package tramflow-backend ruff check backend
uv run --package tramflow-backend mypy backend/app
uv run --package tramflow-backend pytest backend/tests
```

For a migration, also run the upgrade against a clean temporary database and `alembic check`, and document the rollback or forward-fix strategy. See `docs/agentic/VERIFICATION_MATRIX.md`.
