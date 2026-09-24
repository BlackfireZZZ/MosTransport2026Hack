# TASK-033 — dispatcher stop and window filters

## Purpose and acceptance
A dispatcher selects route, stop and half-open time window in Europe/Moscow.
Requests and visible results share that selection; invalid input sends no query.
Changing route clears an incompatible stop; changing horizon clears its window.
Loading, empty and errors have keyboard-accessible recovery. Full-route defaults
and existing scenario behavior stay compatible; filtered scenarios are explicitly
unavailable until that optional contract supports the selected scope.

## Context and boundaries
Owner for-vova-huesos; branch agent/vova-033-filters, worktree
/Users/cute/MosTransport2026Hack-worktrees/vova-033-filters. Original base
 d8313a4b79273306e41001adaf1f4673649cc304; verified foundation integrated at024d138.
TASK028 at9bed644 implements stop_id/start/end/direction_id and route stop catalog.
Do not implement dependent UI until its verified contract is integrated.
Scope frontend/api, feature hook/filter controls, App and deterministic tests.

## Evidence and research
Existing useForecast caches by route/horizon, retains same-key stale data, and
isolates out-of-order responses; its existing tests supply the regression oracle.
Extend that key with every filter and keep request I/O exclusively in src/api.
TanStack documents query key variables as dependencies:
https://tanstack.com/query/latest/docs/framework/react/guides/query-keys
Native datetime-local has no timezone; render Moscow explicitly and convert before
transport, independent of the browser locale:
https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/input/datetime-local
No new dependency or design tokens.

## Progress and validation
Foundation bootstrap and combined make check passed. TASK028 integrated after parent make check passed.
Smallest checks: invalid/partial dates make no request; known Moscow conversion;
route switch drops stop; stop/time late responses cannot replace current selection.
Required gate: frontend-check, make check and Chrome E2E (all horizons, empty/error,
keyboard and responsive states). Recovery: revert this UI commit; bounded backend
still accepts existing route/horizon requests.

## Observed completion
2026-09-25 make check passed: backend331 (45 opt-inSQL tests separately passed in028),
ML151, frontend62, reference119; lint/types/build/Compose/contracts passed.
make e2e against isolated43133 Chrome passed24 scenarios including all horizons,
stop/window query parity, invalid partial input, empty selection, catalog retry,
keyboard and390/768/1440 accessibility. Six timezone tests cover year boundary,
historical offsets, nonexistent and ambiguous Moscow hours. Independent review
fixed invalid-selection retry, empty-copy ambiguity and historical overlap.
No dependencies or locks changed. All HTTP stays in src/api. Filter context owns
query keys and AbortSignal; previous query results never enter a new selection.
Recovery is revert of this UI commit. Worktree retained because branch is unpushed.
