# TASK-069 — first observed payment anchor

Owner boarding-first-anchor lead. Base 7c07bc09b4af97f43d89306565a1da09d9af5b07,
branch agent/boarding-first-anchor, dedicated sibling worktree boarding-first-anchor.

Claim: optional observation-boundary anchoring makes the earliest candidate equal
to the first actual payment, without claiming trip start/stop identity. Same-wave
support and quiet-gap contracts remain in force. Existing coalesce tests and the
raw immutable window contract support the implementation; no new learned algorithm.

Complete: deterministic insertion/provenance; tests for empty candidates, exact
matches, duplicates, same wave, quiet-separated nearby waves, actual-time shift;
320-window frozen audit and recomputed three-window schedule visualization.
17 focused tests, 1154 full-gate tests passed, 48 SQL skipped. Static/build/golden/
Compose pass; independent read-only review found no blockers; browser no JS errors.
Evidence: docs/analysis/2026-09-26-first-anchor/README.md. No dependencies added.
Verified patch integration; worktree retained for artifacts and unpushed branch.
Disable --first-anchor to reproduce old times. No serving/training promotion.
