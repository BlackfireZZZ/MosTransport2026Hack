# Pre-hackathon backlog analysis

## Purpose and acceptance

Populate the English agent tracker with evidence-backed work that can be completed
before organizer data arrives. Each task must have a bounded result, code evidence,
acceptance checks, risk, dependencies, execution order, and an ownership lane.
Separate executable synthetic-data work from decisions that require real data.
Do not implement the proposed product changes or claim synthetic accuracy as real quality.

## Context and scope

Sources: root README/design/rules, product concept, architecture/ADRs, backend,
frontend, ML, migrations, tests, and operational scripts. The user supplied and corrected the official statement during analysis; the final
tram passenger-flow statement is preserved in `docs/product/TASK.md`. Discard the
superseded delay brief. Record unknown judging rules, schema, target definition,
coverage, and permitted pre-event reuse explicitly. Pin the source in root, product,
architecture, design, task-template, and subtree entry documents.

Lead owns documentation writes. Three read-only agents inspect backend/infrastructure,
ML/scenarios, and frontend. No other agent modifies files or runtime dependencies.
Root task tracker setup was completed and locally committed before this larger task.

## Working location

- Primary: `/home/blackfire/Hackatons/MosTransport2026Hack`.
- Base: `790f006898ab954dd06316d8574b843341228dc7`.
- Branch: `agent/pre-hackathon-backlog`.
- Worktree: `/home/blackfire/Hackatons/MosTransport2026Hack-worktrees/pre-hackathon-backlog`.
- Integration owner: Codex lead; primary checkout stays read-only until verified integration.

## Progress and decisions

- [x] Existing tracker setup verified; initial `make check` passed with Node 24.19.0
  and locked frontend dependencies (61 backend, 3 ML, 23 frontend tests).
- [x] Record clean base and create dedicated worktree via `make agent-create`.
- [x] Complete source audit and independent review findings.
- [x] Write classified backlog, dependency order, parallel lanes, and data-day gates.
- [x] Validate links, ID uniqueness, dependency DAG, status readiness, diff, and `make check`.
- [x] Integrate verified documentation and report result location / retained worktree.

## Research evidence

Primary-source rationale and limitations will be linked in the analysis document.
Choose baseline/backtesting and explicit service contracts before any graph neural
network. GTFS is a reference for transit semantics, not an assumed organizer format.
No new production dependency or expensive architectural decision is introduced by
this documentation task; future R2 tasks must conduct their own implementation research.

## Validation and recovery

Focused checks: all relative Markdown paths and fragment links resolve, each task
has a unique ID, dependencies exist and are acyclic, ready tasks have no unfinished
prerequisites, each implementation card defines acceptance/verification and a
data-readiness boundary. Review against existing contracts and `git diff --check`.
Final gate: lead runs `make check` in the dedicated worktree under supported runtimes.
Recovery: revert the documentation commit; no runtime or persisted data changes.
Do not remove the worktree or its unpushed branch automatically.

## Observed results and integration

- Lead final gate: `PATH=/home/blackfire/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH make check`
  in the dedicated worktree, exit 0. Backend 61, ML 3, frontend 23 tests passed;
  Ruff/mypy/ESLint/types/build/OpenAPI drift/Compose configuration passed.
- Focused Python validator parsed Markdown links/anchors, tracker rows and card
  headings; verified 58 unique IDs, existing acyclic dependencies, valid readiness,
  no optional prerequisite in required chains, and required fields in every card.
  Initial pass covered 169 local links; final pass includes the completed-plan link.
- `git diff --check`: exit 0. Diff restricted to documentation; no runtime, model,
  API, migrations, manifests, lock files, raw data or generated artifacts changed.
- Backend reviewer found an unnecessary boosted-model prerequisite for real-data
  evaluation; removed it so an executable baseline can be evaluated/promoted alone.
  ML and frontend reviews found no blocking issues.
- Integration method: local documentation commit, then `git merge --ff-only
  agent/pre-hackathon-backlog` into clean primary `main`; no external publication.
- Worktree is retained for review because its branch is unpushed. No force cleanup,
  branch deletion or shared-volume operation is performed. The primary checkout
  contains the integrated result; the branch/worktree preserve the review history.
- Next step: user/lead allocates ready tasks. No future product task was executed.
