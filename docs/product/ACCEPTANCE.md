# Acceptance assumptions and organizer questions

TASK-003, recorded 2026-09-23. The [organizer task](TASK.md) is authoritative.
This register freezes the team's pre-data acceptance interpretation, not an API,
dataset schema, organizer scoring rule, or claim that these cases already pass.
Implementation evidence belongs in the [task tracker](../agentic/TASK_TRACKER.md).

## Known requirements and provisional choices

| Topic | Known requirement / constraint | Provisional preparation choice | Confirmation gate |
|---|---|---|---|
| Target and unit | Passenger flow/load is requested; its measurement is unspecified. | Synthetic boarding-event counts per bucket, explicitly labelled synthetic. A validation is not automatically a unique person, boarding or onboard occupancy. No real target is frozen. | Q01; TASK-049/052 |
| Horizons and calendar | One day, one month and one year are required. | Hourly, daily and monthly buckets respectively; calendar months/years, including leap boundaries, rather than 30/365-day approximations. Exact origin/service-day rules belong to TASK-015. | Q02; TASK-015/049 |
| Time and filtering | Route, stop and time selection are required. [Architecture](../architecture/README.md) specifies UTC storage, Europe/Moscow display and half-open windows. | Test `[from, to)` boundaries and preserve timezone and bucket units in outputs; missing observations stay distinct from zero. | Q02/Q03; TASK-015/050 |
| Refresh | An updating Moscow map is required. | Timestamped synthetic replay/polling demonstrates refresh; source cutoff, generation and UI retrieval are distinct times. Test-controlled cadence is not a production SLA. | Q04; TASK-035/049 |
| Quality | The organizer seeks improved forecasts over simple regression. No metric, incumbent or acceptance margin is supplied. | Compare executable baselines on identical chronological folds for every horizon. Existing golden thresholds are development checks only. | Q05; TASK-051 |
| Decision support | Geographical and temporal forecasts should support fleet decisions. | Show peaks, units, uncertainty availability and provenance. Capacity ratios require compatible units and capacity evidence; absent capacity is unavailable, not zero. | Q01/Q06; TASK-052 |
| Stack and scope | Java/Spring/Netty appear as participant skills, not a mandatory stack. | Retain the current stack; OD, multimodal modeling, graph ML and automatic allocation remain optional. | Q07; organizer rules |

## Measurable acceptance cases

All cases below are planned checks, not results. Passing synthetic cases establishes
implementation behavior only. It cannot establish real accuracy, calibrated
uncertainty, actual operational capacity or organizer acceptance.

| Requirement | Synthetic acceptance case and observable pass condition | Separate real-data acceptance gate | Delivery evidence owner |
|---|---|---|---|
| RQ-01 | Fixed-seed fixture spans at least two calendar years and 1,000,000 rows. Accepted, quarantined and duplicate counts reconcile exactly to input under the documented mutually exclusive classification; rerun/resume does not duplicate accepted events. Record throughput, peak memory, hardware and config against a budget declared before the scale run; do not call an unbudgeted run a scale pass. Invalid batches do not replace published forecasts. | Authorized immutable source, schema/rights and event semantics confirmed; supplied totals reconciled; actual volume/date coverage profiled and measured within agreed local budgets. No claim that two years alone supports annual backtesting. Q01–Q03/Q08. | TASK-016/017/039/041/042; real TASK-049/050 |
| RQ-02 | Deterministic multiyear fixture includes enough training and complete held-out horizon for each test origin. Day/month/year each produces finite, nonnegative, correctly dated predictions and baseline metrics on multiple chronological origins. Hand-calculated error cases match; absent horizon, nonfinite values and insufficient history fail explicitly. Bounds, when supplied, contain the prediction and retain their method/provenance; interval quality is evaluated separately. A losing candidate is not promoted. | Confirm target, metric, incumbent and per-slice promotion thresholds before evaluation; run untouched real temporal slices with adequate history for every horizon and report baseline comparisons and interval coverage. Unsupported annual history remains unverified. Q01/Q02/Q05. | TASK-004/020–024/058; real TASK-051 |
| RQ-03 | Fixture has route A: stop S1 counts 2 and 3, stop S2 counts 5 and 7 in adjacent one-hour buckets; another route has a distinct value. First bucket returns route A total 7 and S1 total 2; both buckets return 17 and 5. The exclusive end excludes the next bucket, other routes never enter the sum, and no join duplicates counts. Empty windows differ from observed zero; invalid windows fail. Repeat boundary checks for month/year buckets and Moscow calendar transitions. | Actual route/direction/stop IDs, time semantics and source-to-map crosswalk reconcile against a known sample; unmatched/ambiguous rows have explicit coverage decisions. Aggregation must match the confirmed target's additive or non-additive semantics. Q01–Q03. | TASK-015/028/032/033; real TASK-050 |
| RQ-04 | Replay runs A then B on committed Moscow geography with known stop values for every horizon. Map, chart and KPI agree on run/selection/value after refresh. Delay A until after B and verify A cannot overwrite B. Inject refresh and basemap failures: last good data is visibly stale, first-load error differs from empty, retries recover, and map or accessible alternative remains inspectable without a live external service. Show generation/source/fetch times and synthetic label. | Confirm live versus batch feed availability, refresh cadence, latency/freshness definitions and deployment conditions; demonstrate agreed update behavior with authorized real inputs and report crosswalk coverage. Replay alone does not certify a live feed. Q03/Q04/Q07. | TASK-007–010/034/035/037/042; real TASK-049/050 and operational rehearsal |
| RQ-05 | Known fixture peak is correctly identified by route, stop, timestamp and unit; every plotted value and available bound can be inspected by keyboard. Missing capacity/intervals are labelled unavailable. Provenance and synthetic/stale status remain visible. A dispatcher can select the peak's location/time and recover from a failed refresh without confusing old and new runs. No unsupported fleet optimum or occupancy claim appears. | Dispatcher/domain owner confirms units, useful workflow and capacity assumptions using real samples; model quality and supported uncertainty pass RQ-02 gates. Occupancy/OD remain unsupported without identifying evidence. Q01/Q05/Q06. | TASK-005/033–036/038/043; real TASK-051/052 |

