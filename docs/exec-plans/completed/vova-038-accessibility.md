# TASK-038 dispatcher accessibility

## Purpose / observable result
Filters, provenance, map and open values remain usable at 390/768/1440 CSS pixels, with keyboard, enlarged content and reduced motion. No document horizontal overflow or axe violations in success/recovery states; synthetic fixtures do not prove model quality.

## Context
Base 04bf1a9; branch agent/vova-038-accessibility in /Users/cute/MosTransport2026Hack-worktrees/vova-038-accessibility. Primary remains read-only. DESIGN.md, TASK-038 and existing dashboard/map/values/filter/freshness suites define behavior.

## Scope / non-goals
Only index.css, dispatcher-accessibility.e2e.ts and this plan. No App/API/components/fixtures/dependencies/shared documentation edits.

## Acceptance
Three viewport combined success/stale screenshots; error/retry, invalid/empty filters with axe; actual Tab reachability; enlargement/reflow and reduced motion. Allow internal table scrolling, preserve selection behavior.

## Progress / decisions
Bootstrap passed. Hypothesis: existing component semantics suffice; CSS changes only after a failing browser assertion demonstrates a defect. Existing tests cover horizon correctness; new tests cover integrated accessibility.

## Research evidence
https://www.w3.org/WAI/WCAG21/Understanding/reflow documents equivalent reduced CSS viewport and exceptions for two-dimensional content. https://www.w3.org/WAI/WCAG21/Understanding/resize-text requires usability at 200% enlargement. The initial CSS zoom probe overflowed because media queries retained the desktop width; it was rejected as a browser-zoom substitute. The final test sets native Chrome zoom to 200% through chrome://settings/appearance in a disposable persistent profile. It asserts innerWidth 720 from a 1440 viewport while root CSS zoom remains 1. Full Chromium is required because headless-shell has no settings UI. CDP captures doubled physical bounds to avoid Playwright clipping native-zoom screenshots.

## Validation / recovery
Observed results on unique preview 43138 with Chrome /Applications/Google Chrome.app/Contents/MacOS/Google Chrome:
- `make bootstrap`: passed; existing dependencies, no changes.
- `npx playwright test dispatcher-accessibility --workers=2`: 7 passed.
- `make check`: passed; backend 350 passed / 48 SQL tests skipped in this non-DB gate, ML 151, frontend 79, contracts 119; architecture, lint, types, build, generated contracts and Compose validation passed.
- `make frontend-check` after screenshot changes: passed.
- `npx playwright test --workers=2`: 44 passed, including all 7 new cases.
- Final native-zoom test after explicitly selecting full Chromium: 1 passed.
- `git diff --check`: passed. No CSS defects demonstrated; no product code changed.

Logs: /tmp/task038-check.log, /tmp/task038-frontend.log, /tmp/task038-e2e.log, /tmp/task038-final-zoom.log. Twelve screenshot artifacts reside under this worktree's frontend/test-results/dispatcher-accessibility.* directories; native zoom is dispatcher-native-zoom-200-full.png. Final isolated native-zoom rerun is under /tmp/task038-final-zoom. Inspected actual success/stale views for all widths, native 200%, keyboard, reduced motion and error/filter/empty captures: controls readable, no overlap, internal table/chart scrolling stays within cards, missing map background has text recovery and accessible stop table.

No dependencies, API/schema changes, authored contract edits or passenger data. Browser fixtures are synthetic; this does not establish real-data quality or complete assistive-technology certification. Revert isolated commit to recover. Parent owns integration and final combined gate; retain clean worktree until integration/cleanup authorization.
