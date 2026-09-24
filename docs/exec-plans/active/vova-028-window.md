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
