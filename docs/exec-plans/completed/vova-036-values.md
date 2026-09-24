# TASK-036 — inspectable values and honest units

Owner for-vova-huesos, base373bfdf, branch agent/vova-036-values, worktree
/Users/cute/MosTransport2026Hack-worktrees/vova-036-values.

## Claim and evidence
Every plotted point is inspectable through a keyboard-accessible table with full
Europe/Moscow start, exact numeric values, target/unit and nullable paired bounds.
Unknown bounds/capacity remain distinct from zero. Existing forecast.v1, ADR0005,
ACCEPTANCE.md and API schema are authoritative; no new model/contract is invented.
TASK024 remains backlog. Per allocation, implement frozen fields and explicitly
mark interval quality unavailable. Nominal metadata is not calibrated quality.

API capacity has no unit, source or compatible scope evidence. Raw legacy numbers
cannot establish that events are comparable to vehicle seats. Suppress capacity
line/load ratios and show unavailable explanation, including optional scenario:
its request also lacks run/window identity and cannot promise snapshot parity.
Independent review confirmed that disabling the optional scenario is narrower
than redesigning its contract. Preserve component for future validated integration.

## Checks and rollback
Known value tests at year/leap boundaries; missing vszero bounds; nominalmetadata
never implies quality. Browser keyboard table selection, all horizons and axe.
Run make check and make e2e. No dependencies/backend/ML/contracts authored changes.
Rollback frontend commit restores legacy UI but also unsupported capacity claims.

## Observed results
Focused calendar/known-value tests passed, including zero bounds, missing bounds,
29 February and year rollover. Independent review found no blockers; replaced
rate-like unit wording with neutral interval values and aligned the missing-band
notice with bound validation. make check passed350backend/151ML/79frontend/
119reference; 48opt-inSQL separately verified028. Full Chrome E2E37 passed,
including keyboard selection of accessible table rows for day/month/year and axe.
TASK024 remains outside allocation; no calibration claim is made. No dependencies,
API or authored shared contracts changed. Own preview43136 stopped after checks.
