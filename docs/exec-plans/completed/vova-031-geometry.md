# TASK-031: geometry quality

Owner: for-vova-huesos. Branch: agent/vova-031-geometry.
Worktree: /Users/cute/MosTransport2026Hack-worktrees/vova-031-geometry.
Base: d8313a4b79273306e41001adaf1f4673649cc304.

## Purpose and hypothesis

A missing edge remains navigable but cannot appear as a real rail line. Supplied
geometry, distances, reachability and error semantics remain unchanged.

## Context and scope

Domain `track_coordinates` supplies silent straight connectors. Network GeoJSON
and pathfinding consume it. Own graph domain/schema/UI/tests only; no forecast,
ML, database or manually authored shared contract changes.

## Acceptance

Partial and absent geometry expose quality and counts. Synthetic supplied
geometry is distinguished. UI omits inferred lines and states why in visible and
accessible text. Complete geometry and disconnected paths preserve behavior.

## Progress and decisions

ADR-0007 recorded before implementation. Existing regression tests are the
contract; extend them before accepting the result. Toolchain bootstrapped using
locked dependencies. New dependencies: none.

## Research evidence

This is an additive provenance field plus existing UI status behavior; no new
complex technology or pattern is introduced. See ADR-0007 alternatives.

## Validation and recovery

Focused domain/API and UI tests, generated contract check, then make check.
Browser keyboard/viewport validation covers visible quality status. Revert the
commit to roll back; no persistent data migration.

### Verification observed 2026-09-25

- `make bootstrap`: succeeded; locked dependencies, npm audit zero vulnerabilities.
- Initial `make check`: backend/ML passed; frontend build exposed required new
  response fields missing from fixtures. Corrected the fixtures without weakening
  generated schemas; repeated `make check` passed.
- `uv run --package tramflow-backend pytest backend/tests/test_tram_graph_api.py`:
  19 passed, including HTTP quality fields against the complete committed graph.
- `PLAYWRIGHT_BASE_URL=http://127.0.0.1:43131
  PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
  npx playwright test e2e/network.e2e.ts --workers=2`: 12 passed. Existing
  390/768/1440 responsive cases and new 390/1440 keyboard/axe cases passed.
- `make contract-generate` updated only generated `contracts/openapi.json` and
  frontend schema. This is the allocation's explicitly required generated
  contract output; authored `contracts/**` files were not edited.
- `git diff --check`: clean. No dependencies, migration, secrets or generated
  browser artifacts added. PostgreSQL integration tests are opt-in and remain
  skipped by `make check`; this task changes no SQL/schema.

Integration pending parent review; worktree retained intentionally. No push or
primary-checkout edit performed. No manual geometry certification is implied by
`provided`; it means the source supplied a polyline. Old UI clients remain subject
to their pre-existing silent-fallback behavior until deployed with the new UI.
- Final `make check`: exit 0; backend 300 passed / 10 opt-in SQL tests skipped,
  ML 151 passed, frontend 49 passed, shared contracts 119 passed; lint, mypy,
  production build, generated-contract check, architecture and Compose checks passed.

### Review correction

Independent review found that legacy GeoJSON-only `synthetic: true` was discarded
when graph metadata lacked the marker. The loader now conservatively preserves a
true marker from either validated file. A false or missing counterpart cannot
relabel synthetic geometry as provided. Three regression cases exercise missing,
false and true graph flags with synthetic GeoJSON through segment/path/API output.
Focused `pytest backend/tests/test_graph_validation.py`: 98 passed.
Repeated `make check`: exit 0; 303 backend passed (10 opt-in SQL skips), 151 ML,
49 frontend and 119 contracts passed, with all static/build/Compose gates passing.

## Integration
Locally integrated into main at 202caed after independent review and parent combined
make check (exit0). No remote push. Worktree retained because branch is unpushed.
