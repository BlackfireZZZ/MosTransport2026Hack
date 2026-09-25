# Organizer-data research handoff — TASK-059

## Objective and status

Completed first-data EDA, source reconciliation, exploratory seasonal benchmarks,
and concrete application/ML integration assessment. No production model, adapter,
API, database, dependency, runtime or UI contract was changed. No submission was
sent. TASK-020/039 remain owned by their existing leads.

## Location and ownership

- Base SHA: `0767619f487725e516ae3d00ef6ef138520160f1`.
- Primary checkout: `/Users/cute/MosTransport2026Hack`, branch `main`.
- Research worktree: `/Users/cute/MosTransport2026Hack-worktrees/real-data-eda`.
- Branch: `agent/real-data-eda`.
- Owner: real-data-eda lead; `docs/analysis/2026-09-25-organizer-data/*`, new tracker
  TASK-059 and a dated evidence update to unassigned TASK-049.
- Independent subagent: read-only code/contract and report review; no file ownership.
- Original untracked ZIP, PDF and `.DS_Store` preserved outside the worktree.

## Decisions and evidence

Archive SHA-256 and all counters are in `evidence.json`. After union, event-time
filtering before November and success-only counting, all 57,551 sparse labels
match exactly (59,667,191 events). November's 562 successful tail rows are excluded.
Route5 has one failed raw validation and no positive target support. Reference
geometry is incomplete for forecast routes and includes post-origin snapshots.

The report recommends a versioned route-level publication path, not fake stop
identity. Training and scoring operate on aggregates; one issued forecast feeds
both submission and API. Baseline experiments do not constitute production model
promotion or a score on the hidden period. Missing keys mean zero rows in this
extract; delivery coverage and service state are still separate unresolved inputs.

## Verification commands and observed results

Run date: 2026-09-25. Research Python is the bundled interpreter documented in README.

- `profile.py <archive> /tmp/tram-eda/results`: exit0, all 62,443,497 rows read;
  101.32s train, 26.99s test. Full six-column source scan, not sampling.
- `reconcile.py <archive> /tmp/tram-eda/results`: exit0; exact full key/value
  assertions pass; ZIP hash, all reference sheets and route5 checked.
- `baselines.py <archive> /tmp/tram-eda/results`: exit0, ten experiments over two
  frozen-origin folds. No future observations enter fitted profiles.
- Formatted saved `baselines.py <archive> /tmp/tram-eda-reproduce`, followed by
  `cmp .../results/baselines.json .../tram-eda-reproduce/baselines.json`: exit0,
  byte-identical results.
- `.venv/bin/ruff check --no-cache docs/analysis/2026-09-25-organizer-data/*.py`:
  all checks passed. Python AST parsing and evidence arithmetic assertions passed.
- Parent `PATH=/tmp/tramflow-tools/bin:/tmp/tramflow-node/node_modules/.bin:$PATH make check`:
  exit0; backend350 passed/48 SQL skipped, ML265 passed, frontend92 passed,
  reference119 passed. Architecture/Ruff/mypy/ESLint/TypeScript, ML golden-eval,
  production frontend build, OpenAPI drift and Compose validation passed.
- `git diff --check`: exit0 before integration.
- Independent report/code review: pass after clarifying that the performance
  documentation requirement originates in the PDF, not the ZIP README.

Initial bootstrap used system npm10.8.2 and failed its engine gate. Reusing the
already installed npm11.19 with Node24.21 and existing lockfile succeeded. No
manifest/lock edits or new dependencies. Initial research lint caught compact
one-line formatting; Ruff formatting resolved it and the final check passed.
One sandboxed Ruff invocation could not write cache; `--no-cache` resolved it.

## Limits and next action

Raw transaction-ID uniqueness, passenger identity, all fourteen-field quality,
actual delivery timestamps and historical service completeness are unverified.
The archive supplies no separate licence/retention policy. Data was processed
locally and raw data was not committed or externally published. PDF pages were
rendered and all six inspected by the parent. No DB migration, SQL runtime,
browser E2E or load test was needed for these research-only changes; the 48 SQL
skips must not be mistaken for a newly verified production integration.

Next: owner review of target/availability/route-only scope, backward-compatible
route-window contract and real aggregate adapter; coordinate TASK-020/039, then
TASK-029 publication and TASK-058 parity tests. See README priority table.

## Integration and cleanup

Integration method: local fast-forward of the reviewed research commit into main,
with original user files preserved; no push/PR/external publication.
Keep this worktree and branch because the branch is unpushed; do not force cleanup.
Temporary aggregate intermediates remain in `/tmp/tram-eda`; no services or Docker
volumes were started by this task. Only locked local dependency environments were
prepared for verification.
