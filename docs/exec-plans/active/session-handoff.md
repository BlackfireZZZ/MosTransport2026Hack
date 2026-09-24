# Session checkpoint — 2026-09-25

## Integrated state

Primary repository: `/home/chessnok/hacks/MosTransport2026Hack`, branch `main`.
Three data-lane tasks are complete and integrated:

| Task | Merge | Completed plan |
|---|---|---|
| TASK-016 reproducible synthetic fixtures | `4478d43` | [synthetic-transport-data](../completed/synthetic-transport-data.md) |
| TASK-018 identity alignment | `3703f29` | [identity-alignment](../completed/identity-alignment.md) |
| TASK-017 bounded historical ingestion | `80f3372` | [historical-ingestion](../completed/historical-ingestion.md) |

Both TASK-017 and TASK-018 were reviewed by an independent agent, accepted with
findings, and the findings were fixed in follow-up commits (`fc59a76`,
`628636d`) before the merge. `make check` is exit 0 on `main`.

No unmerged work lives outside `main`. Every remote branch that `main` already
contained was deleted on 2026-09-24; the SHA record for that cleanup is outside
the repository, in the job scratch directory, and is not needed to reproduce
anything.

## Work split

Serving plus map/UI is allocated to a second agent as the
[`for-vova-huesos`](../../agentic/FOR_VOVA_HUESOS.md) block: TASK-027, 028, 031,
032, 033, 034, 035, 036, 038, 056, owning `backend/**` and `frontend/**`.

The lead keeps the offline data/ML lane and owns `ml/**`:
TASK-019 (leakage-safe aggregates and horizon features) → TASK-020
(rolling-origin backtesting) → TASK-021 / TASK-022 (baselines, operational
slices) → TASK-024 (interval scaffolding) → TASK-029 (atomic publication, needs
the second agent's TASK-027 schema) → TASK-058 (evaluation-gated pipeline), with
TASK-039 (first-data profiling) available in parallel after TASK-019.

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

Lead's next task: TASK-019, which depends on TASK-017 and TASK-018 and is now
unblocked. Follow the worktree and ExecPlan rules in the root `AGENTS.md`; keep
million-row outputs outside git.

## Lifecycle / boundaries

Worktrees `historical-ingestion` and `identity-alignment` may be removed now
that `main` contains both merges. The local dev stack (Compose `db`, uvicorn on
8000, Vite on 5173) was started for the user on 2026-09-24 and is not part of
the integration evidence.
