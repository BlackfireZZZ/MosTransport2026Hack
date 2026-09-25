# Parallel block `for-vova-huesos`

A second agent owns this block end to end, in parallel with the lead's offline
data/ML lane. It is one coherent outcome: **a dispatcher can open the map, pick a
route, stop and time window, and read forecast values whose run, units, geometry
quality and freshness are all explicit.** Nine of the ten tasks depend only on
work already merged; the one cross-lane wait is named below.

Read [AGENTS.md](../../AGENTS.md) and [TASK_TRACKER.md](TASK_TRACKER.md) first.
This file allocates work and file ownership; it does not widen authority.
Owner value in the tracker: `for-vova-huesos`.

## Tasks, in dependency order

| Order | Task | Area | Blocked by (inside block) | Ready now |
|---|---|---|---|---|
| 1a | [TASK-027](TASK_TRACKER.md#task-027) persist coherent forecast runs, enforce value invariants | backend + migration | — | yes |
| 1b | [TASK-031](TASK_TRACKER.md#task-031) make missing per-edge geometry explicit | backend + frontend | — | yes |
| 1c | [TASK-032](TASK_TRACKER.md#task-032) join forecast entities to versioned Moscow map geometry | data + backend | — | yes |
| 2 | [TASK-028](TASK_TRACKER.md#task-028) serve bounded route/stop/time-window aggregates | backend | 027 | after 027 |
| 3 | [TASK-033](TASK_TRACKER.md#task-033) dispatcher stop and time-window filters | frontend | 028 | after 028 |
| 4 | [TASK-034](TASK_TRACKER.md#task-034) synchronize map, time selection and chart state | frontend + backend | 028, 032, 033 | after 033 |
| 5 | [TASK-035](TASK_TRACKER.md#task-035) provenance and trustworthy refresh state | frontend + backend | 034 | after 034 |
| 6 | [TASK-036](TASK_TRACKER.md#task-036) uncertainty and units inspectable without hover | frontend | 033, 035, **lead's TASK-024** | after 035 and 024 |
| 7a | [TASK-038](TASK_TRACKER.md#task-038) accessibility and responsive operation | frontend | 033–036 | last |
| 7b | [TASK-056](TASK_TRACKER.md#task-056) self-describing dispatcher forecast report export | frontend | 035, 036 | last |

1a, 1b and 1c are independent of each other and can run in three worktrees at
once. From order 2 the chain is sequential because each step consumes the
previous contract.

## File ownership

Owned by this block — the lead does not edit these while the block is open:

- `backend/**` (including `backend/alembic/versions/**`, new revisions only)
- `frontend/**`
- `docs/decisions/**` for ADRs this block writes. 0006 is now taken by
  [ADR-0006 stop identity and direction](../decisions/0006-stop-identity-and-direction.md),
  so TASK-031 writes `0007-edge-geometry-quality.md`.
- `docs/exec-plans/active/<task-slug>.md` for each task that needs an ExecPlan

Owned by the lead — read freely, do not modify:

- `ml/**` (TASK-032 may import `tramflow_ml.identity` and
  `tramflow_ml.ingestion` as libraries; extending them is a lead task)
- `contracts/**` — the shared test oracle. A contract change is a joint
  decision: raise it instead of editing, and never import `contracts` from
  production code.
- `docs/agentic/TASK_TRACKER.md` rows other than this block's ten

Shared, append-only: `docs/agentic/HANDOFF.md`. Report status there rather than
editing the lead's rows.

## Cross-lane dependencies

- TASK-036 is the only task here that waits on the lead: it needs TASK-024
  (calibrated-interval scaffolding) for real interval metadata. If TASK-024 has
  not landed when order 6 comes up, do TASK-056 and TASK-038 first, or build the
  accessible table and units against the frozen `forecast.v1` interval fields
  and mark interval quality unavailable — never invent a calibration claim.
- Every other prerequisite is merged: TASK-007, TASK-008, TASK-010, TASK-012,
  TASK-015, TASK-025, TASK-026, TASK-030, TASK-037 are `done`, and TASK-032's
  prerequisite TASK-018 is merged as `3703f29`.
- The lead's TASK-029 (atomic batch publication) consumes TASK-027's schema and
  waits for it. Do not implement publication in TASK-027; persist runs and
  invariants only, and leave the active-run switch to TASK-029.
- TASK-041 (million-row and bounded query/UI budgets) measures both lanes and
  stays unassigned until TASK-028 and TASK-034 are merged.

## Settled before you start: stop identity and direction

[ADR-0006](../decisions/0006-stop-identity-and-direction.md) answers a question two
of your tasks would otherwise each answer differently. Read it before touching
TASK-027 or TASK-032; the short version and the two consequences that bind you:

The repository holds **three stop namespaces**. The OSM graph's nodes are
`stop_position` points on the track and are **direction-specific** — measured on the
committed extract: 856 nodes, 919 edges, **0 edges with a reverse twin**, and 382
names carried by more than one node. The contract (`contracts/data_v1.py`) and the
`stops` table are **physical places** with direction as a separate axis; the
synthetic catalog deliberately reuses one stop id in both directions and gives two
different stops the same name. The canonical namespace stays physical.

**TASK-027 — `forecast_points` needs a direction column.** Its `stop_id` points at
the physical namespace, so `(route_id, stop_id, horizon, bucket_start)` does *not*
determine a direction: a route passes a physical stop both ways. Tram loading is
strongly asymmetric between directions, so collapsing them destroys the signal the
forecast exists for. Add direction and include it in the uniqueness. You are writing
a new migration anyway; doing it now costs a column, doing it later costs a data
migration. This supersedes the key written in `docs/architecture/README.md`
(`(route_id, stop_id, horizon, bucket_start)`) — update that line with your migration.

**TASK-032 — the crosswalk key is the pair, not the stop.**
`(canonical stop, direction) → OSM node` is **1:1**, precisely because the OSM nodes
are direction-specific. Keying on the stop alone is 1-to-many and ambiguous. Do not
merge OSM nodes by name to recover a physical stop unless you also keep the
direction: 382 names are shared, and 19 names sit on four nodes, 11 on three, one on
ten. `tramflow_ml.identity` already returns `Ambiguous` rather than guessing when a
name is shared on a pattern — match that behaviour, and report unmatched and
ambiguous counts rather than silently dropping.

Two consequences the lead found in the serving code while settling this, both
yours:

- **Direction has to reach the API, not just the table.** `ForecastResponse` in
  `backend/app/schemas/forecast.py` is per-route with a flat `points` and `stops`
  list and carries no direction anywhere; `frontend/src/features/forecast/` has no
  notion of it either. So TASK-027's column is an API shape change that continues
  into TASK-028 and the UI tasks: run `make contract-generate`, commit the
  regenerated `schema.generated.ts`, and decide explicitly whether a dispatcher
  picks a direction or sees both — do not quietly sum them.
- **Unknown capacity cannot currently be expressed, and is silently invented.**
  `ForecastPointModel.capacity` defaults to `180.0`
  (`backend/app/infrastructure/db/models.py`), and `ForecastPointResponse.capacity`
  is `Field(gt=0)`, so a stop with no known capacity is served a fabricated 180
  rather than an absence. TASK-027's own acceptance requires zero or unknown
  capacity to be handled explicitly before division — that means the default and
  the `gt=0` bound both have to go, and the response needs a way to say "unknown".

Related and already recorded: `docs/exec-plans/tech-debt.md` TD-002 —
`stops.name` is declared globally unique, which real stop names do not honour. It
does not block you today (the graph is a file repository, ADR-0003, and never enters
`stops`), but it is yours the moment TASK-032 seeds real stop rows.

## Working rules

- One worktree per task: `make agent-create ID=<slug> REF=main`, branch
  `agent/<slug>`. Rebase or merge `main` before opening a merge request; never
  push to `main` directly, never force-push.
- Evidence before changes: record the command and its observed output, not an
  expectation. TASK-031 changes a currently tested behaviour, so its ADR and
  rollback note land before the code.
- Never rewrite `backend/alembic/versions/20260919_0001_initial.py`. Every schema
  change is a new revision with a verified `upgrade`/`downgrade`.
- API shape changes run `make contract-generate` and commit the regenerated
  `frontend/src/api/schema.generated.ts`; `make contract-check` must be clean.
- `make check` is the gate for every task in this block, plus the task's own
  focused commands (`make migration-verify backend-sql-test` for 027/028,
  `make e2e` for 033–036/038, after one `make e2e-install` per machine). First
  run in a fresh worktree needs `make bootstrap` — `sync-all` plus
  `frontend-install`, not `sync-ml` alone.
- Toolchain: `uv` ≥ 0.12.13 and Node 24 / npm ≥ 11.19 are hard requirements.
- Keep the honesty constraints from the task cards: no summed interval bounds
  under an unstated independence assumption, no "calibrated" or "confidence"
  wording on synthetic data, no straight line presented as real rail geometry,
  and unavailable capacity must not render as zero.
