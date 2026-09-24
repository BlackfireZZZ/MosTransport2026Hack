# TASK-028 bounded forecast selection

Owner for-vova-huesos. Worktree /Users/cute/MosTransport2026Hack-worktrees/vova-028-window,
branch agent/vova-028-window. Base main d8313a4b79273306e41001adaf1f4673649cc304;
TASK-027 cherry-picked as 76e4a99 from 2602b4d.

## Purpose and hypothesis

One selected run returns exact route or stop values for a half-open time window,
without mixing route aggregates with stop rows or duplicating repeated route stops.
Legacy no-filter seed requests retain values and bucket counts. Invalid or excessive
windows fail explicitly. SQL groups before transfer; response cardinality is bounded.

## Contracts and scope

Frozen forecast.v1 bounds cannot be summed without an aggregation model. Preserve
single-row uncertainty/capacity; combined values report null. Serving integer IDs
are explicitly a surrogate namespace, never canonical IDs. Add run provenance and
resolved selection, stable unique route-stop selector API. No dependency, schema,
training or UI screen changes. Existing DB run schema and repository tests support
this approach. API generated output is regenerated, not hand edited.

## Acceptance and verification

Chronological exact buckets, two-direction sums, repeated-stop deduplication,
exclusive end, timezone validation, empty selection, oversized rejection, draft/run
isolation, seed parity. SQL tests include EXPLAIN (ANALYZE, BUFFERS). Run focused
HTTP/SQL then make check, migration-verify and stack-verify. No required check may
be waived. Revert commit for recovery; no migration is introduced.

## Decisions and research

Use existing SQLAlchemy select/group_by and the existing PostgreSQL composite
run/route/time index. No new complex algorithm: deterministic disjoint count sums.
Unknown interval dependence yields unavailable bounds. Existing API uses integer
seed IDs; a separate mapping task owns canonical/OSM joining.

## Progress

Bootstrap passed with locked dependencies. TASK-027 prerequisite passed all gates
before this task began editing. Implementation in progress.

## Final API contract

`GET /forecasts` retains route_id/horizon and adds optional stop_id, direction_id,
start/end. End is exclusive by bucket start; timestamp offsets are required and
start/end must appear together. Maximum elapsed spans are 24 hours, 31 days and
366 days, with 24/31/12 bucket limits respectively. Omitted windows resolve from
an indexed first bucket for the requested run/entity/direction. The legacy calendar
remains explicitly legacy; no generated bucket end or canonical ID is invented.
Explicit valid empty windows return 200 with empty arrays; unknown route/stop/run
returns 404; invalid limits return 422; inconsistent stored data returns 409.

Points group only route aggregate rows, or only the requested stop. Stop maps use
separate stop rows, deduplicated route membership, and never add route aggregates
to stop counts. Direction sums use exact decimal representations of serialized
float values, converted to float once at the response boundary; singleton values
preserve their original bits. Nonfinite sums and load ratios fail explicitly.
Unknown dependency between multiple sources means combined bounds/capacity are
null. `selection.interval_aggregation` declares `single_source_or_unavailable`.

`run` exposes run_id, dataset/source/feature/entity/calendar/graph versions, target,
unit, synthetic, forecast_origin, data_cutoff, interval level/method and
`identity_namespace=serving-surrogate-integer`. Existing top-level generated_at
and model_version remain. `selection` includes resolved start/end, stop/direction,
aggregation key and interval policy. `stop_points` supplies stop_id, timestamp,
nullable bucket_end/direction, predicted/bounds/capacity and aggregation_scope
from the same run/query/window as chart points. Legacy bucket_end is null.
SQL-serving always emits these; optional transport fields preserve custom old
repository fixtures without inventing metadata.

`GET /routes/{route_id}/stops` lists unique numeric serving IDs, names, positions
and first occurrence sequence. It is a selector catalog, not an ordered trip.
The response stops limit is 1000 and grouped row transfer is capped at 31031.
These are provisional local safety limits, not organizer SLA claims.

## Review and observed verification, 2026-09-25

Merged main foundation (`024d138`) into this branch; retained main tracker and
completed plans unchanged. Removed accidentally reintroduced active TASK-027 plan.
Independent review fixed direction-aware default windows, UTC elapsed limits,
representational overflow, orphan route-stop predictions and synthetic precision.
First SQL run found an explicit-seed primary-key collision in a new fixture;
second found an old fixture retaining predictions after deleting route membership.
Both fixtures now satisfy the tested contracts. Fractional aggregation oracle uses
independent Decimal arithmetic over serialized values, not Python binary addition.

- `make backend-sql-test`: final 45 passed in 1.46s, including real HTTP filter,
  stop selector, empty/error/run coherence, direction and numeric boundary tests.
- `EXPLAIN (ANALYZE, BUFFERS)` with 10000 extra synthetic rows: index scan on
  ix_forecast_run_route_time; 30 selected rows, 18 shared buffer hits, execution
  0.050ms on this local disposable stack. This is a reproducible query-plan check,
  not a production performance claim or TASK-041 scale certification.
- `make check`: exit 0; backend 331 passed (45 opt-in SQL cases verified separately),
  ML 151 passed, frontend 50 passed, contracts 119 passed. Architecture, lint,
  mypy, production build, generated API check and Compose validation passed.
- `make migration-verify`: clean initial+run-schema upgrade, no migration drift;
  disposable database/volume removed. No new schema or migration in TASK-028.
- Standard isolated stack harness plus an extra temporary HTTP smoke script:
  backend/database/frontend healthy; baseline smoke passed; route stop list and
  Moscow-offset stop/window query returned one matching chart/map value, same run,
  and unavailable legacy bucket_end. `/tmp/task028-stack-verify.py` is an unchanged
  owned harness except its ROOT and extra smoke command, not a repository change.
  Repeated smoke passed after the final numeric implementation. All test stacks
  and volumes were removed by their owning harnesses.
- `git diff --check`: clean. No dependency changes. Generated OpenAPI and frontend
  types synchronized; authored shared contracts unchanged. No UI product edits.

Integration: retained clean task worktree for parent review/local integration;
no main edit, remote push or worktree cleanup performed by this task.

## Narrow post-integration correction: occupancy aggregation

Base d2d063d, same clean task worktree; root authorized this follow-up. ADR-0005
permits disjoint count sums and forbids summing occupancies across times/stops.
The repository now rejects combined sources or time-bucket stop totals unless
(target, unit) is one of synthetic_boardings/event_count,
validation_count/event_count or boarding_count/passengers. Single-source,
single-bucket onboard_load remains readable; unsupported aggregation returns 409.
No API/schema/shared authored-contract or dependency change was needed.

Observed verification 2026-09-25: focused domain tests 5 passed; disposable SQL
suite 48 passed, including HTTP single-occupancy success and direction/time sum
409 regressions. `make check` exit 0: backend 335 passed (48 SQL cases verified
separately), ML 151 passed, frontend 62 passed, contracts 119 passed; all static,
build, generated contract and Compose checks passed. Owned test database/volume
removed; `git diff --check` clean. Separate fix commit retained for root integration.
