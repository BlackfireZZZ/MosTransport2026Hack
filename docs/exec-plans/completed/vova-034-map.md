# TASK-034: coherent forecast time and map selection

## Purpose / observable result
One forecast response supplies the selected bucket, stop values and map positions.
Changing the bucket changes the current KPI, chart highlight and accessible stop
list together. Real canonical joins require an explicit versioned surrogate bridge.

## Context
Base d2d063d8f4dd09f9887f3b931688028e51f5c447; branch agent/vova-034-map;
worktree /Users/cute/MosTransport2026Hack-worktrees/vova-034-map.
TASK-028 supplies run/selection/stop_points; TASK-032 supplies strict canonical
geometry. Serving integer identities cannot be cast into canonical or OSM IDs.
Legacy seed only has stop forecasts for each horizon's first bucket; other buckets
must remain empty on the map. bucket_end=null is not a license to invent duration.

## Scope / non-goals
Backend mapping envelope, optional artifact bridge/configuration, shared snapshot
UI state, optional MapLibre forecast layer, deterministic API/browser fixtures.
No dependency, database, ML or model/publication-contract changes. No real-data
crosswalk certification, no forecast interpolation, no fabricated rail lines.

## Acceptance
- All displayed selected values derive from one response/run and exact timestamp.
- Missing/ambiguous/version-incompatible joins remain explicit and counted.
- Synthetic runs may show supplied demo coordinates as points with an unmatched
  OSM warning; non-synthetic unmatched rows have no position.
- Forecast serving IDs use separate callbacks/properties from OSM IDs.
- Keyboard, empty, load, error, responsive and stale responses remain usable.

## Progress / decisions
Hypothesis: one snapshot plus exact bucket selection eliminates cross-response
joins; explicit surrogate keys prevent namespace collisions. Existing focused
mapping tests and deterministic multi-bucket browser fixtures will disprove it.
The lead owns final integration; shared tracker/handoff are not edited here.

## Research evidence
MapLibre official examples `update-a-feature-in-realtime` and `draw-geojson-points`
use a GeoJSON source and setData. Reuse that existing repository pattern for one
bounded circle layer, not animation or new dependencies:
https://maplibre.org/maplibre-gl-js/docs/examples/update-a-feature-in-realtime/
https://maplibre.org/maplibre-gl-js/docs/examples/draw-geojson-points/
Existing map worker/fallback/geometry-quality behavior is retained. No route
polyline is inferred from point membership.

## Validation / recovery
Bootstrap, focused Python/Vitest, contract-generate/check, make check, make e2e.
No migrations; rollback is reverting this task commit and regenerating API types.
Results pending. Worktree retained until verified integration.

## Configuration contract
Set FORECAST_GEOMETRY_MAPPING to a strict forecast-geometry.v1 artifact. Optional
serving_links entries explicitly contain integer route_id/stop_id, a direction_id
string and a nested canonical entity (route_id/direction_id/stop_id strings).
The crosswalk entity_version and graph_version must equal the serving run; absent
or aggregate directions are not inferred. An absent configuration returns visible
mapping_not_configured; an unreadable/invalid artifact returns visible
mapping_configuration_invalid while forecast values remain available.

The provider caches the first valid mapping and immutable graph snapshot together.
Restart the web worker after changing the mapping or active graph. Until restart,
a new run with another graph version is visibly unavailable for mapping; it is not
joined against a mismatched cached version. Invalid initial loads are retryable.
Synthetic status combines forecast, crosswalk and loaded graph provenance.

## Verification and review result
- Focused backend mapping/geometry/API verification: 80 passed before the final
  configured-provider regression. File-backed bridge test now publishes a complete
  graph snapshot and verifies real coordinates with synthetic canonical identities.
- Final make check: exit 0; backend 346 passed / 45 SQL skipped, ML 151 passed,
  frontend 70 passed, reference contracts 119 passed. Architecture, Ruff, mypy,
  ESLint, TypeScript, production build, OpenAPI drift and Compose checks passed.
- make e2e: exit 0, 30 passed with Chrome at http://127.0.0.1:43134. Three horizons,
  exact bucket values, keyboard step/stop controls, missing later buckets, and
  390/1440 viewport+axe cases pass. Existing network tests also pass.
- Browser QA found and fixed mobile min-content overflow and keyboard access to an
  empty scrollable table. Reviewed saved 390px and 1440px screenshots; table scroll
  stays internal and map outage has a persistent recoverable explanation.
- Lead/reviewer checks found and fixed synthetic graph provenance loss, full
  stop/direction selection scope, null/empty chart-click index handling, and map
  envelope entity/graph/run checks. Real forecasts reject synthetic mappings/graphs.
- Browser map backgrounds are intentionally mocked/offline in tests. The existing
  MapLibre worker/style path is reused; a renderer unit test verifies circle-layer
  data and that forecast clicks call serving IDs without hitting the OSM callback.
- One initial permission-review timeout prevented starting make check; retry
  succeeded. This was not a code/test failure. Earlier failing assertions were
  addressed before the final gates above.

No migration, dependency or raw data changes. SQL integration remains the lead's
integration gate; this change does not alter repository queries. The worktree and
unique preview are retained for review/integration, with no push or main edits.
The follow-on TASK-035/036 owns polished provenance/unit/capacity presentation;
TASK-050 owns real mapping certification. No later stop values were invented to
make the legacy seed look complete.
