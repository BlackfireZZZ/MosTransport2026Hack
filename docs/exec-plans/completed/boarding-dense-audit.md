# TASK-066 — dense-route temporal fingerprint audit

Owner lead, completed experiment; real-stop accuracy remains unverified. Base aef37dfe49cec65d05d36f7f8bc58111f65268ce;
worktree /Users/cute/MosTransport2026Hack-worktrees/boarding-dense-audit,
branch agent/boarding-dense-audit. Main holds verified prior changes; preserve.

Claim: if dense validation bursts identify actual ordered stop timing, authentic
edge order should outperform order-shuffled controls on the same observations,
selected phase should predict later intervals, and thinning bursts should preserve
inferred positions. Choosing only high v2 confidence would circularly exclude the
very dense observations under investigation, so selection uses observed counts only.

Rank all9routes using the entire304-day successful ledger summaries. Examine all
routes on the same20dates as prior experiment, emphasize top3routes17/12/11.
Compare capped30s/90s bursts with natural15s/30s-gap bursts. Quantify artificial
max-span boundaries. Select dense windows by validation counts before fitting.
Fit all initial phases with local absolute residuals, allow1..3steps with explicit
skip penalty; test consecutive-only hypothesis separately. Fit initial six gaps
and predict subsequent no-skip intervals without using future gaps; also report
conditional skip-fitting separately. Shuffle edge order as a negative control.
Mask interior observations to test retained-phase reproducibility, not accuracy.

Before edits: existing timing_v2/group_times and sequence local-gap semantics are
contracts. Synthetic distinctive/periodic cycles, skipped observations and local
nonaccumulation will test the new bounded matcher. Sources: GTFS stop_times trip
identity reference; FPP3 time-series CV distinguishes fitted from held-out errors.
No new dependency, serving or feature contract. All results remain inferred.

Acceptance: fixed configs/seeds, raw count ranking, all-route and density/segmentation
slices, timing fit vs shuffled controls, chronological prefix holdout, hidden-burst
stability and identifiable-phase coverage. No claim of true stop accuracy. Parent
runs focused tests and make check, reviews source/data artifacts, integrates only
verified patch. Retain branch/artifacts, no cleanup of others' work.


Completed user steering: compared six segmentation methods, including local-rate
DBSCAN and an explicit rise/decay template. Independent20%payment holdout supports
pulse shape; five-minute rate-preserving controls separate pulse signal from raw
group count. Full20-day run and additional40-burst sequences completed. Source
receipts match; Jan15 repeated byte-identically. Final make check passed1,122tests,
48SQLskipped. Report contains algorithm, parameters, temporal and route aggregates,
scientific figures, negative findings and limits. No labels promoted.

Integration: verified patch on primary with prior uncommitted v2 edits preserved.
Worktree retained for ignored artifacts. No new dependencies or remote publication.
