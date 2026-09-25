# Agent task tracker

This is the repository-local index of agent work. Read it before selecting a task
and update it when ownership, status, blockers, or verification evidence changes.
All entries and task specifications use English. The [authoritative task](../product/TASK.md) governs scope; [the analysis and execution plan](../product/PRE_HACKATHON_ANALYSIS.md) explains priorities, evidence, and parallel lanes. An entry records work; it does
not authorize actions outside the user's scope or [permission boundaries](PERMISSIONS.md).

## Classification

| Field | Values and meaning |
|---|---|
| ID | Stable `TASK-NNN` identifier; never reuse an ID. The integration owner allocates IDs to avoid parallel collisions. |
| Type | `feature`, `bug`, `research`, `docs`, `maintenance`, `debt` |
| Area | One or more of `backend`, `frontend`, `ml`, `data`, `infra`, `ci`, `docs` |
| Priority | `P0`: active incident or correctness blocker; `P1`: blocks an agreed milestone; `P2`: normal planned work; `P3`: optional improvement |
| Risk | `R0`–`R3` as defined in [PERMISSIONS.md](PERMISSIONS.md); priority does not grant authority. |
| Owner | One named integration owner, or `unassigned`; record delegated file ownership in the specification. |
| Dependencies | Blocking task IDs, or `none`; prerequisites must be complete before the task is `ready`. |

| Status | Entry / exit condition |
|---|---|
| `backlog` | Captured outcome; scope, evidence, or acceptance still needs refinement. |
| `ready` | Bounded scope, acceptance criteria, verification commands, authority, and dependencies are resolved. |
| `in_progress` | One owner has claimed the task and recorded its working location. |
| `blocked` | Record the concrete blocker, who or what can resolve it, and the next action; resume only when resolved. |
| `review` | Implementation and evidence are available for review; required failed checks remain visible. |
| `done` | Acceptance and required checks pass, review is complete, and the result location / integration state is recorded. |
| `cancelled` | Record the reason; retain the ID and history. |

## Working agreement

- Select an authorized, unassigned `ready` task with the highest priority; resolve
  ties with the integration owner. Do not take over another owner's work silently.
- Keep one coherent outcome per task. Link a specification using
  [TASK_SPEC.md](TASK_SPEC.md), either below the index or in an existing issue.
  Large tasks use [ExecPlans](../exec-plans/README.md) and the worktree rules in
  [AGENTS.md](../../AGENTS.md). Do not create an ExecPlan for every small task.
- The lead owns this shared index during parallel work. Subagents report through
  [HANDOFF.md](HANDOFF.md); they do not compete to edit the same row.
- The serving and map/UI block allocated to a second agent is defined in
  [FOR_VOVA_HUESOS.md](FOR_VOVA_HUESOS.md); its ten rows and file boundaries
  belong to that owner while the block is open.
- Record the branch, worktree, base SHA, changed-file ownership, exact next action,
  and dated command results in the task detail. Update before handing off or ending
  a session. Never replace a failed check with an unsupported success claim.
- Preserve acceptance criteria during implementation. Record scope changes and
  their authorization; do not weaken criteria to close a task.
- Keep technical compromises in the [debt register](../exec-plans/tech-debt.md).
  A `debt` task links to that record rather than duplicating its risk and closure condition.
- If an external issue exists, link it as the canonical specification. This index
  owns the local status and ownership; do not maintain two competing specifications.

## Execution metadata

The table is the status/ownership source of truth. Every future task is `unassigned`;
lanes describe file ownership boundaries, not assigned people. `A`–`J` are dependency
waves, not calendar dates. A task may start as soon as all listed prerequisites are
`done` and its contract/authority is confirmed; the dependency list overrides wave
labels. `OPTIONAL` is outside the mandatory delivery path; `DATA` requires organizer
inputs. Dependencies include contract-freeze tasks; implementation agents may draft
against reviewed fixtures, but must not mark dependent tasks ready early.

Size is a rough planning estimate for one contributor with tooling available:
`S` up to half a day, `M` roughly 1–2 days, `L` roughly 2–4 days. These are not delivery
promises or a claim all tasks fit the hackathon. Split an L task into linked milestones
before implementation. Follow root worktree/ExecPlan criteria regardless of size label.

Each card supplies the outcome/hypothesis, code evidence, scope, acceptance and
smallest check. Before claiming it, record the actual owner, branch/base/worktree,
file boundaries, dated results and next step using [TASK_SPEC.md](TASK_SPEC.md).
All implementation tasks also run `make check` after focused checks. API/schema/data/
model/runtime changes require R2 review, isolated worktrees and all applicable rows
of [VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md). New complex mechanisms require
primary-source research; a list entry is not an architectural decision or permission
to install dependencies. Do not silently weaken existing contracts.

## Task index

