# TASK-035 — provenance and refresh

## Contract and falsifiable claim
A failed or overdue UI refresh retains the same successful snapshot and labels it
stale; recovery replaces the entire response. Generation, source cutoff and UI
fetch times are separate. Missing live observations and coverage are explicit.
Configurable polling changes checks, never the forecast origin or source cutoff.
Legacy demo cutoff is not an observed source timestamp.

## Scope and prerequisites
Owner for-vova-huesos. Worktree /Users/cute/MosTransport2026Hack-worktrees/vova-035-freshness,
branch agent/vova-035-freshness, base d2d063d. Integrate verified TASK034 before
App/hook wiring. Existing ForecastResponse.run and Query dataUpdatedAt/isRefetchError
are authoritative contracts; existing hooks tests verify retained and isolated data.
No backend, dependency, ML or authored-contract changes are needed.

## Evidence and checks
TanStack query keys isolate filters and AbortSignal cancels obsolete requests.
https://tanstack.com/query/latest/docs/framework/react/guides/query-keys
https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults
Smallest checks: pure freshness boundaries and fake-clock UI outage/recovery;
out-of-order route/stop requests retain only the selected response.
Run focused tests, make check and make e2e. UI freshness is a local check policy,
not a source-data SLA. Existing Card, select and metadata styles follow DESIGN.md.

## Progress
Bootstrap passed on Node24/npm11/uv0.12.13. Independent helper/component work only
until TASK034 merges. Recovery: revert frontend change; API is unchanged.

Independent review confirmed that legacy data_cutoff duplicates seed generation and
must stay unavailable as source evidence. Corrected test units to event_count and
kept epoch zero valid in the general timestamp formatter. Unit labels depend on
both target and unit; unknown combinations retain their literal metadata.
Focused helper/panel tests: 5 passed; frontend lint/type check passed before App
integration. Prepared browser tests for polling outage/recovery, manual expiry and
late responses, using TASK034's mapped snapshot helper once integrated.

## Completion evidence
Integrated034 fbd952d and occupancy guard91c0293. Focused 5 helper/panel tests
passed; manual-reconnect regression added after independent review reproduced an
unwanted request. Removed unconditional synthetic graph description. Full Chrome
E2E34 passed, including outage, recovery, expiry while request hangs, manual check
and late horizon response. Generic fixtures with no run now visibly say unknown
provenance. No telemetry, source coverage or calibration claims introduced.
No dependency/lock changes. Generated API contract unchanged in035.

Final parent make check passed: backend350 (48 SQL opt-in separately passed), ML151, frontend76, reference119; lint/types/build/Compose/contracts passed.
