# Work handoff contract

A subagent returns a concise summary, not a raw transcript. The next contributor must be able to continue without verbal context.

## Required fields

```text
Objective and actual status:
Worktree / branch / base SHA:
Owner of changed files:
Changed contracts and files:
Decisions and supporting evidence:
Verification commands and observed results:
What remains unverified and why:
Risks and open questions:
Exact next step:
Cleanup completed, or why the environment was retained:
```

## Rules

- Do not write “done” or “tests pass” without the command and its observed result.
- Separate facts from assumptions and recommendations from already applied changes.
- Identify uncommitted or third-party changes and do not include them in your result.
- A write-task handoff includes a clear ownership boundary; two agents must not edit the same file or contract at the same time.
- The root agent reviews the diff, integrates the results, and personally runs the final gate.
- When stopping, update the active ExecPlan if one exists and always state the exact next step in the handoff.

## Vova foundation 2026-09-25

Objective and actual status: TASK027/031/032 locally integrated, done. Remaining
block tasks028/033/034/035/036/038/056 are not complete.
Worktree / branch / base SHA: primary /Users/cute/MosTransport2026Hack; original
base d8313a4b79273306e41001adaf1f4673649cc304. Task worktrees are siblings
vova-027-runs, vova-031-geometry, vova-032-mapping; branches agent/<same slug>.
Integration worktree vova-033-filters, branch agent/vova-033-filters. Main was
clean and fast-forwarded to202caed after review and parent combined gate.
Owner: for-vova-huesos; backend/frontend plus own plans/ADRs, ten tracker rows.
Changed contracts: run schema602cc47fd0b9; nullable capacity/interval/load API;
explicit inferred/provided/synthetic geometry; versioned canonical mapping service.
Only generated OpenAPI changed under contracts; ML and authored oracle untouched.
Decisions: initial migration unchanged; legacy seed has explicit legacy provenance;
canonical IDs never inferred from integer equality/names; unknown values stay null.
Verification: bootstrap passed. TASK027 clean migrations/no drift and30SQL tests;
rollback/reupgrade passed on owned DB; make check backend292/ML151/frontend48/
contracts119 passed; Chrome E2E18 passed; stack-verify smoke passed and stack removed.
TASK031 full gate303backend/151ML/49frontend/119contracts; networkChrome12 passed.
TASK032 focused20; gate312backend/151ML/47frontend/119contracts. Parent combined
make check passed after integration; SQL skipped by default unit gate were separately
run for the schema task. Independent reviews found and fixed join/null chart/downgrade
and one-sided synthetic-marker errors.
Unverified: organizer mapping/data/model quality unavailable; TASK032 is the mapping
service, TASK034 wires selected forecast geometry. TASK029 owns validated batch
publication and canonical-to-serving catalog resolution; no publisher added here.
Next: TASK028 bounded API in agent/vova-028-window, then033 filters and034 map.
Cleanup: temporary027Docker DB and smoke volumes removed; worktrees retained because
branches remain unpushed. Tooling only in /tmp: uv0.12.13, Node24.21.0/npm11.19.0;
no dependency manifests/locks changed. Playwright browsers installed by e2e-install.

## Vova selection 2026-09-25

Objective/status: TASK028 and033 verified and integrated through branch
agent/vova-033-filters; remaining034/035/036/038/056.
Worktree: /Users/cute/MosTransport2026Hack-worktrees/vova-033-filters; original
base d8313a4, dependency main9bed644; owner for-vova-huesos.
Contracts: optional stop/direction/start/end, half-open bounded windows, same-run
stop_points, run/selection provenance, stable route-stop catalog. UI sends explicit
Moscow instants and separates invalid/loading/empty/error/retained states.
Evidence:02845SQL tests; EXPLAIN uses run/route/time index on10k synthetic rows;
clean migration/no drift; live filteredHTTP and container smoke passed. Parent
make check beforeUI passed.033 final make check331backend/151ML/62frontend/
119reference; Chrome E2E24passed. Calendar ambiguity and late-stop response tests pass.
Assumptions: limits24/31/12buckets and1/31/366days are local bounded-serving budgets,
not organizerSLAs; compound intervals/capacity unavailable without valid aggregation.
Next:034map/timeline integration against stop_points from one snapshot. Legacy
seed has per-stop rows only in first bucket; do not reuse values for other buckets.
Cleanup:028ownedDocker resources removed;033temporaryVite stopped after verification.
Worktrees retained (unpushed branches); no new dependencies or external publication.

## 2026-09-25 — for-vova-huesos: TASK034–035 and aggregation guard

