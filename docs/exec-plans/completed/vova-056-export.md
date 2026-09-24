# TASK-056 — self-describing forecast CSV

Owner for-vova-huesos; base04bf1a9, branch agent/vova-056-export, worktree
/Users/cute/MosTransport2026Hack-worktrees/vova-056-export. TASK038 runs independently
with ownership of CSS and its own E2E. This task owns export helper/component,
App wiring and export tests. No shared CSS edits.

## Contract and checks
One user click exports only visible snapshot.points, without fetch or aggregation.
Every row carries run/route/stop/window, units, bounds, timezone, provenance and
synthetic/stale flags. Selected timestamp is a marker, not a filter on the window.
Missing values are blank, never zero; capacity unavailable matches036. Empty,
initial error and invalid filters disable export. Retained data may export only
with an explicit stale label. Same freshness rule as035, computed at click.
Source cutoff uses035's honest legacy policy. Source coverage remains unavailable.

RFC4180 quoting/CRLF and UTF-8 CSV are sufficient for <=31 bounded rows:
https://www.rfc-editor.org/rfc/rfc4180
Untrusted text may be interpreted as spreadsheet formulas; quotes alone do not
prevent it. OWASP notes editor-dependent behavior and save/reopen limitations:
https://owasp.org/www-community/attacks/CSV_Injection
Use a literal text: prefix for dangerous leading characters (including fullwidth
and controls); record escaped_text_columns per row so callers can reverse exact
text. Numeric values are not altered. This is a report download, not a typed
Excel workbook; text identifiers may still be autoformatted by import software.
No dependency or new file-format library needed; test with independent parser.

Focused checks: known rows/window parity, null/zero, escaped comma/quote/newline/
formula fields, stale+legacy metadata; browser downloaded file equals visible table
and route/stop selection, no export request, empty/error/invalid disabled.
Required gate make check; full E2E also run with final038 integration.

## Verification so far
13 focused CSV tests passed (three horizons, exact decimals, null/zero, arbitrary
quoted/newline/formula-like names). Four actual Chrome download tests passed:
selected-stop table parity without refetch, retained stale export, empty/error and
invalid-window suppression. Independent review found mapping-status omission;
added matching run/entity/graph checks and exported status/reason/counts/synthetic,
so a configured but incompatible crosswalk is never silently certified by report.

## Final observed result
Parent combined make check passed: backend350, ML151, frontend92, reference119;
48 opt-in SQL tests separately passed after clean migration/no schema drift.
Parent full Chrome E2E48 passed after ff integration of038 40f95df, including
actual200% browser zoom and download parity. make stack-verify built the final
application and passed database/API/forecast/frontend smoke; own resources removed.
No dependencies, locks, authored contracts or initial migration changed. Worktree
retained unpushed; integration is local fast-forward to main. No external report sent.
