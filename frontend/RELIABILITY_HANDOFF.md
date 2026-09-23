# Frontend reliability — execution and handoff

## Purpose and acceptance

TASK-005–010 and TASK-037, owned by Terminal 4. Base:
`5eccb89b61c24f414d37972be5aabb07b881de10`; branch
`agent/prep-frontend-reliability`; worktree:
`/home/blackfire/Hackatons/MosTransport2026Hack-worktrees/prep-frontend-reliability`.

Observable contract: demo provenance remains explicit during loading, failure and
success; a failed refresh retains the last successful same-selection forecast;
missing/invalid route selection causes no forecast request; old selection and
scenario responses cannot replace current results. Local network inspection remains
available when remote basemap or WebGL fails, and independent query failures have
scoped recovery. Browser fixtures must obey existing forecast and topology types.

Scope is frontend only. Public API, generated schema, dependencies, backend and
shared product/tracker files are unchanged. Stop/time forecast filters and geographic
forecast joins remain subsequent work. This in-scope plan substitutes for a shared
`docs/exec-plans` edit, which the terminal instructions prohibit.

## Evidence and ownership

Existing evidence: `DESIGN.md` stale/error requirements; query keys in
`use-forecast.ts`; seed and prototype calculation in backend ForecastService;
existing generated ForecastResponse and graph schemas. Smallest falsifying checks:
query/component tests, fixture invariants, then mocked-network browser flows.

Lead owns App and forecast components/hooks, this report and final verification.
Network agent owns `src/features/tram-network`; browser agent owns `e2e`.
Shared working tree is isolated from main; these ownership areas do not overlap.

## Progress and decisions

- Forecast hooks use a disabled query function for absent/nonpositive/noninteger IDs;
  App validates selection against the loaded route list. Query keys isolate selections.
- Refresh failure is a separate saved-demo state; successful query data is retained.
- Every scenario edit/reset detaches the previous mutation observer. Existing
  keyed remount isolates route/horizon changes; late-response tests cover reset/edit.
- Demo labels describe current synthetic capabilities without claiming validated
  graph learning, live observations or route assignment.
- Remote style/tile or WebGL errors produce an explicit unavailable map with retry.
  The existing local GeoJSON remains inspectable via a keyboard-accessible stop and
  directed-edge list. This chooses TASK-008's accessible alternative, not a new
  offline cartographic style. Camera transitions respect reduced motion.
- Geometry/search/detail/path failures suppress the corresponding obsolete overlay
  or result. Graph, routes, statistics and Overpass have independent retry controls.
  No selected route means no duplicate geometry failure for the whole graph.
- Browser fixture factory reconciles peaks, bounds and Moscow-aligned day/month/year
  buckets. E2E sources now participate in the normal TypeScript check.

## Research evidence

MapLibre's [event contract](https://maplibre.org/maplibre-gl-js/docs/API/type-aliases/MapEventType/)
documents error/load and WebGL context events; the
[v6 migration guide](https://maplibre.org/maplibre-gl-js/docs/guides/v5-to-v6-migration-guide/)
documents initialization failure behavior. Reviewed 2026-09-23. These lifecycle
boundaries match the installed renderer; handling failure does not establish that
local graph layers rendered. Therefore the UI exposes independent graph inspection
and recreates the renderer on explicit retry. Any rendering error is conservatively
reported as unavailable; a transient tile error may require a retry even if parts
of the canvas are visible. No style replacement, dependency or irreversible
architecture decision is introduced.

## Validation and recovery

Initial system Node 18/npm 9 cannot run this project's locked toolchain. Temporary
runtime `/tmp/prep-frontend-runtime/node-v24.15.0-linux-x64` provides Node 24.15.0
and npm 11.19.0. `npm ci` succeeded with 0 reported vulnerabilities; no dependency
or lockfile changes. `uv sync --all-packages --extra dev --locked` installs existing
check dependencies in this worktree. No new package is adopted by the application.

Final observed evidence on 2026-09-23 (all exit 0):

- `make frontend-check`: lint, typecheck, Vitest and production build passed;
  the final same checks under `make check` include 47 tests across 8 files.
- `make check`: architecture boundaries, backend Ruff/mypy and 61 tests, ML
  Ruff/mypy and 3 tests, synthetic ML evaluation, frontend checks, unchanged
  OpenAPI/generated schema verification and Compose configuration passed.
- `PLAYWRIGHT_BASE_URL=http://127.0.0.1:40690
  PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/google-chrome make e2e`:
  18 Chromium tests passed. API, basemap and tile responses are deterministic;
  no live Overpass is needed. Covered forecast initial failure/retry, saved data,
  loading/empty routes, scenario context changes, keyboard network navigation,
  directed/unreachable/component-separated paths, endpoint swap/reset, empty search,
  independent failures/retries, blocked style/tiles, WebGL failure, map recovery and
  reduced motion. Saved-forecast and offline-network views pass axe and page-overflow
  checks at 390/768/1440px. Screenshots are under ignored `frontend/test-results`;
  mobile saved forecast and offline network were also visually inspected.
- Focused scenario tests cover edit-after-submit, edit/reset during pending requests,
  late older results and failure/retry. Hook tests cover invalid IDs and late
  route/horizon responses. Fixture tests enforce peaks, intervals and calendar order.
- `git diff --check` passed; changed paths are exclusively under `frontend/`.
  No secrets, build products, generated schema or lockfile changes are included.

Reproduce using `export PATH=/tmp/prep-frontend-runtime/node-v24.15.0-linux-x64/bin:$PATH`
and run Vite on port 40690 for the browser command. Logs for this session are
`/tmp/prep-frontend-check.log` and `/tmp/prep-frontend-e2e.log`.

## Integrator handoff

Recommended tracker transitions: TASK-005, TASK-006, TASK-007, TASK-008, TASK-009,
TASK-010 and TASK-037 → `review`; owner Terminal 4 / prep-frontend-reliability.
The shared tracker has not been edited. Implementation and final gates are complete;
review/integration remain with the integrator.

Public contracts changed: none. Internal changes: `useForecast` accepts a nullable
selection and skips invalid queries; provenance component accepts query status/retry;
UI labels/errors now expose demo and stale states. Existing wire payloads are intact.

Exact next step: review this branch's frontend-only commit and cherry-pick it onto
the integration branch, then rerun combined checks. Later forecast filters/geographic
joins must retain selection-key isolation, saved-data/error states and demo labelling;
extend typed fixtures only after those new contracts are agreed.

Limits: tests use synthetic topology and forecasts; they do not establish forecast
quality, real-data compatibility, a live data feed, or production basemap availability.
Full Docker smoke/migration checks are not part of this frontend-only change.
Shared CSS, backend and product contracts need no changes for this block.
Recovery is revert of the frontend commit by the integrator. No schema migration.
Worktree retained as explicitly requested; no merge, push or cleanup is authorized.
