# TASK-032: explicit forecast geometry joins

## Purpose / observable result
Canonical route/direction/stop keys resolve only through an explicit versioned
crosswalk. Missing and ambiguous joins stay inspectable; no name or integer guess.

## Context
Base d8313a4b79273306e41001adaf1f4673649cc304; branch agent/vova-032-mapping;
worktree /Users/cute/MosTransport2026Hack-worktrees/vova-032-mapping.
TASK-032 and ADR-0003 distinguish canonical and OSM namespaces. TASK-018's
source-to-canonical crosswalk cannot safely be inverted. Graph route membership
is a set, never an ordered trip or direction authority.

## Scope / non-goals
Backend domain, use case, strict offline mapping file adapter and fixture tests.
No ML/contracts edits, database migration, HTTP changes or real mapping claims.
The block lead owns integration with forecast serving and UI.

## Acceptance
Directional duplicate names resolve only by full key. Unknown/multiple candidates
remain unmatched/ambiguous with counts. Entity, mapping and validated graph
versions are returned. Mismatched forecast run versions fail closed. Existing
graph loading behavior stays compatible. No ordered trip inferred from route refs.

## Progress / decisions
- Read repository contracts and consumers; bootstrap passed with locked packages.
- Hypothesis: explicit full-key lookup and version equality prevent false joins.
- Existing graph publication checksum validation is reused, with a snapshot API
  returning the version from the same manifest read as the validated graph bytes.

## Research evidence
No new algorithm/dependency; use existing identity matching rules and file-backed
graph ADR. The change does not invert the existing ML crosswalk or extend it.

## Validation / recovery
Focused crosswalk tests then make check. Revert added modules and snapshot wrapper
if rejected; no persistent schema/data mutations. Verification results are recorded below.

## Result and adapter contract
`ForecastGeometryService.map_stops` takes distinct or repeated canonical
route/direction/stop keys and exact forecast entity/graph versions. Repeated keys
across time buckets are deduplicated in first-seen order; quality counts count
entities, not observations. Coordinates exist only for one explicit candidate
whose OSM route membership agrees with the crosswalk. Multiple candidates stay
ambiguous even when one candidate is absent from the graph.

The offline JSON schema is demonstrated by
`backend/tests/fixtures/forecast_geometry.v1.json`: `schema_version`,
`mapping_version`, `entity_version`, `graph_version`, `routes` (canonical route ID
and unordered OSM route refs), and `stops` (full canonical key plus candidate OSM
node IDs). Unknown fields, duplicate JSON fields, coerced IDs and duplicate keys
are refused. Empty candidate arrays explicitly mean unmapped. No name matching,
route-order inference or implicit namespace conversion exists.

`load_geometry_service` requires a published checksummed graph store. The graph
version is captured from the same single manifest read that selected the graph
bytes; a test changes the active pointer during reading and retains consistency.
Missing or mismatched run graph versions fail closed. The caller must expose map
unavailability rather than substitute a different snapshot.

Verification observed: focused mapping + graph publication suite 50 passed;
after adding the manifest-switch regression, mapping suite 15 passed. Mypy:
45 source files clean. `make check` exit 0: backend 307 passed / 10 SQL skipped,
ML 151 passed, frontend 47 passed, contracts 119 passed; lint, build, OpenAPI and
Compose checks clean. SQL tests are unchanged and no schema was edited.

Remaining integration: block lead wires these reusable modules to selected
forecast runs/API/UI in TASK-034. Actual canonical-to-OSM correspondence awaits
organizer evidence and TASK-050; this task intentionally supplies only labeled
synthetic mapping fixtures, not fabricated real coverage. Worktree retained for
lead review/integration; no push, main edit or cleanup performed.

## Independent review correction
The block lead found mapping provenance lacked an explicit synthetic marker.
The artifact now requires a strict `synthetic` boolean, which is preserved on the
crosswalk and result. The marker describes mapping evidence, independently of the
forecast model/run's synthetic status. Multiple OSM refs in one route row mean an
intentional membership union; they do not indicate alternate candidate matches,
trip order or direction. Stop candidate multiplicity always remains ambiguous.

Correction verification: mapping tests 20 passed; `make check` exit 0 (backend
312 passed / 10 SQL skipped, ML 151, frontend 47, contracts 119). No dependency,
API or publication-contract changes. Earlier implementation commit 734ef45 and
this correction await lead integration.
