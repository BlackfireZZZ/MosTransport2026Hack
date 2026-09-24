# TASK-027 — coherent forecast persistence

## Purpose and acceptance
One snapshot reads one run. Null-stop route aggregates are unique within a run;
nonfinite/negative values and invalid intervals fail in PostgreSQL. Capacity may
be unknown or zero without division. Existing synthetic seed remains readable.

## Context and boundaries
Owner: for-vova-huesos. Base d8313a4b79273306e41001adaf1f4673649cc304,
branch agent/vova-027-runs, worktree /Users/cute/MosTransport2026Hack-worktrees/vova-027-runs.
Frozen oracle: contracts/forecast_v1.py (read-only). Existing integer serving IDs
remain separate from canonical entity identity. TASK-029 owns active publication;
this task supplies run metadata and explicit state, not a publication command.
Initial migration is immutable. API nullable capacity propagates to consumers.

## Decisions
Run identity stores dataset/source/feature/entity/graph/model versions, target,
unit, timestamps, interval method/level and synthetic marker. Legacy seed is
explicitly legacy calendar/demo metadata, not a validated forecast.v1 artifact.
New runs default to draft. Only published state is readable, selected once and
reused for point and stop reads. Publication validation/switch remains TASK-029.

## Research
PostgreSQL unique constraints treat NULLs as distinct by default; PostgreSQL 17
supports NULLS NOT DISTINCT, matching the deployed image:
https://www.postgresql.org/docs/17/ddl-constraints.html
SQLAlchemy exposes postgresql_nulls_not_distinct:
https://docs.sqlalchemy.org/en/20/dialects/postgresql.html
Finite bounds need explicit checks because PostgreSQL NaN sorts above Infinity.
No new production dependency.

## Progress and verification
2026-09-25: make bootstrap passed using temporary uv 0.12.13, Node 24.21.0,
npm 11.19.0; locked dependencies unchanged; npm audit reported 0 vulnerabilities.
Baseline make migration-verify backend-sql-test passed: clean upgrade, no drift,
10 PostgreSQL integration tests passed; disposable projects removed.
Baseline backend: 292 passed, 10 SQL tests skipped outside isolated runner.
Implementation verified: make backend-sql-test 30 passed; make migration-verify
passed clean upgrade/no drift. Explicit downgrade to 20260919_0001 then upgrade
head and alembic check passed on owned tramflow-vova027-dev database.
make check passed: backend292 (30 SQL opt-in skipped), ML151, frontend48,
contracts119, lint/types/build/Compose all passed. Chrome E2E18/18 passed at
isolated port43127. Independent review fixed bad join, nullable chart arithmetic,
and downgrade guard for unpublished legacy data. Production-like make stack-verify passed: DB/API/frontend healthy and smoke
passed; disposable stack and volumes removed. make e2e-install completed.
Status: verified, independently reviewed, committed; pending integration.

Integer serving entity IDs remain surrogate IDs; TASK029 must explicitly resolve
canonical identifiers to these catalog entries (never coerce a canonical ID to
an integer). TASK032 owns versioned canonical-to-map crosswalks. Only generated
OpenAPI output under contracts changed as required by block generation rule.
uv/Node/npm were installed in /tmp solely as tooling; no manifest/lock changed.

## Recovery
New migration downgrade must refuse ambiguous multi-run data or nulls incompatible
with old schema; it must never silently discard forecast rows. Test roundtrip on
a disposable database. Keep worktree for review until integration is authorized.
