# TASK-070 — historical schedule and absolute-clock ablation

Owner boarding-absolute-clock lead. Base cb9dce42dddb6a6aca57b18f5143359006ee8c26;
branch agent/boarding-absolute-clock in dedicated sibling worktree.

Claim: calendar-filtered trip clock profiles, a shared initial offset and explicit
terminal priors can be compared against interval-only matching without jumping to
another trip during continuation. First observations remain hypotheses. Raw data,
serving labels and older artifacts remain unchanged. Evidence: GTFS official
reference, immutable shard contract, existing first-anchor coalescing, published
source clocks. Focused tests cover shared offset, skips, source calendars, midnight,
nondecreasing minute clocks, terminal prior and locked continuation.

Completed source research: actual2025archived17/11pages; communityGTFS capture2026,
embeddedMay2025files and declaredApr/May2025calendars,1798trips. Source audit retains
uncertainty/license and quarantines nonmonotone horizontal table associations.
Independent parser and historic OSM stop-order checks completed. No dependencies.

Completed experiment:72segments/144possiblemethodcombinations,87eligiblecorrelated
rows across35windows; most session-first segments lack6detectedonsets. Four-onset
prefix locks profile/offset then2–4onset continuation. Sixvariants/two clocks-shift
controls, month/route breakdowns and station stability. Strong prior improves
conditional interval fit but17minshiftcontrol can outperform actualclock; no hard
stop labels or performance claim adopted. See analysis report/source/summary/stations.

32focusedtests pass; make check1186passed/48SQLskipped, static/build/golden/Compose
pass. Independent read-only implementation/research review no blockers; lead ran
quality gate. Agent module cherry-picks9bcdd63/89bce61 integrated beforeleadgate.
Final verified patch preserves primary uncommitted work; retain both worktrees and
unpushed branches for source snapshots and artifacts. Rollback: remove newoffline
module/scripts; no production contract or previous transform changed.
