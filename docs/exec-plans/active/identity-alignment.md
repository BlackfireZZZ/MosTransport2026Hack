# TASK-018: explicit identity rules for validations and telemetry

## Purpose and acceptance

Join source validation/telemetry rows to canonical catalog entities only through
explicit, versioned crosswalk tables and configurable clock rules. Duplicate stop
names, opposite directions, repeated stops on a loop, stale GPS, clock offsets and
mid-day vehicle route changes never join to the wrong entity: every row gets an
explicit `matched`, `unmatched`, `ambiguous` or `stale` outcome, and a quality
report gives per-stream counts and rates by outcome, match kind and reason.
Existing synthetic generation, evaluation and HTTP code stay unchanged.

## Context and ownership

Base 4478d43; worktree `MosTransport2026Hack-worktrees/identity-alignment`,
branch `agent/identity-alignment`. Owned files: `ml/src/tramflow_ml/identity/`,
`ml/tests/test_identity*.py`, this plan and one `## Identity alignment` section in
`ml/README.md`. `cli.py`, `synthetic.py`, `contracts/`, `backend/`, tracker and
session handoff are not edited; CLI wiring is a later task. Pure-Python API, no
new dependency.

Oracles: `contracts/data_v1.py` (`EntityCatalog.validate_location` zero-based visit
index, `EventRow` availability rule), `contracts/calendar_v1.py` (Moscow service
date). The ML package must not import repository-only contracts, so it reads the
same `entities.json` shape through its own `CanonicalCatalog`; tests use the
contract models as oracles via `sys.path`, as `test_synthetic.py` already does.
`backend/.../models.py` stores stops with a unique name, which the synthetic
catalog deliberately violates; identity work therefore keys on ids, never names.

## Decisions

1. `Crosswalk` is loaded from a plain dict (`crosswalk_version`, `entity_version`,
   `routes`, `directions`, `stops`, `stop_names`, `stop_positions`, `vehicles`) and
   validated against the catalog: unknown canonical ids, wrong `entity_version`,
   name entries whose stop is not on the named pattern, naive or inverted vehicle
   intervals and overlapping intervals for one vehicle raise `CrosswalkError`.
2. Route and direction come only from the source row through the crosswalk. A stop
   that exists in one direction only never implies that direction; a missing or
   unknown direction is `unmatched`, not inferred.
3. Stop resolution order: source stop id via `stops` (kind `exact_id`), then a
   qualified `stop_names` entry `(name, route, direction)`, then catalog stops on the
   pattern with the same name (kind `name_route_direction`; two or more is
   `ambiguous`), then GPS (kind `geo_nearest`). Vehicle assignments are a veto table:
   an assignment covering the event instant that disagrees with the source route is
   `unmatched` with reason `vehicle_route_conflict`; no assignment means no veto.
4. A stop visited twice on a pattern is resolved only by `stop_sequence`
   (source base configurable, canonical zero-based visit index) or by
   `previous_stop_id` naming the preceding visit; otherwise `ambiguous`.
5. Geo matching is scoped to the pattern's stops with known positions, so the
   opposite platform of the same name is never a candidate; haversine on
   R = 6 371 008.8 m; two stops within tolerance is `ambiguous`; none is
   `unmatched`. A GPS fix whose `fix_at` differs from the event by more than the
   staleness threshold is `stale` and not joined.
6. Per-source clock: naive timestamps are interpreted in the source timezone,
   `offset_seconds` is added, output is `Europe/Moscow`; original and adjusted
   `event_at`/`available_at` are kept and `service_day_shifted` is set when the
   Moscow date changes. Missing `available_at` uses a configured lag or is
   `unmatched` (`availability_missing`); availability before the event is
   `unmatched` (`availability_precedes_event`), never clamped.
7. Missing clock configuration for a stream is an operator error and raises
   `AlignmentError`; row-level defects become outcomes so the batch completes and
   the report shows them.
8. All records are frozen dataclasses; alignment returns new records and never
   mutates input rows. Quality output is a dict with sorted keys; rates are
   `count / total` per stream and sum to one.

## Verification plan

Hand-calculated fixtures per failure mode, then `make ml-check`, then
`make sync-backend && make check`, `git diff --check`. Ingest-style test on the
tiny synthetic fixture: an identity crosswalk built from its `entities.json`
must give 100% `exact_id` matches, zero ambiguous/unmatched, and every matched
row must pass `EntityCatalog.validate_location`.

## Boundary

Real organizer columns, name conventions, GPS tolerance and staleness thresholds
are not certifiable before samples; every threshold is configuration. No NDTP or
delay-prediction dependency is assumed.

## Progress

Implemented 2026-09-24 as package `ml/src/tramflow_ml/identity/` (types, payload
helpers, catalog, geo, crosswalk, config, clock, matching, align, quality; largest
module 182 lines, every function under 50 lines) with tests
`ml/tests/test_identity_{fixtures,crosswalk,matching,geo,time,report}.py`.

Two hand-calculated fixtures were wrong on first run and corrected without touching
the implementation: the noon vehicle-change event had kept an 08:01 `available_at`
(so `availability_precedes_event` was the right answer), and one degree of
meridian on R = 6 371 008.8 m is 111 195.08 m, not 111 194.93 m.

## Validation

- `make ml-check`: ruff clean, mypy strict "no issues found in 15 source files",
  122 passed (50 identity tests; 72 pre-existing).
- `make sync-backend && make check`: exit 0. Architecture boundaries passed;
  backend 292 passed / 10 skipped; ML 122 passed; golden evaluation `"passed": true`;
  frontend 8 files / 47 tests passed, production build `built in 466ms`;
  contract check passed; reference-contract 119 passed; Compose config valid.
- First `make check` attempt failed in `frontend-check` because the fresh worktree
  had no `frontend/node_modules`, so `npm run lint` resolved a global ESLint 6.4.0
  that cannot read `eslint.config.js`. `make frontend-install` (`npm ci` from the
  committed lock, 0 vulnerabilities) fixed it; no manifest or lock change.
- Tiny synthetic fixture (64 events, January 2024): validations 100% `exact_id`,
  telemetry 100% `geo_nearest`, zero ambiguous/stale/unmatched, every match passes
  `EntityCatalog.validate_location`, no service-day shift.
- Recovery: the package has no consumer yet (CLI wiring is TASK-032-adjacent
  follow-up); reverting the commit removes it cleanly.

## Open risks

- Geo tolerance, staleness threshold and one-based sequence handling are defaults
  for tests, not certified values; organizer samples decide them.
- `stop_names` fallback compares exact catalog names; normalisation (case, ё/е,
  abbreviations) is deliberately absent until real naming conventions are seen.
- Vehicle assignments veto only; a vehicle with no interval never blocks a join,
  so coverage of the assignment table must be reported separately by the ingester.
