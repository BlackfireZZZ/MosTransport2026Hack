# Pre-hackathon preparation analysis

Reviewed 2026-09-23. Scope is governed by the corrected
[official task](TASK.md), preserved from the user's supplied text. The
[task tracker](../agentic/TASK_TRACKER.md) is the live work queue; this document
explains why the tasks exist and how to sequence them. No product implementation
is claimed by this planning change.

## What can be finished before data arrives

Build a complete, reproducible synthetic-data path from raw validations/telemetry
through normalization, three-horizon baselines, evaluation, atomic publication,
route/stop/time filtering and an updating Moscow map. Build the first-data tools
and failure tests now, so arrival of actual files mainly requires source mapping,
profiling, real backtests and model selection. This is more valuable than selecting
a graph architecture before the measurable target and data coverage are known.

The current concept aligns with passenger forecasting, but its OD inference,
multimodal network, assignment solver and what-if ambitions are optional extensions.
Keep them outside the critical path. Boarding validations are not automatically
onboard occupancy, unique people or OD pairs. Real-time map refresh is a display
requirement; it does not establish that live telemetry will be supplied or that
models must retrain continuously. Java/Spring/Netty are listed participant skills,
not an explicit instruction to replace the existing Python stack.

## Requirements mapped to current evidence

| Requirement | Present and reusable | Missing / proposed tasks |
|---|---|---|
| RQ-01: multiyear, million-row data | Offline ML workspace; PostgreSQL serving; immutable-data rules | No ingestion/normalization/telemetry alignment. TASK-015–019, 039, 041; real intake TASK-049–050. |
| RQ-02: day/month/year ML forecasts | Three API horizon values, seed arrays and evaluation CLI | No executable forecasting pipeline, temporal folds or model publication. TASK-004, 020–025, 027–029, 051, 057–058. |
| RQ-03: route/stop/time aggregation | Route+horizon selection and indexed forecast table | API/client only accept route+horizon; stop joins can multiply rows across buckets. TASK-015, 018–019, 025–028, 032–034. |
| RQ-04: updating Moscow map | Real OSM map and local topology, route/path browser, forecast chart, polling | Forecast schematic and OSM map are separate; no shared time/run/stop selection. TASK-005, 007–012, 030–038, 042. |
| RQ-05: dispatcher allocation support | Dense work surface, predicted counts/bounds/capacity fields, demo scenario | Honest target/capacity semantics, reliable peaks/uncertainty/freshness, selectable geography/time. TASK-015, 022–024, 033–036, 056–057; real capability review TASK-052. |

Already implemented: central typed API client, React/TanStack Query, local shadcn
primitives, MapLibre lazy loading, JSON access logs/request IDs, liveness/readiness,
OpenAPI drift checks, locked dependencies, isolated Compose/worktrees, migration
and smoke commands. Do not allocate duplicate setup tasks for these.

The OSM asset is useful reference geography: documented 856 stops, 919 directed
edges and two disconnected components. It is not measured passenger demand,
actual timetable, service capacity or ground truth for routing choices.
[ADR-0003](../decisions/0003-tram-graph-file-repository.md) keeps it file-backed;
a map join does not by itself justify replacing that design.

## Findings and strength of evidence

| Finding | Repository evidence | Confidence / smallest disproof |
|---|---|---|
| Evaluator accepts NaN and can pass with zero coverage in one horizon | [evaluation.py](../../ml/src/tramflow_ml/evaluation.py) | Reproduced by read-only Python probe; TASK-004 adds regression tests. |
| Forecast rows have no coherent run selection or time bounds | [forecast repository](../../backend/app/infrastructure/repositories/forecast.py) | Code inspection; two-run/multi-bucket PostgreSQL fixture in TASK-027/028. |
| Nullable stop key can permit duplicate aggregate records; capacity division is unguarded in domain | [DB models](../../backend/app/infrastructure/db/models.py), [domain](../../backend/app/domain/forecast.py) | Code + PostgreSQL constraint semantics; verify with clean DB fixtures. |
| Year seed uses 30-day steps; no target/count-rate contract | [initial migration](../../backend/alembic/versions/20260919_0001_initial.py) | Direct inspection; new calendar fixtures/publication rather than rewriting migration. |
| Baseline arrays are hand supplied; ForecastModel has no producer/publisher | [golden fixtures](../../ml/evals/golden_cases.json), [protocol](../../backend/app/ml/protocols.py) | `rg` consumer search; one runnable batch path is acceptance. |
| Partial Overpass response can reach extractor writes | [extractor](../../scripts/fetch_tram_graph.py) | Code inspection; existing API error handling is not used by this script; inject remark payload. |
| Selected stop/window is absent from forecast request | [client](../../frontend/src/api/client.ts) | Direct signature and consumer inspection; TASK-028/033 add contract and browser tests. |
| Scenario inputs can change while old output remains; refresh errors hide prior forecast | [scenario panel](../../frontend/src/features/forecast/components/scenario-panel.tsx), [App](../../frontend/src/App.tsx) | Code-supported findings, not browser-reproduced failures; fault/race tests first. |
| Basemap error message can promise graph rendering before style load | [map component](../../frontend/src/features/tram-network/components/tram-map.tsx) | Hypothesis from lifecycle inspection; blocked-style browser reproduction required. |
| E2E fixture peak and month/year chronology contradict their own points | [dashboard E2E](../../frontend/e2e/dashboard.e2e.ts) | Direct fixture inspection; invariant factory tests. |

