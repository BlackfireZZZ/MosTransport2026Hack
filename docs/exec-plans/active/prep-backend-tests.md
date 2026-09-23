# TASK-014 / TASK-026: backend verification

## Purpose and acceptance

New HTTP tests lock down current forecast/scenario behavior for three horizons,
validation and missing data, zero-change identity and baseline immutability.
PostgreSQL tests must read the migrated seed, prove deterministic ordering and
rollback commits. Production domain, transport, persistence and migrations stay
unchanged. Shared tracker updates belong to the integrator.

## Context and ownership

Base: 5eccb89b61c24f414d37972be5aabb07b881de10; branch
`agent/prep-backend-tests`; worktree
`/home/blackfire/Hackatons/MosTransport2026Hack-worktrees/prep-backend-tests`.
Lead owns Makefile, CI, new lifecycle script, SQL fixtures/tests and this report.
HTTP subagent owns only new `backend/tests/test_forecast_api.py`; lifecycle
subagent owns only new `backend/tests/test_backend_test_env.py`.
Contracts: forecast API schemas/services, SQL repository, initial Alembic seed.
Consumers were searched in backend, Makefile, scripts and CI before editing.

## Decisions and research

Reuse existing Compose services and postgres:17-alpine, no new dependencies.
Every invocation uses a UUID project, project-scoped volume, Docker-assigned
loopback ports and fixed disposable credentials. Explicit Compose file and empty
env file prevent developer .env/COMPOSE_FILE from selecting a working database.
There is no preliminary teardown of a possibly shared project.

- https://docs.docker.com/compose/how-tos/project-name/: project namespace isolation.
- https://docs.docker.com/compose/how-tos/networking/: discover published ports.
- https://docs.sqlalchemy.org/en/20/orm/session_api.html: create_savepoint joins an
  external transaction without committing it. The real PostgreSQL failure/commit
  regression test, not SQLite behavior, is the acceptance evidence.

Existing migration-verify/stack-verify used fixed project IDs and initial volume
cleanup. They now reuse the same UUID lifecycle, so concurrent runs cannot remove
one another's resources. Migration verification now uses locked local uv tools;
CI installs the existing backend toolchain before it.

## Progress

- Worktree created from requested base; primary checkout initially clean.
- HTTP and lifecycle tests delegated in non-overlapping files.
- SQL fixtures and lifecycle implemented; required stack smoke still in progress.

## Validation and recovery

Required: focused HTTP/service tests, backend-sql-test, migration-verify,
compose-check, isolated stack smoke, make check, failure/cancellation cleanup,
independent review, diff audit. SIGKILL/daemon outage cannot guarantee cleanup;
runner prints its exact project and reports cleanup failures. Worktree is retained
for integrator, no merge/push/removal authorized. Final evidence follows here.

## Observed evidence (2026-09-23)

- Focused HTTP/service pytest: 41 passed (39 new HTTP cases).
- `make backend-sql-test`: 10 passed against PostgreSQL 17; empty-database
  Alembic upgrade and drift check passed; owned resources removed.
- Lifecycle pytest: 18 passed. Includes setup/migration/test errors, signal exit,
  environment poisoning, diagnostic failures and cleanup failures.
- Real fault injection: a temporary PATH wrapper made the migration subprocess
  exit 37 after PostgreSQL startup. Runner returned 37; Docker label queries
  found zero owned containers, volumes and networks. An inherited invalid working
  DATABASE_URL/COMPOSE_FILE/project was ignored.
- Real SIGTERM during PostgreSQL startup: runner returned 143; Docker label
  queries found zero owned containers, volumes and networks.
- Independent read-only review found cancellation during diagnostics could bypass
  cleanup. Fixed by suppressing repeat signals on entering finally, bounding
  diagnostics and handling diagnostics failures. Reviewer reran five mocked
  failure/cancellation probes successfully and found no remaining blocker.
- Lead `make check`: exit 0; 118 backend passed, 10 SQL tests explicitly skipped
  in this fast gate; 3 ML and 23 frontend tests passed; Ruff, mypy, architecture,
  ML golden evaluation, frontend lint/types/build, OpenAPI drift and Compose passed.
  Existing pinned runtime used: Node 24.19.0, npm 11.19.0. Initial local npm 9
  failed engine-strict; used already-installed supported runtime, no lock edits.
- No dependencies added/upgraded; no production data/domain/API/schema/migration,
  graph or ML files modified. No measured model-quality or scalability claim.

## Integrator handoff

Proposed tracker changes: TASK-014 and TASK-026 ready for review after commit;
tracker intentionally untouched. Integrator owns merge/cherry-pick and status
updates. Next serving block (TASK-027/028) can reuse `sql_session`/`sql_engine` for
run/window invariants; these new invariants must not be inferred from seed tests.
Public HTTP/data contracts unchanged. Developer test command `backend-sql-test`
is new; `verify` includes it; migration/stack verification now use unique projects
and allocated ports. Migration verification requires the existing local locked
backend toolchain, installed in CI. See integration README for recovery.

Primary checkout later acquired third-party changes in TASK_TRACKER.md, TASK.md
and new ACCEPTANCE.md; preserved and excluded. This branch remains based solely
on 5eccb89, as requested.
