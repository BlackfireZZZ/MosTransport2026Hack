# Integrate completed preparation blocks

## Purpose and acceptance

Integrate committed, reviewed preparation groups into the existing primary `main`
branch (there is no `master`). Combined checks must pass before primary integration;
public API and dependency versions stay unchanged. Preserve unfinished graph work.

## Context and ownership

Primary: `/home/blackfire/Hackatons/MosTransport2026Hack`, clean at base
`4a36d0ba1606bdb1fdb1523df97f5d9fe8f07280`.
Integration: sibling worktree `MosTransport2026Hack-worktrees/integrate-prep-blocks`,
branch `agent/integrate-prep-blocks`. Lead owns integration and this evidence.
Read-only reviewers cover backend, frontend, and graph/ML readiness.

## Scope and decisions

- Contracts: already merged as 087e9f0; no new completeness audit claimed.
- ML: implementation at d548bb8 matches main b026e53 exactly under `ml/`;
  do not reintroduce the older product documents from that branch.
- Backend: merge adb48fd (TASK-014/026).
- Frontend: merge a226094 (TASK-005/006/007/008/009/010/037).
- Graph: unfinished parent and loader worktrees; exclude intermediate commits.
- No new technology or dependency; existing branch contracts and tests are evidence.
- Both merges were conflict-free. Independent reviewers found no blockers.

## Validation and recovery

Run `make check`, contract pytest, `make backend-sql-test migration-verify
stack-verify`, and Chromium E2E on dedicated Vite port 42418. Audit diff, then
fast-forward main only if its clean base still matches. Preserve source worktrees.
Recovery is a reviewed revert; no production schema changes are introduced.

## Progress

- `make check`: exit 0; backend 120 passed / 10 SQL skipped, ML 50 passed,
  frontend 47 passed; lint, types, build, architecture, API drift and Compose pass.
- `uv run --package tramflow-backend pytest contracts/tests -q`: 12 passed.
- Chromium `make e2e` with dedicated URL and system Chrome: 18 passed.
- `make backend-sql-test migration-verify stack-verify`: exit 0; 10 PostgreSQL
  tests, clean Alembic upgrade/drift checks, built stack and smoke passed.
  Owned containers, volumes and networks were removed.
- Integration worktree and branch retained for review; source worktrees untouched.
  Vite test server stopped. No remote push is part of this integration.