Baseline verification before backlog edits: `make check` passed on Node 24.19.0
after restoring existing locked frontend dependencies with npm 11.19.0. Observed:
61 backend tests, 3 ML tests, 23 frontend tests; static checks, production build,
OpenAPI drift and Compose configuration passed. This does not certify migrations,
browser behavior, million-row performance or model accuracy. Those require the
separate checks listed in future tasks. Initial Node 18 and stale-dependency
failures were local environment issues; no manifest/lock edits were needed.

## Delivery order and stopping points

The tracker lists 56 proposed future tasks, plus two documentation tasks. They are
an ordered preparation inventory, not a promise to finish everything in three days.
Prioritize the following vertical milestones; secondary robustness tasks can be
scheduled alongside them under the ownership rules below.

| Milestone | Work | Evidence of value before actual data |
|---|---|---|
| 1. Honest, stable foundation | TASK-003–005, 007–014, 026; optional existing scenario fix 006 | Clear requirements/demo state; reproduced defects covered; usable offline geography and SQL harness. |
| 2. Frozen synthetic contracts | 015–016, 025; 011/012→030; 018→032 | No guessed organizer schema; target/time/entity/publication fixtures let teams work independently. |
| 3. Offline baseline and serving in parallel | Data 017→019→020→021/022→024; serving 025+026→027→028 and 029 | Data runner and SQL/API consumer are independently testable against the same artifact. |
| 4. Required dispatcher work surface | 010+028→033; 008+032+033→034→035→036; 037→038 | Route/stop/window changes synchronously update map/chart/KPI, with honest freshness and units. |
| 5. Full pre-data rehearsal | 058→042; 039, 040, 041→043 | Reproducible synthetic ingestion→model→publication→map plus first-data diagnostics and recovery. |
| 6. Additional useful depth | 023, 031, 055–057; optional 044–048 after core | Candidate, geometry quality, resource limits, explanations/export; optional scenarios do not block core. |
| 7. Actual data and evidence | 049→050→051; 050→052 | Real target/joins/coverage, honest long-horizon evaluation and model promotion. |

The principal modeling dependency chain is
`003 → 015 → 016 → 017/018 → 019 → 020 → 021/022 → 024 → 058`.
The serving chain is `015 → 025 → 027 → 028`, with `026` available immediately.
Publication `029` uses validated fake artifacts first and does **not** wait for a
trained model. The map chain is `011/012 → 030`, then `018+030 → 032`, then
`028+032+033 → 034`. Integration `042` joins these chains.

For limited time, reach milestone 5 with executable baselines before attempting
nonlinear models or scenarios. The full mandatory path never depends on
TASK-044–048, 053 or 054. A prototype losing to a baseline is useful evidence;
a misleading claim of real model quality is not.

## Parallel execution without competing edits

| Lane | Exclusive ownership and useful concurrency |
|---|---|
| CONTRACT | TASK-003/015/025 and requirements/manifest fixtures. One integration owner freezes shared schemas. Backend/ML reviewers are read-only until ownership is allocated. |
| DATA / DATA-FEATURES | Generator→ingestion→features→intake. Pipeline modules can split after shared schemas freeze; keep CLI edits with one owner. |
| DATA-MAPPING | TASK-018/032 and later real adapter mapping. Can parallelize with ingestion, but owns crosswalk semantics consumed by both ML and map. |
| ML-EVAL | TASK-004 first; 020→022 and 057 later. One owner of evaluation.py and golden gate; do not parallel-edit them for separate metrics. |
| ML-MODEL / ML-UNCERTAINTY | Baselines→candidate; intervals after evaluator interface freeze. Distinct model/calibration modules permit parallel work; shared CLI and manifests merge through lead. |
| SERVING / BATCH-PUBLISH | One owner of forecast domain/API/persistence and migrations; publisher adapter in a separate owned module after TASK-025. Run/freshness schema remains single-owner. |
| GRAPH-EXPORT / GRAPH-LOAD | Extractor and loader fixes can run independently; agree manifest/geometry contracts before TASK-030/031. No simultaneous edits to graph domain contracts. |
| UI-SHELL / UI-MAP / UI-CHART | Distinct feature modules after query contracts freeze. App.tsx, shared CSS, src/api/client.ts and generated schema have one integrator; map filters and shell selection must not be independently redesigned. |
| QA-UI / API-TEST | Fixture/helper and new test modules can be separate ownership areas. Coordinate existing E2E files and contract changes; a test author must not silently redefine product contracts. |
| INFRA / OBSERVABILITY / PERFORMANCE | Separate tests/logging/benchmarks can run concurrently. One owner of Makefile/Compose/CI; unique projects, ports and volumes. |
| SCENARIO | Optional after mandatory milestones; cannot reserve core forecast/domain files against P1 delivery. |

