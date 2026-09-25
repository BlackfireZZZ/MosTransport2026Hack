# Session checkpoint — 2026-09-25

## Integrated state

Primary repository: `/home/chessnok/hacks/MosTransport2026Hack`, branch `main`.
Three data-lane tasks are complete and integrated:

| Task | Merge | Completed plan |
|---|---|---|
| TASK-016 reproducible synthetic fixtures | `4478d43` | [synthetic-transport-data](../completed/synthetic-transport-data.md) |
| TASK-018 identity alignment | `3703f29` | [identity-alignment](../completed/identity-alignment.md) |
| TASK-017 bounded historical ingestion | `80f3372` | [historical-ingestion](../completed/historical-ingestion.md) |
| TASK-019 leakage-safe aggregates and horizon features | `fd621d0` | [horizon-features](../completed/horizon-features.md) |

Each task was reviewed by an independent agent and, for TASK-019, validated by a
second independent agent against the acceptance criteria. Every finding was fixed
before the merge (`fc59a76`, `628636d`, `3392f99`, `80b93c4`). `make check` is
exit 0 on `main`: backend 292 passed / 10 SQL skipped, ML 265 passed, frontend 47
passed, reference contracts 119 passed.

No unmerged work lives outside `main`. Every remote branch that `main` already
contained was deleted on 2026-09-24; the SHA record for that cleanup is outside
the repository, in the job scratch directory, and is not needed to reproduce
anything.

## Work split

Serving plus map/UI is allocated to a second agent as the
[`for-vova-huesos`](../../agentic/FOR_VOVA_HUESOS.md) block: TASK-027, 028, 031,
032, 033, 034, 035, 036, 038, 056, owning `backend/**` and `frontend/**`.

The lead keeps the offline data/ML lane and owns `ml/**`. TASK-019 is done, so
the remaining chain is TASK-020 (rolling-origin backtesting) → TASK-021 /
TASK-022 (baselines, operational slices) → TASK-024 (interval scaffolding) →
TASK-029 (atomic publication, needs the second agent's TASK-027 schema) →
TASK-058 (evaluation-gated pipeline). TASK-039 (first-data profiling) is
unblocked and can run in parallel.

`contracts/**` is shared: it is the cross-boundary test oracle, changed only by
joint decision, and never imported by production code.

## Toolchain findings

- `uv` ≥ 0.12.13 is required (`pyproject.toml`); a standalone install to
  `~/.local/bin` satisfies it when the system package is older.
- `frontend/package.json` requires Node 24 / npm ≥ 11.19; `n 24` into `~/.local`
  satisfies it.
- `make bootstrap` runs `sync-all` (`uv sync --all-packages --all-extras
  --locked`) plus `frontend-install`. A per-package `uv sync` is exact, so
  running `sync-backend` and `sync-ml` in sequence removes the other package's
  dev extras and backend tests then fail at collection with
  `Unknown config option: asyncio_mode`. Use `make sync-all`.
- A fresh worktree has no `frontend/node_modules`, so `make check` fails in
  `frontend-check` on a global ESLint until `make frontend-install` has run;
  `make bootstrap` covers this. `make e2e` additionally needs one
  `make e2e-install` per machine.

## Exact continuation

Lead's next task: TASK-020 (history-aware rolling-origin backtesting), which
depends on TASK-004 and TASK-019 and is now unblocked. TASK-039 can run beside
it. Follow the worktree and ExecPlan rules in the root `AGENTS.md`; keep
million-row outputs outside git.

The stop-identity question the feature work surfaced is settled in
[ADR-0006](../../decisions/0006-stop-identity-and-direction.md): the repository
holds three stop namespaces, the OSM graph's nodes are direction-specific
(measured: 0 reciprocal edges, 382 names on more than one node) while the
contract and the `stops` table are physical places with direction as a separate
axis. The canonical namespace stays physical, so the
`(canonical stop, direction) → OSM node` crosswalk is 1:1, and `forecast_points`
needs a direction column because its `stop_id` points at the physical namespace.
Both consequences land in the second agent's TASK-032 and TASK-027.

`docs/exec-plans/tech-debt.md` carries TD-001 (the three recorded feature
digests are documented but pinned by no test) and TD-002 (`stops.name` is
globally unique, which real stop data does not honour).

## Lifecycle / boundaries

Worktree `horizon-features` may be removed now that `main` contains its merge;
the earlier task worktrees are already gone. The local dev stack (Compose `db`, uvicorn on
8000, Vite on 5173) was started for the user on 2026-09-24 and is not part of
the integration evidence.
