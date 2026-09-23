# Complete TASK-015/025 before synthetic generation

## Purpose and acceptance

Reopen prematurely completed contracts. Invalid calendar buckets, inconsistent
provenance/uncertainty and manifest mismatches must fail before publication.
Normalized event contracts must distinguish event time from availability, known
entities from ambiguous names, and observed zero from missing coverage. Existing
HTTP API stays unchanged; shared reference contracts are not runtime imports.

## Context and ownership

Base cece609fff4ea9b7e1e12dbbb4e303b9244b49c8; primary clean.
Worktree `/home/blackfire/Hackatons/MosTransport2026Hack-worktrees/complete-data-contracts`,
branch `agent/complete-data-contracts`. Lead owns forecast contract, fixtures,
shared gate/CI and docs. Calendar agent owns calendar_v1.py and its test; raw-data
agent owns data_v1.py and its test. No overlapping file ownership.
`rg` confirms reference consumers are backend/ML contract tests only. JSON schema
has no runtime consumers. Production packaging remains TASK-029.

## Decisions / scope

See ADR-0005 for provisional internal calendar/data policy. A forecast publication
contains complete temporal coverage for every represented entity; subset entity
selection is allowed, partial time coverage is not. Values share one run envelope.
Synthetic target and flag agree in both directions; all points either have bounds
with one method/level or all omit uncertainty. Manifest fields must match before
consumer use. No organizer field mapping or measured accuracy claim.

## Evidence and research

Independent executable audit accepted years-long hourly buckets, out-of-horizon
points, false synthetic flags and bounds without interval metadata. TASK015
previously had no calendar/raw/entity/missing-zero tests. Root contracts/tests
was excluded from make check. These are correctness gaps, not new product scope.
Python datetime/zoneinfo official docs confirm astimezone preserves the instant
and calendar-aware dates must be explicit. Pydantic model validators already used
in this repository suffice; no dependency change. Web tool hung; official Python
pages were successfully read via HTTPS urllib with timeout, Pydantic docs returned
HTTP error. Existing validator implementation is the Pydantic API evidence.

## Verification and recovery

Start with independent regression cases, then schema snapshot comparison, both
consumer suites, Ruff/mypy, make check, and Docker smoke for the added CI gate.
Review by independent agent; lead final integration gate. Revert code/schema and
fixtures together if rollback required. No DB/API migration or live artifact exists.

## Progress

Completed in isolated worktree. Independent review approved after 117 passing
shared tests; its extreme-date observation was fixed and two regression cases added.
Lead final `make check`: exit 0; 292 backend passed / 10 SQL skipped, 50 ML,
47 frontend and 119 shared-contract tests passed, plus Ruff/mypy/architecture,
ML golden evaluation, build, OpenAPI drift/schema snapshot and Compose checks.
`make stack-verify`: exit 0, built-stack smoke passed and owned resources removed.
The subsequent extreme-date fix changes reference validators only, not container
runtime; full make check was repeated after it. Focused raw-data suite: 44 passed;
calendar suite: 34 passed. No dependencies/locks or HTTP payloads changed.

Corrected the misleading backend unknown-version test name and previous tracker
completion claims. Main integration is fast-forward from recorded clean base;
no push. Worktree/branch retained for review. Organizer assumptions remain open;
TASK-016 may now consume the normalized wire contracts. Production packaging and
mandatory catalog/manifest checks at publication remain consumer responsibilities.
