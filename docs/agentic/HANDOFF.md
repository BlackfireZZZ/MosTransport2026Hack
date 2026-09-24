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