Suggested first four concurrent assignments: lead handles TASK-003 and shared
contracts; ML owner takes TASK-004; map owner takes TASK-008; data/graph owner takes
TASK-011. Then rotate available ownership to TASK-005, 010, 012–014 and 026.
Do not spawn 56 agents: maintain a small active set and one owner per file/contract.
Every writing agent uses an isolated worktree when root criteria apply. Read-only
reviews do not count as parallel writes. Leads alone integrate and run final gates.

## What must wait and what should not be built speculatively

- TASK-049–052 are externally blocked on real schemas, data rights, coverage,
  labels and capacities. Their pre-data tooling is separately executable now.
- Boardings/occupancy/OD distinctions and yearly-fold support cannot be resolved
  by inventing synthetic labels. Keep insufficient-history and unsupported-target
  results explicit.
- Do not adopt Kafka/Spark, a feature store, microservices, a graph database or a
  GNN merely because the brief says millions of rows or AI. Measure ingestion/query
  bounds first. Existing pandas/scikit-learn/PostgreSQL are sufficient starting tools,
  not a guarantee of final scale or quality.
- Do not build a delay-prediction/NDTP product from the superseded brief. The current
  task does not specify that telemetry protocol. Actual format adapters stay configurable.
- Do not turn role examples into an unrequested Java backend rewrite. Escalate only
  if a later authoritative organizer rule explicitly mandates another stack.

## Primary-source research and adaptation limits

Sources checked 2026-09-23. These support candidate approaches, not measured results
on this repository's future passenger data.

| Source | What is reused | Difference / risk |
|---|---|---|
| [Forecasting: Principles and Practice — time-series cross-validation](https://otexts.com/fpp3/tscv.html) | Rolling origins and evaluation at actual forecast horizons for TASK-020 | Yearly validation needs sufficient complete history; short synthetic cases cannot demonstrate that. |
| [scikit-learn lagged forecasting example](https://scikit-learn.org/stable/auto_examples/applications/plot_time_series_lagged_features.html) | Lags, temporal splits, boosting and interval candidates for TASK-019/023/024 | Demand-count example is not tram occupancy; use installed tooling, not every tutorial dependency; benchmark against simple regression. |
| [pandas read_csv](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html) | Iterator/chunksize scaffold for TASK-017 | Chunked reading alone does not bound joins/dedup/aggregation state; measure the entire pipeline and spill or bound state explicitly. |
| [PostgreSQL 17 constraints](https://www.postgresql.org/docs/17/ddl-constraints.html) | Understand null uniqueness and value constraints for TASK-027 | Choose a schema/constraint strategy after the run contract; clean migration and recovery tests remain mandatory. |
| [GTFS Schedule Reference](https://gtfs.org/documentation/schedule/reference/) | Useful distinctions among stops, trips, directions and service-day times for TASK-015/018/044 | A semantic reference only; organizer format is unknown, and schedule availability does not reveal onboard demand. |
| [MapLibre Map API](https://maplibre.org/maplibre-gl-js/docs/API/classes/Map/) | Existing map/style/source lifecycle for TASK-008/034 | Rendering failure must be browser-reproduced; no untested fallback claim, no new map library. |
| [GitHub task guidance](https://docs.github.com/en/copilot/tutorials/cloud-agent/get-the-best-results) and [Anthropic long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) | Bounded acceptance, persisted progress, explicit verified completion | Markdown is light for this repository but provides no lock; shared tracker owner and checked dependencies mitigate collisions. |

## Planning verification record

Completed: 170 local links/anchors; 58 unique task IDs/cards; acyclic dependencies;
ready tasks have no unfinished prerequisites; mandatory work has no optional
prerequisites. Three independent reviews passed after removing an unnecessary
boosting dependency from real baseline evaluation. `git diff --check` and lead-run
`make check` passed (exit 0): 61 backend, 3 ML and 23 frontend tests, static checks,
production build, OpenAPI drift and Compose config. The 56 future tasks comprise
45 pre-data tasks, 7 optional extensions and 4 externally blocked data tasks;
11 are ready to claim. No product task is marked implemented by this analysis.
The complete worktree/base/integration report is kept in the
[execution plan](../exec-plans/completed/pre-hackathon-backlog.md).
