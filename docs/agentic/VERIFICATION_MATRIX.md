# Change verification matrix

Select every applicable row. Run focused checks before the full gate and include the observed exit code or result in the report.

| Change | Minimum falsifying check | Required gate |
|---|---|---|
| Documentation | referenced links, paths, and commands exist | `git diff --check` + diff review |
| Backend domain/application | unit test for the rule or use case | Ruff, mypy, backend pytest |
| HTTP API | success + validation/error tests + schema compatibility | backend gate + smoke test for the affected endpoint |
| SQL/repository | PostgreSQL integration test for the range and aggregation | backend gate; for an expensive query, `EXPLAIN (ANALYZE, BUFFERS)` |
| Alembic | upgrade on a clean temporary database; rollback/forward-fix strategy | `alembic check`, backend gate, Compose smoke test |
| Frontend logic | closest Vitest or component test | `npm run lint`, `npm run test -- --run`, `npm run build` |
| UI flow | critical happy, error, and what-if paths plus keyboard access | frontend gate + `make e2e` |
| ML feature/data | schema, time/timezone boundaries, and leakage test | Ruff, mypy, ML pytest |
| ML model | identical temporal splits, baseline, and multiple slices | ML gate + `make ml-eval` |
| Compose/runtime | `docker compose config --quiet` | clean `up --build --wait`, `make smoke`, and logs on failure |
| Multiple areas | boundary contract or integration test | every affected gate, then `make verify-fast` |

Area-specific commands are defined in the nearest `AGENTS.md`. Do not replace a required check with a broader one if the broader result cannot localize a failure. If a required check is unavailable, the change is not ready.
