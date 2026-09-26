# TASK-065 — first-validation timing and schedule interval reconstruction

Owner: lead. Status: completed (experimental comparison; no model promotion). Base eabc2d5e1030e6366d0d0ccba37e989ce4343eb8;
worktree /Users/cute/MosTransport2026Hack-worktrees/boarding-timing-v2,
branch agent/boarding-timing-v2. Primary checkout has earlier documentation edits,
which are not implementation dependencies and must be preserved during integration.

## Claim and acceptance

First-payment group timestamps, validated schedule-derived local durations and
chronologically fitted dense reference durations will change inferred phase and
local residuals while preserving every source event and original route/hour mass.
No schedule-only departure list is labelled a confirmed trip. Multiple starting
positions survive globally scored sequence inference; missing-payment stops remain
allowed. Existing v1 outputs and code behavior remain unchanged by default.

Acceptance: synthetic tests prove skip transitions, first timestamps, no cumulative
timing error, ambiguity/alias rejection and chronological separation. Run matched
real-data baseline/v2 comparisons on all nine routes and multiple temporal slices;
report coverage, agreement, full posterior flow movement, residuals, skipped-stop
hotspots, stability and dense-reference held-out coverage. Broaden to complete dates
where feasible; declare exact denominators and exclusions. No measured accuracy or
occupancy claims without independent gold. Parent runs make check and diff audit.

## Ownership and contracts

Lead owns new timing_v2.py and experiment runner/CLI/docs; backward-compatible
optional timing arrays in sequence.py plus focused tests. Schedule agent owns
schedule_intervals.py and its tests. Dense-profile agent owns dense_profiles.py
and its tests. Shared worktree, strictly non-overlapping files; final integration
and verification are owned by lead. Existing RouteEvidence stays compatible.

## Evidence and research

Existing real.py uses mean burst times, four scenarios and original-hour soft-mass
aggregation. sequence.py already uses local observed differences and skip steps.
composition.py uses nearest independent stop departure, not coherent trip IDs.
GTFS https://gtfs.org/documentation/schedule/reference/ requires trip_id and ordered
stop_times for scheduled trip identity; departure-list pairing here remains inferred.
https://otexts.com/fpp3/tscv.html supports evaluating on later observations: reference
profiles train before the evaluation date, with explicit vehicle disjointness checks.
Transfer from 2026 schedules is not historically certified. Purely periodic clocks
may admit multiple travel-time aliases; tests must prevent false precision.

## Progress

- Read repository contracts, inspected current algorithms, created isolated worktree.
- Implementation and schedule/source audit in progress.

## Recovery and handoff

All outputs versioned in ignored ml/artifacts. No serving, API or database changes.
Retain previous data and model. If v2 is less stable, report it and do not promote.
Keep worktree until verified integration; do not clean unpushed branches/artifacts.

## Observed outcome and verification

4,017,177events/20dates/all9routes preserved exactly by event key, route and hour.
V1/V2hard agreement8.43%;softmassmoved7.42%;distancefromuniform6.81%. No confident
anchors or dense profiles survived. Paired perturbations worse in allfourcases;
report explicitly rejects promotion. The absence of supported profiles is a
measured result, not a silently invented fallback.

Parent make check passed350backend/545ML/92frontend/119contracts,48SQLskipped;
focused86tests passed;7dailyfiles repeated identically with1vs4workers. Paired
stability output reproduced identically. Ruff/mypy/build/golden/Compose passed.
No new dependency, serving, API, DB or frontend change. Report and source/test
files integrated as verified patch into primary; previous uncommitted docs retained.
Worktree retained for ignored artifacts and its unpushed branch; no cleanup of
user data or pre-existing worktrees. Final report link in TASK065.