The route/stop arithmetic above is a count-target test, not permission to sum
occupancies or rates. TASK-015 must specify aggregation semantics before these
cases become data/API contracts. Boundary fixtures must include year rollover,
February in leap and non-leap years, and events at exactly `from` and `to`.

## Unresolved organizer questions

Every answer below is **unresolved**. The lead records the respondent, date and
source of each answer here before changing an assumption; only the organizer or
authorized data/domain owner can resolve external facts. No questions have been
sent by this task.

| ID | Question for organizer / data owner | What stays gated pending an answer |
|---|---|---|
| Q01 | What is the target and unit: validations, boardings, unique passengers, onboard count or load ratio? What labels, sampling and corrections establish ground truth? | Real target certification and occupancy claims; synthetic count scaffolding may proceed. |
| Q02 | What are horizon origins, required output cadence, timezone, service-day rollover, timestamp meaning and late-arrival/availability rules? How much complete history exists? | Real adapters, leakage-safe fold eligibility and calendar alignment. |
| Q03 | What file schemas, route/direction/trip/vehicle/stop identifiers, identifier versions and crosswalks are supplied? How are duplicates, cancellations and missing telemetry represented? | Actual field mapping and entity reconciliation; do not guess columns or nearest-name joins. |
| Q04 | Is a live feed available, or only historical/batch files? What refresh cadence, end-to-end latency, freshness cutoff and outage behavior will be assessed? | Live/SLA claims; configurable labelled replay can proceed. |
| Q05 | What scoring metrics, horizon/slice weights, holdouts, baseline/incumbent outputs, uncertainty requirements and acceptance thresholds apply? | Real model promotion and competition-score claims; local evaluator robustness can proceed. |
| Q06 | Are schedules, departures, vehicle capacities, exits or permitted trip linkage available? Which dispatcher decisions and capacity units should be supported? | Validated occupancy, OD and fleet optimization; geographic count forecasts remain eligible when target confirmed. |
| Q07 | Is Python allowed? What pre-event code/data/model reuse, external services, offline operation, deployment and submission artifact/format rules apply? | Competition eligibility and submission/deployment decisions; no assumed permission to publish externally. |
| Q08 | What access licence, privacy/retention, authorized storage and redistribution constraints cover source data and derived artifacts? Who grants access? | Real-data intake and sharing; synthetic tooling uses no passenger identifiers. |

## Next contract boundary

TASK-015 may use these provisional cases to design synthetic target/entity/calendar
and manifest contracts. It must not mark unresolved organizer facts confirmed.
TASK-025 separately freezes publication; TASK-049/050 resolves source mapping;
TASK-051 certifies quality only after the real gates. No production schema or
dependency is introduced by this register.
