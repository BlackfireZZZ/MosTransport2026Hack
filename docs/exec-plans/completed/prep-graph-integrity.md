# Graph integrity: TASK-011, TASK-012, TASK-030

## Purpose / observable result

An incomplete Overpass response cannot replace graph artifacts. Malformed graph
data fails as `TramGraphDataError` and readiness returns unavailable. The exporter
publishes a complete, validated, versioned five-file snapshot through one atomic
manifest switch, with an explicit rollback to any prior complete snapshot.

## Context / ownership

Lead: Codex, branch `agent/prep-graph-integrity`, worktree
`/home/blackfire/Hackatons/MosTransport2026Hack-worktrees/prep-graph-integrity`.
Base: `b026e532acc91ce6bb6f13642401c899793a852d`; primary checkout initially clean.
Sibling `graph-publication` was created before the user reiterated the required
ID and remains clean, unused and retained. No other worktree is removed.

TASK-011 agent owns extractor and its new tests in `graph-extract-validation`.
TASK-012 agent owns graph domain/repository, shared parser and validation/health
tests in `graph-loader-validation`. Lead owns publication module/tests and docs;
lead takes over extractor/repository only after the corresponding agents finish.
Shared tracker, integration and final gate belong to lead.

## Scope / non-goals

Only scripts, backend graph domain/repository helpers, relevant tests and docs.
No frontend, forecast domain/API, public graph API, DB, Makefile/CI, dependencies,
or live Overpass test requests. Preserve directed routing, committed topology,
and legacy per-edge missing-geometry fallback (TASK-031 is separate).

## Acceptance / falsifiable claim

- Mocked HTTP-200 remark response exits nonzero and preserves all prior bytes.
- Malformed roots, duplicates, invalid IDs, coordinates, lengths and endpoints
  fail consistently; committed 856-node/919-edge/two-component graph still loads.
- Injected export/write/validation failures leave the active manifest unchanged.
- Each manifest binds all five artifact checksums and common source metadata;
  JSON/GeoJSON mismatch is rejected even if checksums are recomputed.
- Readers resolve the active manifest once and read one immutable snapshot;
  cached readers retain their complete snapshot until process restart.
- Rollback revalidates a prior snapshot before switching the active manifest.

## Progress / decisions

- Inspected task cards, callers, settings, packaging, repository and existing tests.
- TASK-011 and TASK-012 assigned in isolated worktrees; no overlapping writers.
- Keep existing explicit path constructor and HTTP contract. For conventional
  same-directory JSON/GeoJSON paths, `graph-store/` takes precedence when present.
  Legacy committed files remain supported before first publication.
- TASK-011 and TASK-012 integrated as `6eebe78` and `e1c60af`. Initial focused
  integrated suite passed 146 tests. Independent review identified the first
  legacy-to-versioned adoption failure; first publication now stages the whole
  store before an atomic directory rename. Added regression and consistent error
  handling for deeply nested manifests and long numeric route refs.

## Research evidence

Primary Python os.replace/fsync documentation and SQLite atomic-commit analysis
were fetched and reviewed before publication implementation. The web-search tool
did not finish, so the official pages were fetched directly via curl. Context,
adaptation and filesystem limits are recorded in
[ADR-0004](../../decisions/0004-atomic-graph-snapshots.md). No new dependency is needed.

## Validation / recovery

Focused mocked extractor, corrupt-data/readiness and publication failure tests,
then `make backend-check`, explicit script lint, `make check`. Compare committed
topology and schema drift. Independent review before final lead-owned gate.
Never rewrite a published snapshot; retain previous snapshots for rollback.
Do not claim power-loss or distributed-filesystem guarantees beyond documented
OS/filesystem semantics. Results and exact commands are recorded at handoff.

## Completed evidence and handoff — 2026-09-23

TASK-011, TASK-012 and TASK-030 acceptance is complete in this worktree. Agent
commits were cherry-picked in order, then lead implemented publication and
integrated independent review corrections. No other lanes' files were edited.

Observed commands:

- `uv run --package tramflow-backend pytest backend/tests/test_graph_extractor.py -q`:
  31 passed, including `python -S` standalone rollback in a separate process and
  mocked partial/error payload preservation for both legacy and versioned layouts.
- `uv run --package tramflow-backend pytest backend/tests/test_graph_publication.py -q`:
  36 passed. Covers failure before each artifact completes, corrupt/missing files,
  metadata/value/direction mismatch, rollback, captured readers during activation,
  cached-reader semantics and failures during first adoption.
- `uv run --package tramflow-backend ruff check scripts/fetch_tram_graph.py --config backend/pyproject.toml`:
  passed. Backend Ruff and mypy (42 files) passed within the full gate.
- `PATH=/home/blackfire/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH make check`:
  exit 0 after the final code change; 220 backend, 48 ML, 23 frontend tests,
  architecture boundaries, lint/types, golden evaluation, production build,
  OpenAPI drift and Compose config all passed.
- `git diff --check` and local documentation link validation passed (76 references).

Two independent reviewers approved the final scope. Their initial findings
(first-adoption failure, malformed-input exception leaks and GraphML per-edge
direction override) were fixed and covered before the final gate. One reviewer
also ran a two-thread first-publication race: two complete versions survived,
active topology was correct and each rollback loaded 856 stops. This experiment
is supplementary; no live Overpass request was made.

Committed graph bytes were not changed. Round-trip tests confirm 856 stops,
919 edges, component sizes 694/162 and unchanged statistics. Public API schemas,
forecast, frontend, DB, Makefile/CI, dependencies and lock files are unchanged.
Only existing locked dependencies were installed to run checks. Documentation
states Python 3.13 as the supported standalone interpreter; no third-party
package is required by the extractor/publication path.

Integration method: local cherry-picks of the two agent commits plus lead's
publication commit on `agent/prep-graph-integrity`. The result has not been merged
to primary: another terminal advanced main to `6a0f1a7` while this isolated block
ran. Exact next step for the integration owner is to merge this branch into the
current integration checkout, keep other lanes' tracker statuses, and run the
combined `make check` there. The original base remains
`b026e532acc91ce6bb6f13642401c899793a852d`.

Cleanup: this worktree and both clean agent worktrees/branches are retained for
integration/audit. The unused clean `graph-publication` worktree is also retained;
no other worktree was removed and no Docker stack/volume was started. Power-loss
durability, hostile writers and non-POSIX filesystems remain explicitly outside
the verified local filesystem contract; API processes must restart to adopt a
new active graph because their existing cache semantics are preserved.

## Combined integration — 2026-09-23

Integration worktree: `/home/blackfire/Hackatons/MosTransport2026Hack-worktrees/integrate-graph-block`,
branch `agent/integrate-graph-block`, base `7856223e76bcca0e4f239b87e839c2e4da65c589`.
Merged c3b0735 with only a tracker conflict, retaining all completed non-graph
statuses and graph TASK-011/012/030 results. Independent review found no blockers
and ran 166 focused tests. Lead focused graph suite: 156 passed; extractor Ruff clean.
Lead `make check`: exit 0, 292 backend passed / 10 SQL skipped, 50 ML passed,
47 frontend passed, architecture/types/lint/build/API drift/Compose passed.
Shared contract tests: 12 passed. `make backend-sql-test stack-verify`: exit 0,
10 PostgreSQL tests, clean migrations and built-stack smoke passed; owned runtime
resources removed. Diff audit clean; no committed graph bytes changed.
Integration into primary uses fast-forward from the clean recorded base. No push.
Integration and source worktrees retained for review; no other's workspace removed.