| ID | Outcome / specification | Type | Area | Priority | Risk | Status | Owner | Lane | Dependencies | Wave | Size |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TASK-001 | [Create a discoverable agent task tracker](#task-001) | docs | docs | P2 | R1 | done | Codex lead | CONTRACT | none | A | S |
| TASK-002 | [Analyze and populate the pre-hackathon backlog](#task-002) | docs | docs | P1 | R1 | done | Codex lead | CONTRACT | TASK-001 | A | M |
| TASK-003 | [Freeze acceptance assumptions and organizer questions](#task-003) | research | docs | P1 | R1 | done | Codex lead | CONTRACT | none | A | S |
| TASK-004 | [Reject invalid evaluation inputs and gate every horizon](#task-004) | bug | ml | P1 | R1 | done | Codex lead | ML-EVAL | none | A | S |
| TASK-005 | [Make demonstration and model capability labels truthful](#task-005) | bug | frontend | P1 | R1 | done | integration lead | UI-SHELL | none | A | S |
| TASK-006 | [Bind scenario output to the submitted parameter snapshot](#task-006) | bug | frontend | P2 | R1 | done | integration lead | UI-SCENARIO | none | A | S |
| TASK-007 | [Preserve stale forecasts and gate queries on valid selection](#task-007) | bug | frontend | P1 | R1 | done | integration lead | UI-SHELL | TASK-005 | B | S |
| TASK-008 | [Keep the local network usable without a remote basemap](#task-008) | bug | frontend | P1 | R1 | done | integration lead | UI-MAP | none | A | M |
| TASK-009 | [Expose partial network query failures and scoped retries](#task-009) | bug | frontend | P1 | R1 | done | integration lead | UI-MAP | TASK-008 | B | S |
| TASK-010 | [Build internally consistent browser forecast fixtures](#task-010) | maintenance | frontend | P1 | R1 | done | integration lead | QA-UI | none | A | S |
| TASK-011 | [Reject incomplete Overpass extracts before writing outputs](#task-011) | bug | data | P1 | R1 | done | Codex lead | GRAPH-EXPORT | none | A | S |
| TASK-012 | [Validate graph structures and numerical invariants strictly](#task-012) | bug | backend,data | P1 | R1 | done | Codex lead | GRAPH-LOAD | none | A | M |
| TASK-013 | [Keep exception diagnostics free of raw secrets and identifiers](#task-013) | bug | backend | P1 | R1 | done | safe-error-diagnostics lead | OBSERVABILITY | none | A | S |
| TASK-014 | [Cover current forecast HTTP and numerical boundary behavior](#task-014) | maintenance | backend | P1 | R1 | done | integration lead | API-TEST | none | A | S |
| TASK-015 | [Define canonical targets, entities, calendar and dataset manifests](#task-015) | feature | data,ml,backend | P1 | R2 | done | complete-data-contracts lead | CONTRACT | TASK-003 | B | M |
| TASK-016 | [Generate reproducible multiyear synthetic transport datasets](#task-016) | feature | data,ml | P1 | R2 | done | synthetic-transport-data lead | DATA | TASK-015 | B | M |
| TASK-017 | [Implement bounded historical ingestion with restart and quarantine](#task-017) | feature | data,ml | P1 | R2 | done | historical-ingestion lead | DATA | TASK-016 | C | L |
| TASK-018 | [Align validations and telemetry with explicit identity rules](#task-018) | feature | data,ml | P1 | R2 | done | identity-alignment lead | DATA-MAPPING | TASK-015, TASK-016 | C | M |
| TASK-019 | [Build leakage-safe aggregates and horizon-specific features](#task-019) | feature | data,ml | P1 | R2 | done | horizon-features lead | DATA-FEATURES | TASK-017, TASK-018 | D | L |
| TASK-020 | [Implement history-aware rolling-origin backtesting](#task-020) | feature | ml | P1 | R2 | in_progress | rolling-backtest lead | ML-EVAL | TASK-004, TASK-019 | D | M |
| TASK-021 | [Implement executable seasonal and simple-regression baselines](#task-021) | feature | ml | P1 | R2 | backlog | unassigned | ML-MODEL | TASK-020 | E | M |
| TASK-022 | [Report operational slices and interval quality without hiding failures](#task-022) | feature | ml | P1 | R2 | backlog | unassigned | ML-EVAL | TASK-020 | E | M |
| TASK-023 | [Add a reproducible lag/calendar boosting candidate](#task-023) | feature | ml | P2 | R2 | backlog | unassigned | ML-MODEL | TASK-021, TASK-022 | F | M |
| TASK-024 | [Produce calibrated-interval scaffolding with past-only calibration](#task-024) | feature | ml | P1 | R2 | backlog | unassigned | ML-UNCERTAINTY | TASK-021, TASK-022 | F | M |
| TASK-025 | [Freeze the versioned offline forecast publication contract](#task-025) | feature | backend,ml | P1 | R2 | done | complete-data-contracts lead | CONTRACT | TASK-015 | C | M |
| TASK-026 | [Add isolated PostgreSQL repository integration test support](#task-026) | maintenance | backend,ci | P1 | R2 | done | integration lead | INFRA | none | A | M |
| TASK-027 | [Persist coherent forecast runs and enforce value invariants](#task-027) | feature | backend | P1 | R2 | done | for-vova-huesos | SERVING | TASK-025, TASK-026 | D | L |
| TASK-028 | [Serve bounded route, stop and time-window forecast aggregates](#task-028) | feature | backend | P1 | R2 | done | for-vova-huesos | SERVING | TASK-027, TASK-015 | E | L |
| TASK-029 | [Publish validated batch artifacts atomically and idempotently](#task-029) | feature | backend,ml | P1 | R2 | backlog | unassigned | BATCH-PUBLISH | TASK-025, TASK-027 | G | M |
| TASK-030 | [Publish graph artifacts as a validated versioned set](#task-030) | feature | data,backend | P1 | R2 | done | Codex lead | GRAPH-EXPORT | TASK-011, TASK-012 | B | M |
| TASK-031 | [Make missing per-edge geometry explicit](#task-031) | feature | backend,frontend | P2 | R2 | done | for-vova-huesos | GRAPH-LOAD | TASK-012, TASK-030 | C | M |
| TASK-032 | [Join forecast entities to versioned Moscow map geometry](#task-032) | feature | data,backend | P1 | R2 | done | for-vova-huesos | DATA-MAPPING | TASK-018, TASK-030 | D | M |
| TASK-033 | [Add dispatcher stop and time-window filters](#task-033) | feature | frontend | P1 | R2 | done | for-vova-huesos | UI-SHELL | TASK-028, TASK-010 | F | M |
| TASK-034 | [Synchronize forecast map, time selection and chart state](#task-034) | feature | frontend,backend | P1 | R2 | done | for-vova-huesos | UI-MAP | TASK-028, TASK-032, TASK-033, TASK-008 | G | L |
| TASK-035 | [Expose provenance and trustworthy real-time refresh state](#task-035) | feature | frontend,backend | P1 | R2 | done | for-vova-huesos | UI-SHELL | TASK-025, TASK-028, TASK-007, TASK-034 | H | M |
| TASK-036 | [Make forecast uncertainty and units inspectable without hover](#task-036) | feature | frontend | P1 | R1 | done | for-vova-huesos | UI-CHART | TASK-015, TASK-024, TASK-033, TASK-035 | H | M |
| TASK-037 | [Cover network navigation and outages in browser tests](#task-037) | maintenance | frontend | P1 | R1 | done | integration lead | QA-UI | TASK-008, TASK-009, TASK-010 | C | M |
| TASK-038 | [Verify dispatcher accessibility and responsive operation](#task-038) | maintenance | frontend | P1 | R1 | done | for-vova-huesos | QA-UI | TASK-033, TASK-034, TASK-035, TASK-036, TASK-037 | I | M |
| TASK-039 | [Build a first-data profiling and adaptation toolkit](#task-039) | feature | data,ml | P1 | R2 | in_progress | intake-profiling lead | DATA | TASK-017, TASK-018, TASK-019 | E | M |
| TASK-040 | [Observe batch quality, publication and forecast freshness](#task-040) | feature | backend,ml | P2 | R2 | backlog | unassigned | OBSERVABILITY | TASK-029, TASK-035, TASK-013 | I | M |
| TASK-041 | [Measure million-row ingestion and bounded query/UI budgets](#task-041) | research | data,backend,frontend | P1 | R1 | backlog | unassigned | PERFORMANCE | TASK-017, TASK-028, TASK-034, TASK-026 | H | M |
| TASK-042 | [Verify offline synthetic data-to-map integration](#task-042) | maintenance | backend,frontend,ml,infra | P1 | R2 | backlog | unassigned | INTEGRATION | TASK-058, TASK-034, TASK-035, TASK-036, TASK-037 | I | L |
| TASK-043 | [Rehearse first-data arrival and freeze a reviewable demo](#task-043) | maintenance | docs,infra | P1 | R2 | backlog | unassigned | INTEGRATION | TASK-038, TASK-039, TASK-041, TASK-042, TASK-040 | J | M |
| TASK-044 | [Preserve directional ordered route patterns for assignment](#task-044) | feature | data | P3 | R2 | backlog | unassigned | GRAPH-EXPORT | TASK-030, TASK-032 | OPTIONAL | M |
| TASK-045 | [Define a unit-consistent capacity model and solver port](#task-045) | feature | backend | P3 | R2 | backlog | unassigned | SCENARIO | TASK-015, TASK-025 | OPTIONAL | M |
| TASK-046 | [Prototype demand-conserving assignment and graph overlays](#task-046) | feature | backend,ml | P3 | R2 | backlog | unassigned | SCENARIO | TASK-016, TASK-044, TASK-045 | OPTIONAL | L |
| TASK-047 | [Persist reproducible scenario runs without overwriting forecasts](#task-047) | feature | backend | P3 | R2 | backlog | unassigned | SCENARIO | TASK-027, TASK-046 | OPTIONAL | M |
| TASK-048 | [Show optional scenario deltas and reproducible comparisons](#task-048) | feature | frontend | P3 | R2 | backlog | unassigned | UI-SCENARIO | TASK-006, TASK-034, TASK-047 | OPTIONAL | M |
| TASK-049 | [Inspect organizer data and confirm the measurable target](#task-049) | research | data,ml | P1 | R2 | blocked | unassigned | DATA | TASK-039 | DATA | M |
| TASK-050 | [Implement and certify real adapters and map crosswalks](#task-050) | feature | data,ml | P1 | R2 | blocked | unassigned | DATA-MAPPING | TASK-049, TASK-018, TASK-032 | DATA | L |
| TASK-051 | [Evaluate and promote models on untouched real temporal slices](#task-051) | research | ml | P1 | R2 | blocked | unassigned | ML-MODEL | TASK-021, TASK-022, TASK-024, TASK-050 | DATA | L |
| TASK-052 | [Establish whether occupancy and OD are identifiable](#task-052) | research | data,ml | P2 | R2 | blocked | unassigned | CONTRACT | TASK-050 | DATA | M |
| TASK-053 | [Gate spatial or graph-model experiments on measured baseline failures](#task-053) | research | ml | P3 | R2 | backlog | unassigned | ML-MODEL | TASK-051, TASK-052 | OPTIONAL | L |
| TASK-054 | [Assess multimodal expansion only after tram acceptance](#task-054) | research | data,ml | P3 | R2 | backlog | unassigned | CONTRACT | TASK-044, TASK-052 | OPTIONAL | M |
| TASK-055 | [Bound shared Overpass requests and failure resource usage](#task-055) | maintenance | backend,infra | P2 | R2 | backlog | unassigned | OBSERVABILITY | TASK-003 | B | M |
| TASK-056 | [Export a self-describing dispatcher forecast report](#task-056) | feature | frontend | P2 | R1 | done | for-vova-huesos | UI-CHART | TASK-035, TASK-036 | I | S |
| TASK-057 | [Explain model behavior and compare baseline errors](#task-057) | feature | ml,frontend | P2 | R2 | backlog | unassigned | ML-EVAL | TASK-023, TASK-022 | G | M |
| TASK-058 | [Run an evaluation-gated offline forecasting pipeline](#task-058) | feature | ml,backend | P1 | R2 | backlog | unassigned | BATCH-PUBLISH | TASK-019, TASK-020, TASK-021, TASK-022, TASK-024, TASK-029 | H | M |
| TASK-059 | [Profile supplied organizer data and map the ML integration gap](../analysis/2026-09-25-organizer-data/README.md) | research | data,ml,docs | P1 | R1 | done | real-data-eda lead | DATA-REVIEW | none | DATA | S |
| TASK-060 | [Train and compare real route-level forecast candidates](../exec-plans/completed/route-ml-experiments.md) | feature | ml,docs | P1 | R2 | done | route-ml-experiments lead | ML-EXPERIMENT | TASK-059 | DATA | M |
| TASK-061 | [Data/target/model passport and ensemble challenger](../analysis/2026-09-25-model-passport/README.md) | research | ml,docs | P1 | R1 | done | route-ml-experiments lead | ML-EXPERIMENT | TASK-060 | DATA | M |

## TASK-001

- **Outcome:** An agent can find one tracker from the root instructions, classify
  work, identify ownership and dependencies, and resume from recorded evidence.
- **Context / hypothesis:** The repository has a task template, an empty debt
  register, and ExecPlan directories, but no general task index. A Markdown index
  linked from the root documents closes this gap without changing runtime behavior.
- **Scope / ownership:** Lead edits this file, `AGENTS.md`, and `README.md` only.
  A read-only subagent independently confirmed the missing tracker and reviewed
  classification. No runtime, API, dependency, or data contracts change.
- **Acceptance:** English classification and lifecycle; valid local links; explicit
  ownership, dependencies, and evidence requirements; discoverability from both
  root documents; existing permission and verification rules preserved.
- **Working location:** Primary checkout, branch `main`, base
  `a19d955029765d219ed81156993ac28f539ec079`. This three-file documentation task
  requires neither a dedicated worktree nor an ExecPlan; only the lead writes.
- **Verification:** Check local links and classification, run `git diff --check`,
  review the diff, then run `make check` under the repository's supported runtimes.
- **Verification result (2026-09-23):** Local link validation and
  `git diff --check` passed. Independent read-only review found no blocking
  conflicts. `make check` passed (exit 0) with Node 24.19.0 after synchronizing
  existing locked frontend dependencies using npm 11.19.0. Backend: 61 tests;
  ML: 3 tests; frontend tests, build, OpenAPI drift, and Compose checks passed.
  Earlier Node 18 / stale dependency failures were environment issues; manifests
  and lock files remain unchanged.
- **Result / integration:** Documentation is present in the primary checkout;
  a local checkpoint records this completed setup before the expanded backlog task.
- **Next action:** Populate a separately tracked pre-hackathon backlog from the
  concept and verified code gaps, as requested by the user.

## TASK-002

- **Outcome:** Fill the tracker with evidence-backed pre-data preparation, dependencies,
  parallel ownership and external gates aligned to the corrected official brief.
- **Scope:** Documentation only: authoritative task, root/subtree entry links,
  concept/architecture/design scope notes, analysis, tracker and execution plan.
- **Evidence:** Three read-only audits of backend/data, ML and frontend; lead inspected
  consumers and ran the baseline gate. Superseded delay/NDTP recommendations discarded.
- **Acceptance:** Every task has classification, code evidence, outcome, tests,
  dependencies and data boundary; task graph acyclic; official requirements traceable;
  optional OD/scenarios cannot block the core pipeline; local references valid.
- **Location:** `agent/pre-hackathon-backlog` at
  `/home/blackfire/Hackatons/MosTransport2026Hack-worktrees/pre-hackathon-backlog`,
  base `790f006898ab954dd06316d8574b843341228dc7`.
- **Verification (2026-09-23):** 170 local links/anchors validated; 58 unique cards
  and rows; acyclic dependencies and correct ready states; required tasks do not
  depend on optional extensions. Three independent read-only reviews completed.
  Removed boosting as a hard prerequisite for real baseline evaluation.
  `git diff --check` and lead-run `make check` passed (exit 0): 61 backend, 3 ML,
  23 frontend tests, static checks, build, OpenAPI drift and Compose config.
- **Result / integration:** Verified documentation is integrated by local fast-forward
  into `main`; no push. Worktree retained with its unpushed branch for review.
- **Next action:** Claim an authorized ready task; start with TASK-003/004/008/011
  in separate ownership areas. Product tasks remain unimplemented.
- **Execution record:** [Completed plan](../exec-plans/completed/pre-hackathon-backlog.md).

## TASK-003

**Freeze acceptance assumptions and organizer questions** — RQ-01–05.

- **Owner / location:** Codex lead; primary checkout
  `/home/blackfire/Hackatons/MosTransport2026Hack`, branch `main`, base
  `5eccb89b61c24f414d37972be5aabb07b881de10`. Three documentation files only:
  this tracker, `docs/product/TASK.md`, and
  [acceptance register](../product/ACCEPTANCE.md). No runtime/data/API contract
  changes; no large-task criterion applies. Independent reviewer is read-only;
  existing sibling worktrees are preserved.
- **Hypothesis / smallest disproof:** Every RQ has a concrete synthetic case and
  separate real-data gate without turning unresolved questions into requirements.
  Check requirement coverage, local links, source consistency and independent
  review, then `git diff --check` and `make check`; runtime behavior stays unchanged.
- **Verification (2026-09-23):** Python local-reference/coverage check passed:
  76 file links across the three documents, five requirement rows with separate
  real-data gates, eight question entries. `git diff --check` passed. Independent
  read-only source/acceptance review approved with no blockers. Lead-run
  `PATH=/home/blackfire/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH make check`
  passed (exit 0): 61 backend, 3 ML, 23 frontend tests; architecture, lint/types,
  golden evaluation, frontend build, OpenAPI drift and Compose config passed.
- **Result / integration:** Three documentation files applied locally on `main`,
  uncommitted for review. No runtime or dependencies changed; no environment was
  created to clean up. Existing worktrees remain untouched. This verifies the
  register, not the future synthetic cases or real-data quality.
- **Next action:** Scope TASK-015's synthetic target/entity/calendar/manifest
  contract using this register in a dedicated worktree; organizer questions stay
  unresolved until attributed answers arrive. TASK-015 and TASK-055 remain backlog
  pending their own contract/authority review despite TASK-003 being complete.
- **Evidence / scope:** [docs/product/TASK.md](../../docs/product/TASK.md). Record target/unit choices, provisional bucket cadence, scoring/format unknowns, permitted pre-event reuse, and real-time meaning; distinguish known requirements from assumptions.
- **Acceptance:** Every RQ has a measurable synthetic acceptance case and an explicit real-data acceptance gate; unanswered questions remain unresolved rather than guessed.
- **Focused verification:** Documentation link/requirement review; git diff --check.
- **Pre-data boundary / risk:** Can finish the question/assumption register now; organizer answers remain external gates for certification, not blockers to reversible scaffolding.

## TASK-004

**Reject invalid evaluation inputs and gate every horizon** — RQ-02.

- **Owner / location:** Codex lead; isolated worktree
  `/home/blackfire/Hackatons/MosTransport2026Hack-worktrees/ml-evaluation-finish`,
  branch `agent/ml-evaluation-finish`, base
  `5eccb89b61c24f414d37972be5aabb07b881de10`. Integrated commits `0621821` and
  `d548bb8`; primary checkout contains the reviewed diff. Files owned:
  `ml/src/tramflow_ml/evaluation.py`, `ml/evals/README.md`,
  `ml/tests/test_evaluation.py`, `ml/tests/test_evaluation_cli.py`.
- **Hypothesis / smallest disproof:** Nonfinite input, invalid thresholds,
  duplicate IDs, unknown/missing horizons and zero-demand slices fail explicitly;
  each required horizon gates baseline WAPE and interval coverage independently.
  Existing report schema and valid golden metrics remain unchanged. Focused
  evaluator and CLI tests are the falsifying check.
- **Verification (2026-09-23):** Focused suite passed 47 tests, then the full
  `make check` passed (exit 0): architecture check, backend 61 tests, ML 48
  tests, Ruff, mypy, golden evaluation, frontend lint/types, 23 frontend tests,
  production build, OpenAPI contract check and Compose config. Independent
  read-only review found no blockers. Invalid CLI inputs return nonzero diagnostics
  without writing a report; the coverage regression returns a failing report even
  when overall coverage is 0.9.
- **Result / integration:** TASK-004 implementation is present in the primary
  checkout alongside the earlier documentation changes. No dependency, API,
  database or model artifact was added. The isolated worktree remains retained
  with clean status for review; its branch is preserved.
- **Next action:** Continue with TASK-005 or another highest-priority ready task;
  real-data model quality remains gated by TASK-049/051.
- **Evidence / scope:** [ml/src/tramflow_ml/evaluation.py](../../ml/src/tramflow_ml/evaluation.py). Fix demonstrated acceptance of NaN and coverage checks that only gate the overall score; document zero-demand, duplicate-ID and required-horizon policies.
- **Acceptance:** NaN/Inf and invalid thresholds fail; a year slice with 0% coverage cannot pass behind good day coverage; all-zero demand is reported explicitly; valid golden fixtures still pass.
- **Focused verification:** uv run --package tramflow-ml pytest ml/tests/test_evaluation.py; make ml-eval.
- **Pre-data boundary / risk:** Synthetic/committed inputs suffice; real-data quality is not claimed.

## TASK-005

**Make demonstration and model capability labels truthful** — RQ-04–05.

- **Evidence / scope:** [frontend/src/App.tsx](../../frontend/src/App.tsx). Label seed forecasts and prototype scenarios consistently; replace unconditional model availability and unsupported graph-learning claims with actual state.
- **Acceptance:** Loading/error/demo states never claim a validated or live model; generated-at time is identified; existing route/horizon navigation remains usable.
- **Focused verification:** Frontend component state fixtures and existing dashboard E2E; make frontend-check; make e2e.
- **Pre-data boundary / risk:** Synthetic/committed inputs suffice; real-data quality is not claimed.

- **Integration evidence:** Merged and verified with the other completed blocks; see [combined verification](../exec-plans/completed/integrate-prep-blocks.md).

## TASK-006

**Bind scenario output to the submitted parameter snapshot** — EXT: existing what-if demo.

- **Evidence / scope:** [frontend/src/features/forecast/components/scenario-panel.tsx](../../frontend/src/features/forecast/components/scenario-panel.tsx). Invalidate or explicitly mark previous output after slider edits; prevent reset and pending requests from restoring obsolete results.
- **Acceptance:** Edit-after-submit, reset-while-pending, failure/retry and route/horizon change fixtures never display results as belonging to new inputs.
- **Focused verification:** Focused scenario component tests; scenario Playwright flow; make frontend-check; make e2e.
- **Pre-data boundary / risk:** Fix existing behavior if capacity permits; optional what-if must not delay mandatory forecasting.

- **Integration evidence:** Merged and verified with the other completed blocks; see [combined verification](../exec-plans/completed/integrate-prep-blocks.md).

## TASK-007

**Preserve stale forecasts and gate queries on valid selection** — RQ-03–04.

- **Evidence / scope:** [frontend/src/features/forecast/hooks/use-forecast.ts](../../frontend/src/features/forecast/hooks/use-forecast.ts). Keep previous successful data on refresh failure with explicit stale state; avoid requests for default route 1 before routes load; handle empty route lists.
- **Acceptance:** First-load error differs from stale refresh; empty routes issue no forecast request; late responses from old selections never relabel current data.
- **Focused verification:** Fake-clock/query tests and retry/filter E2E; make frontend-check; make e2e.
- **Pre-data boundary / risk:** Synthetic/committed inputs suffice; real-data quality is not claimed.

- **Integration evidence:** Merged and verified with the other completed blocks; see [combined verification](../exec-plans/completed/integrate-prep-blocks.md).

## TASK-008

**Keep the local network usable without a remote basemap** — RQ-04.

- **Evidence / scope:** [frontend/src/features/tram-network/components/tram-map.tsx](../../frontend/src/features/tram-network/components/tram-map.tsx). Reproduce blocked style/tiles and WebGL failure; implement a verified local blank-style fallback or a truthful unavailable state with recovery.
- **Acceptance:** Blocked external style cannot leave a message falsely claiming a rendered graph; committed graph can be inspected through map or accessible alternative; retries and reduced motion work.
- **Focused verification:** Deterministic blocked-style Playwright test; make frontend-check; make e2e.
- **Pre-data boundary / risk:** Research the official MapLibre style lifecycle before changing it; no live Overpass dependency in tests.

- **Integration evidence:** Merged and verified with the other completed blocks; see [combined verification](../exec-plans/completed/integrate-prep-blocks.md).

## TASK-009

**Expose partial network query failures and scoped retries** — RQ-04.

- **Evidence / scope:** [frontend/src/features/tram-network/components/tram-network-view.tsx](../../frontend/src/features/tram-network/components/tram-network-view.tsx). Handle selected-route geometry, stop search/detail and Overpass status failures without indefinite checking or stale overlays masquerading as current.
- **Acceptance:** Each query has loading/empty/error/retry behavior; remote Overpass outage does not prevent use of committed local topology.
- **Focused verification:** Network component state tests plus browser fault injection; make frontend-check; make e2e.
- **Pre-data boundary / risk:** Synthetic/committed inputs suffice; real-data quality is not claimed.

- **Integration evidence:** Merged and verified with the other completed blocks; see [combined verification](../exec-plans/completed/integrate-prep-blocks.md).

## TASK-010

**Build internally consistent browser forecast fixtures** — RQ-02–04.

- **Evidence / scope:** [frontend/e2e/dashboard.e2e.ts](../../frontend/e2e/dashboard.e2e.ts). Replace contradictory peaks and month/year dates in fixtures with one deterministic factory using current contracts.
- **Acceptance:** Peak equals maximum point value; all buckets ordered and aligned; intervals enclose predictions; route/stop/window fixtures can be added after contract freeze.
- **Focused verification:** Fixture invariant unit tests and existing three Playwright flows; make frontend-check; make e2e.
- **Pre-data boundary / risk:** Synthetic/committed inputs suffice; real-data quality is not claimed.

- **Integration evidence:** Merged and verified with the other completed blocks; see [combined verification](../exec-plans/completed/integrate-prep-blocks.md).

## TASK-011

**Reject incomplete Overpass extracts before writing outputs** — RQ-04.

- **Implementation / handoff:** Terminal 5, Codex lead; isolated worktree
  `/home/blackfire/Hackatons/MosTransport2026Hack-worktrees/prep-graph-integrity`,
  branch `agent/prep-graph-integrity`, base `b026e532acc91ce6bb6f13642401c899793a852d`.
  Owns extractor, graph domain/repository, related tests/docs only. Parallel agent
  commit `7be660c` integrated as `6eebe78`; lead added missing-reference validation
  and versioned publication integration. Mocked failures preserve old output bytes.
  Final extractor suite: 31 tests passed, including standalone no-packages rollback
  and byte-preserved legacy/versioned outputs. Final integrated gate and handoff
  are recorded in the [ExecPlan](../exec-plans/completed/prep-graph-integrity.md).
- **Evidence / scope:** [scripts/fetch_tram_graph.py](../../scripts/fetch_tram_graph.py). The API client handles HTTP-200 remark errors; make the standalone extractor reject partial/error payloads before replacing any output.
- **Acceptance:** HTTP-200 JSON with remark exits nonzero and preserves existing files byte-for-byte; valid fixture still exports; no live shared-server stress.
- **Focused verification:** New extractor tests under backend/tests with mocked transport; make backend-check.
- **Pre-data boundary / risk:** Synthetic/committed inputs suffice; real-data quality is not claimed.

## TASK-012

**Validate graph structures and numerical invariants strictly** — RQ-04.

- **Implementation / handoff:** Same Terminal 5 branch/base/worktree as TASK-011.
  Agent commit `7efa8fe` integrated as `e1c60af`; shared stdlib parser plus domain
  guards reject malformed shapes, duplicates, nonfinite/range/type errors and
  unknown endpoints as `TramGraphDataError`. Existing geometry fallback remains.
  Agent focused 91 tests and backend gate 149 tests passed. Lead added regression
  guards for very long numeric refs and malformed direct-domain geometry. Final
  integrated `make check` passed: 220 backend, 48 ML and 23 frontend tests;
  architecture, Ruff, mypy, golden evaluation, build, OpenAPI and Compose passed.
  No public API changes. Shared ExecPlan records review and integration status.
- **Evidence / scope:** [backend/app/infrastructure/repositories/tram_graph.py](../../backend/app/infrastructure/repositories/tram_graph.py). Reject duplicate IDs, malformed roots, invalid coordinates, nonfinite/negative lengths and unknown endpoints through consistent graph-data errors.
- **Acceptance:** Committed graph loads; corrupt fixture matrix fails deterministically; readiness reports unavailable instead of accidental 500 or silent node collapse; valid path semantics preserved.
- **Focused verification:** Graph repository/domain/readiness tests; make backend-check.
- **Pre-data boundary / risk:** Synthetic/committed inputs suffice; real-data quality is not claimed.

## TASK-013

- **Result (2026-09-23):** Safe exception metadata and route-template logging; 19 focused tests, full `make check` and Docker smoke pass. Branch `agent/safe-error-diagnostics`, base `6a0f1a7`; [verification, ownership and scope](../exec-plans/completed/safe-error-diagnostics.md).

**Keep exception diagnostics free of raw secrets and identifiers** — RQ-01.

- **Evidence / scope:** [backend/app/infrastructure/observability.py](../../backend/app/infrastructure/observability.py). Define allowed diagnostic fields and test nested exceptions; current traceback formatter can expose driver text.
- **Acceptance:** Injected synthetic secret/passenger markers never reach logs or responses; request ID, safe error category and useful context remain available.
- **Focused verification:** Captured-log and error-response tests; make backend-check.
- **Pre-data boundary / risk:** Do not inspect actual credentials or passenger data to construct tests.

## TASK-014

**Cover current forecast HTTP and numerical boundary behavior** — RQ-02–03.

- **Evidence / scope:** [backend/tests/test_forecast_service.py](../../backend/tests/test_forecast_service.py). Add focused endpoint/validation tests using dependency overrides before contract expansion; existing service tests cover only two happy paths.
- **Acceptance:** All three horizons, missing route/snapshot, invalid input, zero-change scenario and baseline immutability are covered; valid response shape is unchanged.
- **Focused verification:** New forecast API test module plus test_forecast_service.py; make backend-check.
- **Pre-data boundary / risk:** Synthetic/committed inputs suffice; real-data quality is not claimed.

- **Integration evidence:** Merged and verified with the other completed blocks; see [combined verification](../exec-plans/completed/integrate-prep-blocks.md).

## TASK-015

**Define canonical targets, entities, calendar and dataset manifests** — RQ-01–03, RQ-05.

- **Corrected and completed (2026-09-23):** Reopened after audit, then added calendar/availability/entity/missing-zero rules and publication consistency checks. Final `make check` includes 119 shared-contract tests; independent review and Docker smoke pass. Branch `agent/complete-data-contracts`, base `cece609`; [evidence](../exec-plans/completed/complete-data-contracts.md).
- **Evidence / scope:** [docs/product/CONCEPT.md](../../docs/product/CONCEPT.md). Specify boardings versus occupancy, route/direction/stop identifiers, event/availability time, service day, half-open windows, units, missing versus zero, and versioned source/feature manifests.
- **Acceptance:** Schema fixtures cover duplicate stop names, UTC/Moscow midnight, leap year and variable months; aggregation rules prohibit summing incompatible quantities; unsupported occupancy/OD is explicit.
- **Focused verification:** New schema and time-boundary tests in ml/tests and backend/tests; contract review; make ml-check backend-check.
- **Pre-data boundary / risk:** Internal normalized contract only: organizer column names, protocol and final target definition remain unknown. Provisional choices are configurable and versioned.

## TASK-016

- **Execution:** `agent/synthetic-transport-data`, base `b36ece3`; [scope, ownership, measured budget and review record](../exec-plans/completed/synthetic-transport-data.md).
- **Verification (2026-09-24):** million-event run 13.95 s wall / 42 MB peak RSS / 543 MB output against 120 s / 256 MiB / 2 GiB ceilings; `source_hash` reproduced independently twice; independent review findings fixed with output bytes unchanged. `make check`: exit 0 — backend 292 passed / 10 SQL skipped, ML 72 passed, frontend 47 passed, reference contracts 119 passed; architecture, lint/types, golden evaluation, production build, API drift and Compose checks passed.

**Generate reproducible multiyear synthetic transport datasets** — RQ-01–03.

- **Evidence / scope:** [ml/evals/golden_cases.json](../../ml/evals/golden_cases.json). Add configurable raw validation and telemetry fixture generation with seeded peaks, directions, gaps, late/duplicate rows and known totals; include tiny and million-row modes.
- **Acceptance:** Same config/seed yields same content hash; synthetic provenance travels with outputs; known counts and month/year boundaries are independently checked.
- **Focused verification:** Generator schema/count/determinism tests in ml/tests; make ml-check.
- **Pre-data boundary / risk:** Synthetic patterns test mechanics, not Moscow demand accuracy; generate large artifacts outside git.

## TASK-017

- **Execution:** `agent/historical-ingestion`, base `4478d43`, merged into `main` as `80f3372`; [scope, measured budget and review record](../exec-plans/completed/historical-ingestion.md).
- **Verification (2026-09-25):** million-event run 24.2 s / 57 MB peak RSS with an identical 100 000-event peak, so memory is bounded by `--chunk-size`, not row count; a SIGKILL'd run resumed to the same four SHA-256 digests and a byte-identical manifest; `input_rows == valid + duplicates + quarantined` per stream. Independent review ACCEPT (no CRITICAL/HIGH); its six findings are fixed in `fc59a76` with valid-input outputs byte-identical (`validations.jsonl` `5551a578…` reproduced after the fixes). `make check`: exit 0 — backend 292 passed / 10 SQL skipped, ML 96 passed, frontend 47 passed, reference contracts 119 passed.

**Implement bounded historical ingestion with restart and quarantine** — RQ-01.

- **Evidence / scope:** [ml/src/tramflow_ml/cli.py](../../ml/src/tramflow_ml/cli.py). Add offline chunked readers and configurable fixture-column adapters; preserve immutable input hash, versioned normalization, checkpoints, deduplication and quarantine counts.
- **Acceptance:** Valid + quarantined + policy-accounted duplicates reconcile to input; interrupted/resumed and uninterrupted runs agree; memory is bounded by configured chunk/state, not total rows.
- **Focused verification:** Ingestion/restart tests, million-row synthetic run with peak-memory/throughput record; make ml-check.
- **Pre-data boundary / risk:** Implement supported fixture CSV/JSONL first; actual organizer adapters wait for samples. No distributed stack commitment before measurement.

## TASK-018

- **Execution:** `agent/identity-alignment`, base `4478d43`, merged into `main` as `3703f29`; [scope, matching rules and review record](../exec-plans/completed/identity-alignment.md).
- **Verification (2026-09-25):** hand-calculated crosswalk fixtures cover duplicate stop names, opposite directions, repeated stops in one pattern, stale GPS, clock offsets and vehicle reassignment; every unresolved row stays `Unmatched`/`Ambiguous`/`Stale` and is counted in the quality report instead of joining. Independent review ACCEPT with findings, fixed in `628636d` — naive DST-gap and fall-back-overlap wall times are now refused instead of resolved with `fold=0`. `make check`: exit 0 — backend 292 passed / 10 SQL skipped, ML 127 passed, frontend 47 passed, reference contracts 119 passed.

**Align validations and telemetry with explicit identity rules** — RQ-01, RQ-03–04.

- **Evidence / scope:** [backend/app/infrastructure/db/models.py](../../backend/app/infrastructure/db/models.py). Implement versioned source-to-canonical crosswalks and configurable event-time alignment; preserve unmatched/ambiguous results and source quality.
- **Acceptance:** Duplicate names, opposite directions, repeated stops, stale GPS, clock offsets and vehicle route changes never silently join to the wrong entity; unmatched rates reported.
- **Focused verification:** Hand-calculated join fixtures and availability/time-boundary tests; make ml-check.
- **Pre-data boundary / risk:** Real source mapping and matching tolerances cannot be certified before organizer samples; no invented NDTP dependency.

## TASK-019

- **Execution:** `agent/horizon-features`, base `3e4ad59`, merged into `main` as `fd621d0`; [scope, cutoff policies and review record](../exec-plans/completed/horizon-features.md).
- **Verification (2026-09-25):** fixture reconciliation holds through the real `synthetic → ingestion → features` path — 64 valid rows, 64 hourly cells summing to 64, equal cell for cell to the generator's own `cell_totals`, conserved at daily and monthly granularity; the oracle never passes through the feature code. Independent review ACCEPT WITH FINDINGS (900 randomized post-cutoff perturbations with working negative controls moved no feature byte) and independent acceptance validation ACCEPT (all four criteria met by reproduction, late-arriving rows correct to the microsecond, 3456 lag cells recomputed with 0 mismatches). Both reviewers' findings are fixed in `3392f99` and `80b93c4`: a covered-but-unpublished date now yields `missing` instead of a confident zero, monthly features carry a covered-units ratio, capacity is availability-stamped and resolved at the cutoff, and three overstated calendar claims are retracted. The lead reproduced all three recorded digests (`7e412bb0…`, `b3ad914c…`, `408d4580…`) and the publication-lag case independently. `make check`: exit 0 — backend 292 passed / 10 SQL skipped, ML 265 passed, frontend 47 passed, reference contracts 119 passed.

**Build leakage-safe aggregates and horizon-specific features** — RQ-01–03.

- **Evidence / scope:** [docs/architecture/README.md](../../docs/architecture/README.md). Create route/stop/direction buckets, calendar features, lags/rolling statistics and explicit availability cutoffs for day/hour, month/day and year/month policies.
- **Acceptance:** Fixture sums match independently computed totals; future data perturbation cannot change past features; missing differs from zero; year/month boundaries use calendar periods rather than 30-day steps.
- **Focused verification:** Aggregation oracle, leakage and timezone tests in ml/tests; make ml-check.
- **Pre-data boundary / risk:** Bucket policy is the team proposal; actual historical weather/events unavailable at cutoff cannot become features.

## TASK-020

- **Execution:** `agent/rolling-backtest`, base `c34e7d9`, worktree `MosTransport2026Hack-worktrees/rolling-backtest`; [plan](../exec-plans/active/rolling-backtest.md).

**Implement history-aware rolling-origin backtesting** — RQ-02.

- **Evidence / scope:** [ml/src/tramflow_ml/evaluation.py](../../ml/src/tramflow_ml/evaluation.py). Add chronological train/validation/test folds, full-horizon labels, configurable gaps and experiment manifests; candidate and baseline share identical folds.
- **Acceptance:** No overlap/leakage; year evaluation requires complete future year and minimum eligible origins; insufficient history returns an explicit non-passing state; fold/config/version hashes reproducible.
- **Focused verification:** Fold index and future-availability tests; make ml-check ml-eval.
- **Pre-data boundary / risk:** Synthetic history exercises the runner; number of viable real yearly folds remains unknown.

## TASK-021

**Implement executable seasonal and simple-regression baselines** — RQ-02.

- **Evidence / scope:** [ml/evals/golden_cases.json](../../ml/evals/golden_cases.json). Generate seasonal-naive, historical-profile and simple regularized-regression forecasts with installed tooling for each horizon; define adapter boundary for an organizer incumbent.
- **Acceptance:** Expected seasonal fixtures pass; train only before origin; insufficient history/cold start explicit; same folds and slices compare all baselines; each horizon has a real prediction method.
- **Focused verification:** Baseline known-value and reproducible train/predict tests; make ml-check ml-eval.
- **Pre-data boundary / risk:** Current hand-authored baseline arrays are not an executable model or the organizer incumbent; real incumbent comparison is deferred.

## TASK-022

**Report operational slices and interval quality without hiding failures** — RQ-02, RQ-05.

- **Evidence / scope:** [ml/src/tramflow_ml/evaluation.py](../../ml/src/tramflow_ml/evaluation.py). Add route/stop/direction/horizon and event slices, peak error, support counts, coverage and interval width/score; define zero-demand and small-sample handling.
- **Acceptance:** Bad required slice cannot disappear in overall mean; giant intervals are penalized; each metric includes unit/sample/fold count; overload metrics only appear with compatible ground truth.
- **Focused verification:** Hand-computed metrics fixtures and gate-failure tests; make ml-check ml-eval.
- **Pre-data boundary / risk:** Thresholds are provisional until agreed; synthetic success is not evidence of model superiority.

## TASK-023

**Add a reproducible lag/calendar boosting candidate** — RQ-02.

- **Evidence / scope:** [ml/pyproject.toml](../../ml/pyproject.toml). Use already installed scikit-learn for a first nonlinear model and train/predict CLI; compare to every executable baseline on the same folds.
- **Acceptance:** Synthetic smoke training is deterministic; unknown/cold-start policy explicit; model may lose and is not automatically promoted; online worker never imports training code.
- **Focused verification:** CLI reproducibility, fold-parity and model-contract tests; make ml-check ml-eval.
- **Pre-data boundary / risk:** No CatBoost/PyTorch/GNN installation by default; real gains require TASK-051.

## TASK-024

**Produce calibrated-interval scaffolding with past-only calibration** — RQ-02, RQ-05.

- **Evidence / scope:** [backend/app/domain/forecast.py](../../backend/app/domain/forecast.py). Add interval estimator with disjoint historical calibration and explicit nominal level/method/sample support for each horizon.
- **Acceptance:** Bounds finite, nonnegative and ordered; future outcomes never used; coverage and width evaluated by horizon/slice; insufficient support produces an explicit unavailable interval state.
- **Focused verification:** Interval ordering, calibration split and leakage tests; make ml-check ml-eval.
- **Pre-data boundary / risk:** Prepare algorithm and metadata now; do not call synthetic intervals calibrated for real Moscow demand.

## TASK-025

**Freeze the versioned offline forecast publication contract** — RQ-02–04.

- **Corrected and completed (2026-09-23):** Reopened after audit, then added calendar/availability/entity/missing-zero rules and publication consistency checks. Final `make check` includes 119 shared-contract tests; independent review and Docker smoke pass. Branch `agent/complete-data-contracts`, base `cece609`; [evidence](../exec-plans/completed/complete-data-contracts.md).
- **Evidence / scope:** [backend/app/ml/protocols.py](../../backend/app/ml/protocols.py). Define shared artifact and validation fixtures: run/origin, entity/target/unit, buckets, interval level, source/feature/model/graph versions, generated-at, data cutoff and synthetic status.
- **Acceptance:** Reject mixed-run, nonfinite, misaligned or inconsistent artifacts; explicit schema compatibility policy; ML producer and backend consumer validate identical fixtures without backend training imports.
- **Focused verification:** Cross-boundary schema tests plus architecture-check; make ml-check backend-check contract-check.
- **Pre-data boundary / risk:** Do not make publication depend on training a new model; a deterministic fake producer suffices.

## TASK-026

**Add isolated PostgreSQL repository integration test support** — RQ-03.

- **Evidence / scope:** [Makefile](../../Makefile). Extend existing disposable-database lifecycle for actual SQL repository fixtures; allocate unique project/ports/volumes and avoid the developer DB.
- **Acceptance:** Fresh DB tests run valid seed reads, rollback and deterministic ordering; setup/cleanup safe on failure; later run/window invariants can reuse the harness.
- **Focused verification:** New PostgreSQL test command, make migration-verify, Compose config and isolated smoke; make check.
- **Pre-data boundary / risk:** One owner of Makefile/CI/runtime scripts; no competing test stack.

- **Integration evidence:** Merged and verified with the other completed blocks; see [combined verification](../exec-plans/completed/integrate-prep-blocks.md).

## TASK-027

- **Integration:** Locally merged in `main` at `202caed`; independently reviewed; combined `make check` passed in `agent/vova-033-filters`. Evidence: [handoff](HANDOFF.md#vova-foundation-2026-09-25). No remote publication.

- **Working evidence:** [active ExecPlan](../exec-plans/completed/vova-027-runs.md); branch `agent/vova-027-runs`, base `d8313a4b79273306e41001adaf1f4673649cc304`.

- **Allocation:** parallel block [`for-vova-huesos`](FOR_VOVA_HUESOS.md) — owner, order and file boundaries are defined there.

**Persist coherent forecast runs and enforce value invariants** — RQ-02–03.

- **Evidence / scope:** [backend/app/infrastructure/db/models.py](../../backend/app/infrastructure/db/models.py). Add new Alembic migration for immutable run identity/publication state and nonambiguous uniqueness; enforce valid counts/intervals/capacity under the agreed target contract.
- **Acceptance:** Two runs coexist without mixed metadata; duplicate aggregate rows with null stop rejected; zero/unknown capacity handled explicitly before division; invalid partial runs remain invisible.
- **Focused verification:** PostgreSQL invariant/transaction tests; clean migration upgrade and alembic check; make backend-check migration-verify.
- **Pre-data boundary / risk:** Never rewrite initial migration; document recovery and backward-compatible seed handling.

## TASK-028

- **Verified result:** [execution evidence](../exec-plans/completed/vova-028-window.md), owned branch `agent/vova-028-window`; local integration only, no remote push.

- **Allocation:** parallel block [`for-vova-huesos`](FOR_VOVA_HUESOS.md) — owner, order and file boundaries are defined there.

**Serve bounded route, stop and time-window forecast aggregates** — RQ-03.

- **Evidence / scope:** [backend/app/infrastructure/repositories/forecast.py](../../backend/app/infrastructure/repositories/forecast.py). Extend API/application/repository with explicit aggregation key, optional stop, bounded half-open window and one published run; preserve documented old requests via bounded defaults.
- **Acceptance:** Multi-route/stop/bucket/run fixture returns exact selected totals without double counts or repeated ambiguous stops; invalid/oversized windows fail; no unbounded history read; intervals aggregate by documented method.
- **Focused verification:** PostgreSQL oracle and HTTP boundary tests; EXPLAIN (ANALYZE, BUFFERS); make backend-check contract-check migration-verify.
- **Pre-data boundary / risk:** Uncertainty bounds cannot be blindly summed under an independence assumption; choose a declared valid aggregation method or report unavailable.

## TASK-029

**Publish validated batch artifacts atomically and idempotently** — RQ-02–04.

- **Evidence / scope:** [backend/app/ml/protocols.py](../../backend/app/ml/protocols.py). Implement offline validator/publisher command and atomic active-run switch; retain prior valid run and provenance, with a fake model adapter for tests.
- **Acceptance:** Interrupted/invalid/failed-quality run cannot become visible; repeated same artifact does not duplicate rows; old run remains readable; no training in web process.
- **Focused verification:** Fault-injection/idempotency PostgreSQL integration; publication schema tests; make backend-check ml-check migration-verify.
- **Pre-data boundary / risk:** Synthetic/committed inputs suffice; real-data quality is not claimed.

## TASK-030

**Publish graph artifacts as a validated versioned set** — RQ-04.

- **Implementation / handoff:** Same Terminal 5 branch/base/worktree as TASK-011.
  Lead owns stdlib graph artifact publisher, manifest-aware repository integration,
  failure/rollback/concurrency tests, documentation and final verification.
  [ADR-0004](../decisions/0004-atomic-graph-snapshots.md) records primary-source
  research and the versioned artifact contract; the
  [ExecPlan](../exec-plans/completed/prep-graph-integrity.md) records acceptance and review.
  Independent review identified the first-adoption failure case; the revised
  protocol atomically installs the first complete store and preserves legacy
  availability until that commit point. Final publication suite: 36 tests passed;
  full lead-owned `make check` passed (220 backend, 48 ML, 23 frontend tests).
  Independent reviews approved after failure-path and GraphML direction fixes.
  Result merged with current main in `agent/integrate-graph-block`; combined
  `make check` passed (292 backend, 50 ML, 47 frontend), plus 10 PostgreSQL
  tests and Docker smoke. See the ExecPlan combined integration section.
  Source and integration worktrees retained for review; test resources removed.
- **Evidence / scope:** [scripts/fetch_tram_graph.py](../../scripts/fetch_tram_graph.py). Stage JSON/GeoJSON/CSV/GraphML together, validate checksums/source version, and expose only a complete matching set through a manifest.
- **Acceptance:** Interrupted export or mismatched JSON/GeoJSON cannot replace last good snapshot; committed topology and two components preserved; rollback selects prior complete set.
- **Focused verification:** Injected write-failure and manifest mismatch tests; make backend-check.
- **Pre-data boundary / risk:** Research atomic multi-file publication before implementation; retain file repository under ADR-0003 unless measured need warrants a new ADR.

## TASK-031

- **Integration:** Locally merged in `main` at `202caed`; independently reviewed; combined `make check` passed in `agent/vova-033-filters`. Evidence: [handoff](HANDOFF.md#vova-foundation-2026-09-25). No remote publication.

- **Allocation:** parallel block [`for-vova-huesos`](FOR_VOVA_HUESOS.md) — owner, order and file boundaries are defined there.

**Make missing per-edge geometry explicit** — RQ-04.

- **Evidence / scope:** [backend/app/domain/tram_graph.py](../../backend/app/domain/tram_graph.py). Decide and implement strict rejection or visible quality flags for missing edge geometry; current tested straight-line fallback is silent.
- **Acceptance:** A missing individual edge cannot be presented as real rail geometry; intentional synthetic geometry remains distinguishable; path/error contracts and generated types synchronized.
- **Focused verification:** Existing fallback regression plus quality-state API/UI tests; make backend-check frontend-check contract-check.
- **Pre-data boundary / risk:** This changes a tested behavior: document the decision and compatibility/rollback before editing.

## TASK-032

- **Integration:** Locally merged in `main` at `202caed`; independently reviewed; combined `make check` passed in `agent/vova-033-filters`. Evidence: [handoff](HANDOFF.md#vova-foundation-2026-09-25). No remote publication.

- **Allocation:** parallel block [`for-vova-huesos`](FOR_VOVA_HUESOS.md) — owner, order and file boundaries are defined there.

**Join forecast entities to versioned Moscow map geometry** — RQ-03–04.

- **Evidence / scope:** [docs/decisions/0003-tram-graph-file-repository.md](../../docs/decisions/0003-tram-graph-file-repository.md). Implement explicit canonical-to-OSM crosswalk and map payload fixtures; seed DB IDs and OSM IDs are different namespaces.
- **Acceptance:** Duplicate-name/directional stops do not auto-merge; unmatched/ambiguous geometry counts visible; mapping and graph version recorded; route sets are not mistaken for ordered trips.
- **Focused verification:** Crosswalk fixtures with duplicate names, directions and unmapped nodes; make backend-check ml-check.
- **Pre-data boundary / risk:** Real mapping coverage is certified only in TASK-050; no graph-to-PostgreSQL migration solely for convenience.

## TASK-033

- **Verified result:** [execution evidence](../exec-plans/completed/vova-033-filters.md), owned branch `agent/vova-033-filters`; local integration only, no remote push.

- **Allocation:** parallel block [`for-vova-huesos`](FOR_VOVA_HUESOS.md) — owner, order and file boundaries are defined there.

**Add dispatcher stop and time-window filters** — RQ-03.

- **Evidence / scope:** [frontend/src/api/client.ts](../../frontend/src/api/client.ts). Extend central client/hooks and controls with stop selection and start/end time; keep route/horizon filters visible and accessible.
- **Acceptance:** Every filter is in query identity; route change clears incompatible stop; invalid/empty windows explained; keyboard flow works; delayed old responses never appear as new selection.
- **Focused verification:** Request-shape and rapid-filter race fixtures; route/stop/window Playwright tests; make frontend-check contract-check e2e.
- **Pre-data boundary / risk:** Synthetic/committed inputs suffice; real-data quality is not claimed.

## TASK-034

- **Allocation:** parallel block [`for-vova-huesos`](FOR_VOVA_HUESOS.md) — owner, order and file boundaries are defined there.

**Synchronize forecast map, time selection and chart state** — RQ-03–04.

- **Evidence / scope:** [frontend/src/features/forecast/components/network-map.tsx](../../frontend/src/features/forecast/components/network-map.tsx). Replace the disconnected forecast schematic experience with geographically grounded forecast overlays on the existing Moscow graph; share selected run/bucket/entity with chart/KPI.
- **Acceptance:** Moving time selection updates map/chart/KPI consistently; stop values accessible without hover; units/interval/time legend; unmatched stops explicit; synthetic updates test coherence.
- **Focused verification:** Known-value overlay join tests and three-horizon map/timeline E2E; make frontend-check backend-check contract-check e2e.
- **Pre-data boundary / risk:** Reuse installed MapLibre and existing topology; do not imply observed occupancy if target is boardings.

## TASK-035

- **Allocation:** parallel block [`for-vova-huesos`](FOR_VOVA_HUESOS.md) — owner, order and file boundaries are defined there.

**Expose provenance and trustworthy real-time refresh state** — RQ-04–05.

- **Evidence / scope:** [frontend/src/App.tsx](../../frontend/src/App.tsx). Show run/model/data version, synthetic status, source coverage/cutoff and generation time; define configurable polling/freshness behavior using existing query infrastructure.
- **Acceptance:** Refresh failure retains last good coherent snapshot marked stale; map and chart never mix runs; generation/source observation/UI fetch times distinguished; missing live feed is explicit.
- **Focused verification:** Fake-clock refresh/outage/recovery and out-of-order response E2E; make frontend-check backend-check contract-check e2e.
- **Pre-data boundary / risk:** Real-time cadence/SLA is unspecified. No invented live observations; replay/fixture updates are clearly marked.

## TASK-036

- **Allocation:** parallel block [`for-vova-huesos`](FOR_VOVA_HUESOS.md) — owner, order and file boundaries are defined there.

**Make forecast uncertainty and units inspectable without hover** — RQ-02–05.

- **Evidence / scope:** [frontend/src/features/forecast/components/forecast-chart.tsx](../../frontend/src/features/forecast/components/forecast-chart.tsx). Add accessible table/summary and full Moscow bucket timestamps, target units, bounds and compatible capacity metadata; avoid unsupported confidence wording.
- **Acceptance:** Keyboard users can inspect every plotted value; month/year dates exact; unavailable capacity or interval differs from zero; no false precision or calibrated-quality claim on demo data.
- **Focused verification:** Chart/table known-value tests at calendar boundaries; accessibility browser checks; make frontend-check e2e.
- **Pre-data boundary / risk:** Synthetic/committed inputs suffice; real-data quality is not claimed.

## TASK-037

**Cover network navigation and outages in browser tests** — RQ-04.

- **Evidence / scope:** [frontend/e2e/dashboard.e2e.ts](../../frontend/e2e/dashboard.e2e.ts). Add separate network suite using deterministic fixtures for route/stop selection, directed paths, component separation and partial errors.
- **Acceptance:** Keyboard search, endpoint swap/reset, unreachable path, offline basemap, retries and empty results pass without live Overpass.
- **Focused verification:** New network Playwright suite; make frontend-check e2e.
- **Pre-data boundary / risk:** Synthetic/committed inputs suffice; real-data quality is not claimed.

- **Integration evidence:** Merged and verified with the other completed blocks; see [combined verification](../exec-plans/completed/integrate-prep-blocks.md).

## TASK-038

- **Allocation:** parallel block [`for-vova-huesos`](FOR_VOVA_HUESOS.md) — owner, order and file boundaries are defined there.

**Verify dispatcher accessibility and responsive operation** — RQ-03–05.

- **Evidence / scope:** [DESIGN.md](../../DESIGN.md). Apply design requirements to primary forecast/filter/map and error/stale flows; coordinate shared CSS fixes through one owner.
- **Acceptance:** 390/768/1440px, 200% zoom, reduced motion and keyboard complete flow pass; no page overflow; non-colour legends; axe on success/error/map/filter states.
- **Focused verification:** Responsive/keyboard/axe Playwright suite with screenshots; make frontend-check e2e.
- **Pre-data boundary / risk:** Synthetic/committed inputs suffice; real-data quality is not claimed.

## TASK-039

- **Execution:** `agent/intake-profiling`, base `c34e7d9`, worktree `MosTransport2026Hack-worktrees/intake-profiling`; [plan](../exec-plans/active/intake-profiling.md).

**Build a first-data profiling and adaptation toolkit** — RQ-01–03.

- **Evidence / scope:** [ml/src/tramflow_ml/cli.py](../../ml/src/tramflow_ml/cli.py). Add read-only intake report and adapter checklist for alternate synthetic source schemas: date span, missingness, duplicates, units, join coverage and eligible folds.
- **Acceptance:** Unknown schemas fail actionably; report says which horizons/targets are supportable; no raw passenger identifiers in output; counts reconcile across two fixture schemas.
- **Focused verification:** Intake CLI golden-report tests; make ml-check.
- **Pre-data boundary / risk:** Actual field mapping remains TASK-049/050; prebuild tooling without guessing organizer columns.

## TASK-040

**Observe batch quality, publication and forecast freshness** — RQ-01, RQ-04.

- **Evidence / scope:** [backend/app/api/middleware/observability.py](../../backend/app/api/middleware/observability.py). Extend existing structured logs/health with safe run IDs, rejected-row counts, publish failures and data freshness; document liveness versus data availability.
- **Acceptance:** Failed batch leaves last published run intact with visible age; trace a synthetic run end to end; errors contain no payload/identifiers; missing source does not masquerade as fresh data.
- **Focused verification:** Captured-log/fake-clock/publication failure tests; make backend-check ml-check.
- **Pre-data boundary / risk:** Reuse existing logs first; no unsolicited monitoring platform.

## TASK-041

**Measure million-row ingestion and bounded query/UI budgets** — RQ-01, RQ-03–04.

- **Evidence / scope:** [Makefile](../../Makefile). Run parameterized synthetic scale experiments for ingestion memory/throughput, SQL window queries, response size and map responsiveness; agree provisional budgets before optimizing.
- **Acceptance:** Record hardware/config/row counts, p50/p95 and peak memory; EXPLAIN buffers/time for selected windows; cardinality stays bounded; flag exceeded budgets with reproducible commands.
- **Focused verification:** Synthetic million-row benchmark and EXPLAIN (ANALYZE, BUFFERS); browser trace; make check.
- **Pre-data boundary / risk:** No claimed organizer SLA or real workload representativeness; schema/index/runtime changes require a separate R2 implementation task.

## TASK-042

**Verify offline synthetic data-to-map integration** — RQ-01–05.

- **Evidence / scope:** [scripts/smoke.sh](../../scripts/smoke.sh). Extend existing isolated smoke to fixture ingestion → baseline → evaluation → publication → route/stop/window API → Moscow map; cover all horizons.
- **Acceptance:** Fresh isolated stack and no external network can demonstrate valid coherent forecast plus invalid-batch preservation, empty interval and stale refresh; data remains labelled synthetic.
- **Focused verification:** make verify-full plus new synthetic pipeline smoke and browser flow; preserve existing checks.
- **Pre-data boundary / risk:** Reuse Compose/worktree isolation, do not mutate shared volumes. Final integration gate belongs to lead.

## TASK-043

**Rehearse first-data arrival and freeze a reviewable demo** — RQ-01–05.

- **Evidence / scope:** [README.md](../../README.md). Document exact bootstrap/intake/train/publish/demo commands, reset/recovery and capability limitations; exercise a clean checkout and schema-variation fixture.
- **Acceptance:** One reproducible handoff includes run/config versions, required filters/map, failures and recovery, measurements and unknowns; no fabricated competition score or validated accuracy.
- **Focused verification:** Clean isolated rehearsal; make verify-full; command/path review.
- **Pre-data boundary / risk:** Confirm organizer rules, input/submission format and allowed prebuilt code when available; do not publish externally automatically.

## TASK-044

**Preserve directional ordered route patterns for assignment** — EXT: route assignment.

- **Evidence / scope:** [backend/app/domain/tram_graph.py](../../backend/app/domain/tram_graph.py). Add separate ordered relation/direction/pattern artifact rather than treating sorted stop IDs as route traversal.
- **Acceptance:** Loops and repeated stops retained; existing route-set API preserved; provenance and pattern direction tested.
- **Focused verification:** Extractor/pattern fixtures; make backend-check contract-check.
- **Pre-data boundary / risk:** Optional after core map/filter delivery; OSM pattern availability is not actual timetable/capacity evidence.

## TASK-045

**Define a unit-consistent capacity model and solver port** — EXT: what-if.

- **Evidence / scope:** [backend/app/application/services/forecast.py](../../backend/app/application/services/forecast.py). Extract demo math behind an application port; specify departures, bucket duration and vehicle capacity with explicit fleet/cycle assumptions.
- **Acceptance:** Zero-change identity; increasing headway lowers service frequency; absent schedule/capacity produces unavailable result; baseline immutable; existing demo behavior labelled.
- **Focused verification:** Hand-calculated domain and fake-solver contract tests; make backend-check.
- **Pre-data boundary / risk:** No arbitrary 8%-per-vehicle formula presented as physics; not required to complete organizer forecasting features.

## TASK-046

**Prototype demand-conserving assignment and graph overlays** — EXT: OD and what-if.

- **Evidence / scope:** [backend/app/domain/tram_pathfinding.py](../../backend/app/domain/tram_pathfinding.py). Research a simple deterministic toy-network baseline; add immutable closures/local demand overlays separate from demand prediction.
- **Acceptance:** Explicit synthetic OD: served + unmet equals input; capacities respected; ties deterministic; disconnected/closed paths produce unmet demand; source graph unchanged.
- **Focused verification:** Hand-calculated tiny-network conservation/capacity tests; make backend-check ml-check.
- **Pre-data boundary / risk:** Shortest rail path is not behavioral assignment. Adoption on real transport requires TASK-052 and schedule/capacity evidence.

## TASK-047

**Persist reproducible scenario runs without overwriting forecasts** — EXT: what-if.

- **Evidence / scope:** [backend/app/domain/forecast.py](../../backend/app/domain/forecast.py). Record exact normalized inputs, baseline run, graph/solver version and outputs with replay semantics.
- **Acceptance:** Repeated run reproduces outputs; published forecast unchanged; failed scenario leaves no apparently complete record; compatibility maintained.
- **Focused verification:** Scenario replay/transaction/API tests; clean new migration; make backend-check migration-verify contract-check.
- **Pre-data boundary / risk:** Synthetic/committed inputs suffice; real-data quality is not claimed.

## TASK-048

**Show optional scenario deltas and reproducible comparisons** — EXT: what-if.

- **Evidence / scope:** [frontend/src/features/forecast/components/scenario-panel.tsx](../../frontend/src/features/forecast/components/scenario-panel.tsx). Show available signed deltas, affected stops, exact inputs/run and limitations; disable unsupported controls explicitly.
- **Acceptance:** Baseline/scenario share unit/window; no invented uncertainty or redistribution; accessible comparison table and input-bound result export.
- **Focused verification:** Scenario fixture/E2E and accessibility checks; make frontend-check contract-check e2e.
- **Pre-data boundary / risk:** Cannot delay route/stop/time forecast acceptance.

## TASK-049

**Inspect organizer data and confirm the measurable target** — RQ-01–03.

- **Evidence / scope:** [docs/product/TASK.md](../../docs/product/TASK.md). On authorized receipt, record checksums/schema/licence/coverage, actual validation semantics, incumbent availability, scoring and submission requirements.
- **Acceptance:** Read-only report resolves or explicitly blocks targets/horizons; immutable source retained; minimum privacy/retention decisions recorded; no raw sensitive data committed.
- **Focused verification:** Run intake profiler on permitted sample and reconcile supplied totals.
- **Updated 2026-09-25:** Authorized ZIP and detailed PDF have arrived. TASK-059
  [evidence](../analysis/2026-09-25-organizer-data/README.md) resolves source target,
  full raw/labels reconciliation and submission rules. The former data-arrival
  blocker is removed; TASK-039 toolkit dependency and formal adapter/coverage
  certification remain open. No licence/retention policy was supplied with the
  archive. Next action: review this evidence with TASK-039, settle source coverage
  and route-only contract policy, and record the remaining data-owner decisions.

## TASK-050

**Implement and certify real adapters and map crosswalks** — RQ-01, RQ-03–04.

- **Evidence / scope:** [docs/tram-graph.md](../../docs/tram-graph.md). Map actual columns/IDs/time semantics; reconcile validation/telemetry and OSM joins with explicit coverage and ambiguity reports.
- **Acceptance:** Known sample totals/time buckets reconcile; unmatched cases retained; rerun/resume idempotent; schema drift rejected; coverage decision documented.
- **Focused verification:** Real-sample adapter tests plus synthetic regressions; intake reconciliation; make ml-check backend-check.
- **Pre-data boundary / risk:** Blocked by TASK-049 source access and field meaning; data owner resolves ambiguous identities, not nearest-name guesses.

## TASK-051

**Evaluate and promote models on untouched real temporal slices** — RQ-02, RQ-05.

- **Evidence / scope:** [ml/evals/README.md](../../ml/evals/README.md). Run complete-horizon backtests against executable baselines and supplied incumbent, calibrate intervals and select a model by agreed per-slice criteria; include TASK-023 only if available, never block baseline evaluation on boosting.
- **Acceptance:** Document folds/date coverage/metrics for every horizon and route/stop slices; insufficient yearly history remains failed/unverified; test holdout never tunes model; publish model card.
- **Focused verification:** make ml-eval plus reproducible real backtest report; independent review of split/leakage and promotion artifact.
- **Pre-data boundary / risk:** Blocked by adequate labelled history, target agreement and acceptance thresholds; no guarantee an AI candidate beats baseline.

## TASK-052

**Establish whether occupancy and OD are identifiable** — RQ-05 / EXT: OD.

- **Evidence / scope:** [docs/product/CONCEPT.md](../../docs/product/CONCEPT.md). Check exits/trips/vehicle capacities and permitted linkage; determine which load/OD quantities are observed, estimable with assumptions, or unsupported.
- **Acceptance:** Written capability decision with counterexamples and uncertainty; boarding counts never relabelled onboard occupancy; scenario validation eligibility explicit.
- **Focused verification:** Sample-based identifiability review with documented assumptions and lawful field availability.
- **Pre-data boundary / risk:** Blocked by real schema and capacities/trip evidence. Human/data owner resolves unsupported target; core boarding forecast remains possible when confirmed.

## TASK-053

**Gate spatial or graph-model experiments on measured baseline failures** — EXT: graph ML.

- **Evidence / scope:** [docs/product/CONCEPT.md](../../docs/product/CONCEPT.md). Only if residual spatial structure and sufficient data justify it, compare a modest spatial feature baseline before researching ST-GNN/transformer adoption.
- **Acceptance:** Primary-paper/library evidence, identical folds and ablations; accept only agreed multi-slice gains within runtime budget; losing experiment documented, not promoted.
- **Focused verification:** Reproducible controlled backtests and resource report; make ml-check ml-eval.
- **Pre-data boundary / risk:** Deferred until residual evidence exists; no speculative framework/dependency installation now.

## TASK-054

**Assess multimodal expansion only after tram acceptance** — EXT: multimodal.

- **Evidence / scope:** [docs/product/CONCEPT.md](../../docs/product/CONCEPT.md). Identify concrete tram forecast benefit, available metro/bus transfer data and legal/source limits before extending graph/data contracts.
- **Acceptance:** Decision states measurable benefit, inputs, transfer semantics and acceptance experiment, or explicitly rejects expansion.
- **Focused verification:** Primary-source/source-availability review and toy transfer contract tests if adopted.
- **Pre-data boundary / risk:** Not an organizer requirement; external data availability and completed tram core are adoption gates.

## TASK-055

**Bound shared Overpass requests and failure resource usage** — RQ-04.

- **Evidence / scope:** [backend/app/infrastructure/overpass.py](../../backend/app/infrastructure/overpass.py). Review and implement explicit timeout, response-size and concurrency limits around existing gateway; keep known partial-result error handling.
- **Acceptance:** Fake upstream oversized/slow/saturated responses fail explicitly without exhausting ordinary API capacity; valid responses unchanged; no live stress test.
- **Focused verification:** Fake-client timeout/size/concurrency tests and isolated smoke; make backend-check compose-check.
- **Pre-data boundary / risk:** Choose documented local budgets, not invented organizer SLA; transport changes require official-library research.

## TASK-056

- **Allocation:** parallel block [`for-vova-huesos`](FOR_VOVA_HUESOS.md) — owner, order and file boundaries are defined there.

**Export a self-describing dispatcher forecast report** — RQ-05.

- **Evidence / scope:** [frontend/src/features/forecast/components/forecast-chart.tsx](../../frontend/src/features/forecast/components/forecast-chart.tsx). Add user-triggered CSV/report export of selected run/route/stop/window with units, bounds, provenance and synthetic/stale label.
- **Acceptance:** Export values equal visible selected data; timezone and units retained; no raw passenger IDs; empty/error state has no misleading export.
- **Focused verification:** Fixture-based export/value-parity tests; make frontend-check.
- **Pre-data boundary / risk:** Helpful decision support, not an explicit organizer submission format; do not send reports externally.

## TASK-057

**Explain model behavior and compare baseline errors** — RQ-02, RQ-05.

- **Evidence / scope:** [ml/src/tramflow_ml/evaluation.py](../../ml/src/tramflow_ml/evaluation.py). Create model-card/error diagnostics for horizon/route/stop, data support and feature availability; explain associations without causal claims.
- **Acceptance:** Report includes baseline comparison, worst slices, peak misses, unavailable inputs and synthetic marker; feature importance computed on valid temporal partitions.
- **Focused verification:** Known-error fixture report tests and held-out importance checks; make ml-check ml-eval.
- **Pre-data boundary / risk:** Real quality narratives wait for TASK-051; a diagnostics artifact can be implemented now without a new UI screen.

## TASK-058

**Run an evaluation-gated offline forecasting pipeline** — RQ-01–03.

- **Evidence / scope:** [ml/src/tramflow_ml/cli.py](../../ml/src/tramflow_ml/cli.py). Provide one config-driven command from canonical fixture input through features, temporal baseline evaluation, validated export and explicit publication.
- **Acceptance:** Artifact/report share manifest/hash; failed quality exits nonzero without switching active run; repeated seed/config deterministic; dry-run does not publish.
- **Focused verification:** Tiny fixture end-to-end and injected quality failure; make ml-check ml-eval backend-check.
- **Pre-data boundary / risk:** Synthetic/committed inputs suffice; real-data quality is not claimed.

## Research basis

Sources reviewed on 2026-09-23:

- [GitHub: Best practices for Copilot tasks](https://docs.github.com/en/copilot/tutorials/cloud-agent/get-the-best-results)
  recommends bounded tasks with context and complete acceptance criteria. Here,
  the existing task template holds that detail and the index provides discovery.
- [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
  describes incremental work, persisted progress, and verification before declaring
  completion. Those principles fit handoffs between repository sessions. Its
  experimental harness uses JSON feature lists; this small hackathon repository
  uses reviewable Markdown alongside its existing plans instead. Markdown offers
  no automatic locking or schema enforcement: one index owner and diff review
  mitigate collisions and stale status. This is a process choice, not a measured
  improvement to forecast accuracy or runtime SLA.

## TASK-059

User-authorized first-data analysis on 2026-09-25, independent of the unfinished
TASK-039 toolkit. Scope: read-only full raw/labels reconciliation, reference-table
audit, exploratory seasonal backtests, application compatibility report. No
production adapter/model/API changes and no takeover of TASK-020/039.

Owner: real-data-eda lead. Base 0767619f487725e516ae3d00ef6ef138520160f1;
branch agent/real-data-eda; worktree
/Users/cute/MosTransport2026Hack-worktrees/real-data-eda.
Owned files: docs/analysis/2026-09-25-organizer-data/* and this tracker entry.

Hypothesis: successful source rows reproduce route/hour labels when event-time
file tails are handled; production code remains unchanged. Acceptance: complete
raw scan, exact reconciliation or quantified mismatch, safe evidence without card
identifiers, frozen-origin baseline diagnostics, concrete contract/publication gaps.
Verification: supplied-data assertions, baseline reproducibility and make check.
See the [report](../analysis/2026-09-25-organizer-data/README.md) and its HANDOFF.md
for observed evidence, known limitations and exact next action.

2026-09-25 result: full scan 62,443,497 raw rows; exact match of all 57,551
labels after union and pre-November cutoff. Ten frozen-origin seasonal experiments
reproduced byte-for-byte. Parent make check passed: backend350 (48SQL skipped),
ML265, frontend92, reference119; static/build/OpenAPI/Compose gates passed.
Independent report review passed after clarifying the PDF performance attribution.
Integration method: local fast-forward of reviewed research commit; no remote push.
Worktree retained because branch is unpushed. Production implementation remains open.
