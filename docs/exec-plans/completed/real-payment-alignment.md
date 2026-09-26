# Real AFC-to-stop inference using historical OSM and published timetables

## Purpose and authorization

The user explicitly requests actual stop inference for real payments, retrieval of
historical routes/timetables from the internet, and maximum useful reconstruction
even though independent AVL/gold is unavailable. TASK-064 follows TASK-063; lack
of gold blocks claims of measured accuracy, not inference output. The resulting
labels remain inferred/uncalibrated, with candidate alternatives and source dates.

## Context and ownership

Base `06e9884ea4abd86ce2a1d6c92f8fc8a6549ea582`; branch
`agent/boarding-real-alignment`; worktree
`/Users/cute/MosTransport2026Hack-worktrees/boarding-real-alignment`.
Primary checkout is read-only before verified integration.

The previous full audit already accounts for 59,667,191 successful source rows.
Its hash-checked ledger is reused without deduplication. Existing model, API, DB,
frontend and serving data remain outside this offline experiment.

Lead owns partitions, source composition, real inference runner, CLI and reports.
Disjoint agents own historical OSM adapter/tests, timetable adapter/tests, and the
sequence-model module/tests. Final verification and integration belong to lead.

## Falsifiable claims and acceptance

- Published ordered stop sequences and route variants can constrain real timestamp
  sequences. A candidate stop assignment is returned with its pattern version,
  direction, visit position, conditional support, alternatives and ambiguity.
- Exact original route/hour payment mass is conserved, including unresolved and
  out-of-scope events. Rejected payments never gain boarding weight.
- Starts are open; neither first burst nor midnight implies a terminal. Missing
  payment support is a latent visit, not a missing physical stop. Repeated stops
  preserve their sequence positions.
- Snapshot/time provenance is explicit. OSM edit dates are not service-validity
  certificates; current timetables remain transferred priors, never 2025 facts.
- Missing independent gold is recorded as real_stop_accuracy=unverified. Structural
  conservation, repeated-route consistency and synthetic accuracy cannot replace it.
- Synthetic brute-force checks, time/cutoff boundaries, deterministic reruns and
  real perturbation/scenario comparisons precede inference export.

## Approach and experiment contract

Use dated OSM relation histories for ordered patterns and the existing rail graph
for lengths where the same directed pair exists. Explicitly flag any straight-line
fallback and current coordinate provenance. Public official notices identify
known diversions. An archived published timetable supplies dated scheduled evidence;
current schedules can supply separately labeled transferred timing scenarios.

Compare a geometry/time sequence model against unassigned B0 and schedule-only
candidate matching. The bounded sequence model uses forward/backward uncertainty
and a Viterbi path; timing scenarios cover speed/dwell sensitivity. No calibration
or learned spatial truth is claimed. Data selection is chronological and fixed
before measuring assignments. Gold never enters inference configuration.

The primary output includes a best inferred candidate even where it is unsuitable
as a training label; accepted weak labels additionally require scenario agreement,
sufficient conditional support and no known incompatible pattern. Ties stay
ambiguous. A strict training export and a broad exploratory ledger remain distinct.

## Research and source evidence

- OSM API relation history provides timestamped versions and membership, unlike the
  flattened 2026 graph: https://wiki.openstreetmap.org/wiki/API_v0.6
- Historical OSM queries use attic date semantics:
  https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL
- Official timetable pages: https://transport.mos.ru/transport/schedule
- Historical route 7 diversion from 10 July 2025:
  https://www.mosmetro.ru/news/details/7319 ; restored 11 August:
  https://www.mosmetro.ru/news/details/7570
- Forward/backward recurrence:
  https://www.cs.cmu.edu/~15281/coursenotes/hmm_pf/index.html

Evidence, downloaded hashes and failed-source attempts are recorded in the run.
No dependencies are added. OSM-derived files retain ODbL attribution.

## Validation and recovery

Focused tests: shard conservation/restart; OSM version-date boundaries and repeated
visits; timetable wrong-route/date/truncation; sequence posterior versus exhaustive
small enumeration; symmetry, skips, cyclic visits, resets and finite budgets.
Then ML Ruff/mypy/pytest, golden evaluation, parent `make check`, diff/privacy audit.
Each run writes new artifacts and a final manifest; incomplete output is not training
input. Rollback is revert of the isolated commit, without production changes.

## Completed evidence and remaining scientific limits

Full audited ledger repartitioned into304 dates. Historical source composition
preflight passed for all304 dates. Full inference completed for59,667,191 successes;
no original route/hour mass loss, no undecoded successes.3,421,698 soft stop/hour
rows exported with chronological181/62/61-day splits.57,679,999 expected-event mass
is eligible for experimental soft-target use, not observed truth.

Source bundle retains24 OSM histories,37 complete timetable snapshots,20 primary
service notices, all hash-bound. Only one timetable is an actual2025archive;
current proxies and current rail/coordinate geometry remain explicitly dated.
The original graph is used, with explicit straight-line fallback edges.

Independent review fixed Moscow-midnight selection, cross-day context misuse,
session-key collisions, missing timetable evidence bias and per-reset support.
Context is zero/open-midnight. Full posterior mass is retained beyond the three
candidate alternatives. A separate source policy applies hour-overlap exclusions
and explicit restorations without changing immutable inference or losing mass.

A controlled equal-clock fixture exposed bias between exact/proxy precision on
route7 July29. All10,382 affected events and17 raw strict candidates remain in the
audit but are excluded from training. Zero strict labels qualify. No claim of
measured real-stop accuracy or certified historical operated trips is made.

Real sensitivity: six count-stratified vehicle sessions,5,766 events. Candidate
agreement44.2/48.9% for grouping changes,46.1% for20%thinning,70.3% for±5s jitter.
These are sensitivity results, not accuracy. All selected strict-label counts zero.
The report was reproduced byte-for-byte. All14 data files across two real days
were identical under2 versus6workers. Restart reuses only hash-verified day outputs;
changed sources/config/completed parts fail closed.

Final parent make check:350backend,497ML,92frontend,119contracts passed;48SQL skipped
because no SQL/runtime changes. Static checks, production frontend build, golden
ML evaluation and Compose config passed. No dependencies or serving contracts changed.

Results and exact commands: `docs/analysis/2026-09-26-real-stops/README.md`.
Training ZIP and source ZIP are retained in this worktree's ignored `ml/artifacts`;
full per-event inference occupies about3.9GB. Integration is local fast-forward
into main after verification; worktree retained for data and unpushed branch.
Empirical stop accuracy remains unverified because independent stop truth is absent.

Concrete open compromises are tracked in [TD-004/TD-005](../tech-debt.md).