TASK034 base d2d063d, branch agent/vova-034-map, worktree
/Users/cute/MosTransport2026Hack-worktrees/vova-034-map; commit fbd952d locally
fast-forwarded to main after parent make check. Backend346, ML151, frontend70,
reference119 passed; Chrome E2E30 passed. Optional FORECAST_GEOMETRY_MAPPING uses
explicit serving_links and version checks; default synthetic coordinates remain
unmatched OSM. Cached valid mapping requires worker restart when artifacts change.

TASK035 base d2d063d, branch agent/vova-035-freshness, worktree
/Users/cute/MosTransport2026Hack-worktrees/vova-035-freshness; merges verified034.
Panel distinguishes generated/source/UI times and missing coverage/live feed;
legacy source cutoff unavailable. Polling off/15s/60s/300s is a UI check policy,
not source SLA; manual mode disables reconnect polling too. Failure/expiry retains
one response, recovery replaces it; out-of-order responses remain isolated.
Chrome E2E34 passed, including fake-clock outage/recovery, delayed refresh,
manual mode and late response. No dependency or lock changes.

Additional TASK028 correction 91c0293 (original 1abd9d3): only supported count
units may sum sources or stop-window buckets; onboard_load aggregation returns409.
Single source/bucket remains readable. Domain5 and isolated SQL48 passed; no
schema/API change. This protects future publications, not a real-data quality claim.
Worktrees retained clean after commits because branches are unpushed. No remote
publication. Dedicated previews and owned test databases stopped after checks.

## 2026-09-25 — for-vova-huesos: TASK036

Base373bfdf; branch agent/vova-036-values; worktree
/Users/cute/MosTransport2026Hack-worktrees/vova-036-values. Accessible values table
uses the exact selected snapshot, full Moscow timestamps and exact numeric display;
missing intervals differ from zero. No bucket end is fabricated. Interval quality
remains unavailable until lead024 and measured evidence land.
API lacks capacity unit/source/scope metadata, so capacity line and load/reserve
percentages are suppressed. Optional scenario is visibly unavailable: its contract
also lacks run/window binding. It must not silently compute against another run.
make check350backend/151ML/79frontend/119reference and Chrome E2E37 passed.
No dependencies/API/schema/ML/authored-contract edits. Parent local fast-forward
integration after checks; worktree retained unpushed. Recovery is revert, with caveat
that older interface exposes unsupported capacity ratios.

## 2026-09-25 — for-vova-huesos: final TASK038/TASK056 integration

All ten allocated rows are done. TASK038 branch agent/vova-038-accessibility,
base04bf1a9, commit40f95df, worktree
/Users/cute/MosTransport2026Hack-worktrees/vova-038-accessibility: seven additional
browser cases, no CSS changes required. Real Chrome200% setting (1440→720 CSS px),
Tab navigation/focus, reduced motion,390/768/1440, errors/empty/invalid/stale all pass.
TASK056 branch agent/vova-056-export, base04bf1a9, worktree
/Users/cute/MosTransport2026Hack-worktrees/vova-056-export. CSV is derived from one
visible snapshot without another request; contains exact points, nullable bounds,
units/timezone, run/selection/provenance, geometry status, synthetic/stale markers.
Untrusted formula-like text has a reversible text: prefix listed by column.

Parent personally ran combined make check (350 backend,151ML,92frontend,119reference),
clean migration/no drift and48 SQL tests, production-like stack smoke and48 Chrome
E2E tests. All passed. Initial migration, ML and authored shared contracts unchanged;
only generated OpenAPI reflects backward-compatible serving additions. No dependency
or lock changes. No push/PR/publication. Dedicated previews stopped and owned test
Compose resources removed. All10 worktrees retained because branches are unpushed.
See completed/vova-block-final.md for the consolidated result and residual limits.

## 2026-09-25 — synchronize origin/main50630fb with local dispatcher block34a9617

Worktree /Users/cute/MosTransport2026Hack-worktrees/vova-sync-origin, branch
agent/vova-sync-origin. Preserved both histories with a merge and local fast-forward;
no reset/rebase/push. Remote ML files match origin exactly. Tracker preserves all
remote assignments (including019done,020/039in_progress) and ten local completed rows.
Renumbered local edge-geometry ADR0007 because upstream owns0006. Updated architecture
key to implemented run/route/stop/direction/time. UI explicitly displays all available
directions with count-only aggregation and per-direction stop table labels.

Follow-up clarification for lead: ADR0006's (stop,direction) is route-contextual;
EntityCatalog scopes direction by route, and crosswalk correctly keeps route in
its full key. No cross-route meaning of identical direction strings is assumed.

Parent make check passed350backend/265ML/92frontend/119reference. Full Chrome E2E48
passed after isolated rerun of a timed-out nativezoom case; no checks weakened.
See completed/vova-sync-origin.md. Own preview stopped; clean worktree retained
unpushed. Historical task worktrees remain evidence snapshots, not active replicas.
