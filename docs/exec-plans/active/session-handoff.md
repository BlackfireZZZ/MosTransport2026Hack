# Session checkpoint — 2026-09-24

## Integrated state

Primary repository: `/home/chessnok/hacks/MosTransport2026Hack`, branch `main`.
TASK-016 (reproducible synthetic transport fixtures) is complete and integrated
from `agent/synthetic-transport-data`; see its
[completed execution plan](../completed/synthetic-transport-data.md) for the
measured million-event budget, independent review and final `make check` record.

Remote branches `agent/graph-extract-validation`, `agent/graph-loader-validation`,
`agent/prep-ml-evaluation` and `agent/ml-evaluation-finish` contain only patches
already integrated into `main` (`git cherry` reports every commit as equivalent or
its content is byte-identical to `main`); `chore/sqlalchemy-asyncio-extra` is an
ancestor of `main`. They can be deleted after a human confirms; no unmerged work
lives outside `main`.

## Toolchain findings

- `uv` ≥ 0.12.13 is required (`pyproject.toml`); a standalone install to
  `~/.local/bin` satisfies it when the system package is older.
- `frontend/package.json` requires Node 24 / npm ≥ 11.19; `n 24` into `~/.local`
  satisfies it.
- `make bootstrap` runs `sync-backend` then `sync-ml`; each `uv sync --package`
  is exact, so the second removes `pytest-asyncio` and backend tests then fail at
  collection (`Unknown config option: asyncio_mode`). CI is unaffected because
  each job syncs one package. Work around locally with `make sync-backend`
  before `make check`; a Makefile fix is the next maintenance item.

## Exact continuation

Next task by dependency order: TASK-017 (bounded historical ingestion with
restart and quarantine), which depends only on TASK-016. TASK-018 (identity
alignment) can proceed in parallel; both feed TASK-019. Follow the worktree and
ExecPlan rules in the root `AGENTS.md`; keep million-row outputs outside git.

## Lifecycle / boundaries

Worktree `MosTransport2026Hack-worktrees/synthetic-transport-data` may be removed
once `main` contains the merge. No remote push of `main` was performed by an
agent. The local dev stack (Compose `db`, uvicorn on 8000, Vite on 5173) was
started for the user on this date; it is not part of the integration evidence.
