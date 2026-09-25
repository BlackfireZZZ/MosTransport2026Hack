# ExecPlan: operational slice and interval reporting (TASK-022)

- Branch: `agent/slice-metrics`, base `a87837c`.
- Worktree: `/home/chessnok/hacks/MosTransport2026Hack-worktrees/slice-metrics`.
- Integration owner: the TASK-022 agent; the lead owns `docs/agentic/TASK_TRACKER.md`.
- Parallel writer: TASK-021 owns `ml/src/tramflow_ml/baselines/`. This plan does not
  read, write, or depend on that package.

## 1. Purpose / observable result

A model that is excellent on average and catastrophic on one operational slice must
fail the quality gate, and the verdict must name the slice. Today nothing in the
repository can say that: `make ml-eval` slices only by horizon, and
`BacktestOutcome.passed` is a statement about the fold set, not about quality
(`docs/exec-plans/completed/rolling-backtest.md`, Open risks, last-but-two bullet:
"`passed` is about folds, not quality … TASK-022 owns the quality verdict").

Observable after this change:

- `build_report(points, required=..., thresholds=...)` returns a `SliceReport` whose
  `failures` name every slice that breached a threshold, with the observed value, the
  threshold constant's name and its value, the sample count and the fold count.
- A report whose overall WAPE passes and whose `route_daypart` slice
  `route-A|evening_peak` does not has `passed is False` and a failure line naming that
  slice. Overall performance cannot remove that entry.
- Interval quality is reported as coverage **and** mean width **and** mean interval
  (Winkler) score. A `[0, 10000]` interval scores far worse than a tight one even
  though its coverage is 1.0.
- Every metric carries `unit`, `samples`, `folds`.
- `overload` is `null` with a stated reason whenever the target is not a load or the
  capacity is not known for every point of the slice.
- Two runs over the same points, in any input order, produce byte-identical JSON.

## 2. Context

Existing, read before writing:

- `ml/src/tramflow_ml/evaluation.py` — the golden gate behind `make ml-eval`.
  `evaluate()` slices by horizon only, raises on zero demand, and reports interval
  coverage with no width. Its output must stay byte-identical: `ml/evals/golden_cases.json`
  belongs to TASK-021's evidence scope and `ml/src/tramflow_ml/cli.py` is not ours.
- `ml/src/tramflow_ml/backtest/metrics.py` — `FoldMetrics(scored, actual_total,
  error_total)` with `mae` and `wape` properties, `wape` `None` when `actual_total == 0`.
  `fold_metrics()` sums in a fixed order; `combine()` pools folds by their sums so an
  average of averages cannot hide a slice.
- `ml/src/tramflow_ml/backtest/results.py` — `BacktestStatus = Literal["evaluated",
  "insufficient_history", "insufficient_signal"]`. This is the vocabulary a slice
  verdict must match rather than compete with.
- `ml/src/tramflow_ml/features/records.py` — `EntityKey(route_id, direction_id,
  stop_id)`, `Horizon`, `GRANULARITY_FOR_HORIZON`, `MOSCOW`, `COUNT_UNIT`,
  `require_aware`.
- `docs/decisions/0006-stop-identity-and-direction.md` — a stop is a physical place and
  direction is a separate mandatory axis, never inferred. A route passes a physical stop
  in both directions and tram load is sharply asymmetric between them, so a slice on
  `stop_id` alone is not a slice on an operating side.
- `contracts/forecast_v1.py` — `lower_bound`/`upper_bound` on the point,
  `interval_level`/`interval_method` on the artifact, both-or-neither at each level.
  The contract promises ordering and finiteness; it promises nothing about calibration.
  `AggregationUnit` is `event_count | passengers | vehicles`; `onboard_load` is the only
  target that is an occupancy. Production code must never import `contracts`, so these
  two strings are mirrored as named constants with the mirror stated in the docstring.

Terms used below: a **slice** is a group of scored points sharing one `(axis, value)`.
A **required slice** is one the caller declares must exist and must be judgeable.
**Support** is the pair (samples, folds) behind a number.

## 3. Scope / non-goals

In scope: `ml/src/tramflow_ml/slices/` (new), tests under `ml/tests/test_slices_*.py`
and `ml/tests/test_evaluation_slices.py`, and one `## Slice and interval reporting`
section appended to `ml/README.md`.

Non-goals: changing `evaluation.py`, `cli.py`, `ml/evals/golden_cases.json`,
`contracts/**`, `backend/**`, `frontend/**`, or any other `tramflow_ml` subpackage;
producing predictions of any kind; calibrating intervals (TASK-024); certifying any
threshold (needs organizer data, TASK-051).

## 4. Acceptance

1. `make ml-eval` output is byte-identical to its output at base `a87837c`.
2. `make ml-check` and `make check` pass.
3. A hand-computed fixture (computed on paper, recorded in section 7) matches the
   code's output for MAE, WAPE, coverage, mean width and mean interval score.
4. A report whose overall WAPE passes and whose evening-peak route slice does not has
   `passed is False`, and `failures` names `route_daypart=route-A|evening_peak`.
5. A required slice with no points is `unproven`, not a silent pass.
6. `mean_interval_score` for `[0, 10000]` is larger than for a tight interval whose
   coverage is the same.
7. A zero-demand slice reports `wape: null`, status `insufficient_signal`, and never a
   `0.0` that lowers a pooled ratio.
8. A slice below `MIN_SAMPLES_FOR_GATE` is reported in full, marked, and not gated.
9. `overload` is absent with a reason for `unit="event_count"`, and present only for
   `target="onboard_load"`, `unit="passengers"`, capacity known for every point.
10. Two runs over the same points in different input orders produce identical bytes.

## 5. Progress / decisions

Decisions, each with the alternative that was rejected:

1. **Reuse `backtest.metrics.fold_metrics`/`combine` rather than re-derive WAPE.**
   `rolling-backtest.md` records that refactoring `evaluation.py` to share the summation
   was considered and rejected because it backs `make ml-eval` and its zero-demand
   divergence is intentional. That argument does not apply in this direction: the new
   module is free to adopt the backtest definition wholesale, so there are two
   definitions in the repository, not three, and the zero-demand behaviour is the
   backtest's by construction rather than by a parallel edit. `evaluation.py`'s raising
   behaviour is untouched, so `test_backtest_shared.py`'s pin is unaffected.
2. **Zero demand follows the backtest, not `evaluation.py`.** `wape` is `None` and the
   slice status is `insufficient_signal`. `evaluation.py` raises instead; that is a
   deliberate difference for a curated five-case golden file where a zero-demand horizon
   is an authoring mistake. A real slice with no demand is data, not a mistake.
3. **Small samples are marked, never suppressed and never silently averaged.** A slice
   with fewer than `MIN_SAMPLES_FOR_GATE = 12` scored points, or fewer than
   `MIN_FOLDS_FOR_GATE = 2` distinct folds, keeps every metric and its support, gets
   status `insufficient_samples` or `insufficient_history`, and is excluded from the
   gate. Rejected: suppression (hides the slice, which is the failure mode this task
   exists to prevent) and gating them anyway (a three-sample WAPE is noise, and a gate
   that fails on noise stops being believed). `insufficient_history` is reused from the
   backtest with its meaning intact — too few independent origins. `insufficient_samples`
   is the one new word, for a genuinely different axis: enough origins, too few rows.
4. **Every `evaluated` slice gates; `required` adds existence and judgeability.**
   Rejected: gating only declared required slices, which makes the gate exactly as good
   as somebody's memory. Because small and zero-demand slices are already de-gated by
   decision 3, gating everything does not make the gate fire on noise.
5. **A required slice that is absent or not judgeable is `unproven`, and `unproven`
   blocks the pass.** `passed = not failures and not unproven`. Absence must not buy a
   pass.
6. **Interval quality is the interval (Winkler) score, reported beside coverage and
   width, never coverage alone.** `IS = (u - l) + (2/alpha)(l - y)1{y<l} + (2/alpha)(y - u)1{y>u}`
   with `alpha = 1 - level`; lower is better, unit is the target unit. Rejected:
   coverage plus a width cap, which is two thresholds that trade against each other with
   no stated exchange rate. The score is the standard proper rule for a central interval
   (Gneiting & Raftery 2007, §6.2; Winkler 1972).
7. **The interval score is gated against the slice's mean actual demand, not its MAE.**
   A perfectly predicted slice has `mae == 0`, which makes any score ratio infinite; an
   `evaluated` slice always has `actual_total > 0`, because `actual_total == 0` is
   `insufficient_signal`, so mean actual is always a usable denominator.
8. **The headline slice is a cross, not a single axis.** "Catastrophic at the evening
   peak on one busy route" is route x daypart. A `route_daypart` axis is therefore
   produced alongside the single axes.
9. **Daypart exists only where the bucket is hourly.** `GRANULARITY_FOR_HORIZON` makes
   the `day` horizon hourly and the others daily/monthly. Evening-peak error cannot be
   measured from a monthly bucket, so those points are in no daypart slice at all rather
   than in a fabricated one.
10. **Direction is never collapsed.** Per ADR-0006 the `direction` axis value is
    `route|direction`, because a bare `direction_id` is meaningless across routes, and a
    `stop` axis exists as well but is documented as spanning both operating sides.
11. **Overload needs compatible ground truth, and absence is representable.**
    `overload` is `None` plus a reason unless `target == "onboard_load"`,
    `unit == "passengers"`, and every point carries a positive capacity. The repository's
    open defect — `ForecastPointModel.capacity` defaulting to `180.0` against a
    response schema demanding `gt=0`, so an unknown capacity is served as a fabricated
    number — is not replicated: there is no default capacity anywhere in this module.
12. **Points are canonically sorted before summation.** Float addition is not
    associative, so a report that summed in caller order would be order-dependent.
    Sorting by `(horizon, entity, bucket_start in UTC, fold_id)` makes the bytes a
    function of the point set alone.
13. **One unit and one target per report.** A report pooling event counts with passenger
    loads has no unit, so mixing them is refused at the boundary.
14. **Thresholds are a frozen dataclass whose defaults are the named constants, and the
    report prints them with `"certified": false`.** Each failure carries the constant's
    name beside the observed value it judged.

15. **`evaluation.py` is not edited at all — a deliberate deviation from the card's
    stated scope.** The TASK-022 card names `ml/src/tramflow_ml/evaluation.py` under
    "Evidence / scope". It was planned to gain a `slice_points()` bridge; that was
    dropped after the design settled, for two reasons. A golden case carries no entity
    and no bucket instant, so a bridge would have had to invent a timestamp, and the
    daypart axis is *derived* from that timestamp — a fabricated 18:00 would have
    manufactured an evening-peak slice out of nothing, which is precisely the kind of
    dishonesty this task exists to prevent. And `evaluation.py` backs `make ml-eval`,
    whose output the brief requires to stay byte-identical; every line not written there
    is a line that cannot break it. The link the bridge was for is provided instead by
    `ml/tests/test_evaluation_slices.py`, which imports both modules and pins their WAPE
    and MAE against each other on the real `ml/evals/golden_cases.json` — the same
    pattern `test_backtest_shared.py` already uses for the backtest. That file also
    demonstrates, rather than asserts, why the second reporter exists: a `[0, 10000]`
    interval passes the golden gate at coverage 1.0 and fails the slice report on its
    interval score. Nothing in the card's acceptance criteria requires an edit to
    `evaluation.py`; all four are met by the new package.
16. **Adding width and interval score to `evaluate()` was considered and rejected.**
    It would be a real improvement — the golden gate reports coverage alone, which is
    the exact failure mode named in this card — but it changes `make ml-eval` bytes
    while TASK-021 is running against that gate in parallel, for a benefit TASK-058
    gets anyway when it routes publication through `slices`. Recorded here as known
    debt rather than done quietly.

Milestones: (a) plan; (b) `slices/` with tests, hand fixture first; (c) gate and
interval demonstrations; (d) the golden-gate agreement test; (e) README section;
(f) full verification.

## 6. Research evidence

- Winkler, R. L. (1972), "A Decision-Theoretic Approach to Interval Estimation",
  *JASA* 67(337) — the original central-interval score.
- Gneiting, T. & Raftery, A. E. (2007), "Strictly Proper Scoring Rules, Prediction, and
  Estimation", *JASA* 102(477), §6.2 — the interval score as the proper rule for a
  central prediction interval, and the statement that it decomposes into width plus a
  miss penalty, which is why coverage alone cannot be the criterion.
- Gneiting, T. & Katzfuss, M. (2014), "Probabilistic Forecasting", *Annual Review of
  Statistics and Its Application* 1 — "sharpness subject to calibration", the principle
  behind reporting width beside coverage.
- Hyndman, R. J. & Koehler, A. B. (2006), "Another look at measures of forecast
  accuracy", *IJF* 22(4) — why a percentage error is undefined at zero demand, which is
  the same rule `backtest/metrics.py` already applies.

No internet access was used; these are cited from the standard literature and none of
them is implemented from a copied source — the interval score is four arithmetic
operations and is written out in `slices/metrics.py` in the form given above. Nothing
here introduces a dependency: `ml/pyproject.toml` is unchanged.

## 7. Validation / recovery

Commands and observed output are recorded below as they are run.

### `make ml-eval` before and after

Captured at base `a87837c` before any file was created, and again with the package in
place. Both runs exit 0 and the captured bytes are identical:

```
$ sha256sum /tmp/ml-eval-before.txt /tmp/ml-eval-after.txt
cff74cfae2539325321f47065ddcf2bde1eaf6d8114401cb33e7faf11be9225f  /tmp/ml-eval-before.txt
cff74cfae2539325321f47065ddcf2bde1eaf6d8114401cb33e7faf11be9225f  /tmp/ml-eval-after.txt
$ diff /tmp/ml-eval-before.txt /tmp/ml-eval-after.txt && echo IDENTICAL
IDENTICAL
```

### `make ml-check` and `make check`

```
$ make ml-check          # exit 0
ruff: All checks passed!
mypy: Success: no issues found in 56 source files
pytest: 529 passed in 33.46s     (479 before this branch; 50 new)

$ make check             # exit 0
Architecture boundaries passed.
backend:   292 passed, 10 skipped
ml:        529 passed
ml-eval:   "passed": true
frontend:  8 test files, 47 passed; lint and build clean
contracts: 119 passed
compose:   docker compose config --quiet
```

### Hand-computed fixture

Computed on paper first, then compared with the code. Four points, one entity, `day`
horizon, level 0.8 so `alpha = 0.2` and the miss multiplier is 10. The table, the
arithmetic and the expected values are the module docstring of
`ml/tests/test_slices_metrics.py`; the code agrees with all of them.

| quantity | by hand | from the code |
|---|---|---|
| `actual_total` | 100+200+150+50 = 500 | 500.0 |
| `error_total` | 10+40+10+5 = 65 | 65.0 |
| `mae` | 65/4 = 16.25 | 16.25 |
| `wape` | 65/500 = 0.13 | 0.13 |
| `baseline_wape` | 240/500 = 0.48 | 0.48 |
| `coverage` | 3/4 = 0.75 (point 2 has 200 < 210) | 0.75 |
| `mean_width` | (30+50+50+20)/4 = 37.5 | 37.5 |
| `mean_interval_score` | (30 + [50+10x10] + 50 + 20)/4 = 62.5 | 62.5 |
| `relative_interval_width` | 37.5/125 = 0.3 | 0.3 |
| `daypart=morning_peak` | 2 samples, wape 20/250 = 0.08, score 40 | same |
| `daypart=evening_peak` | 1 sample, wape 40/200 = 0.2, score 150 | same |
| `daypart=offpeak` | 1 sample, wape 5/50 = 0.1, score 20 | same |

The one place the code and the paper disagree is float noise in `2/alpha`, which is
`10.000000000000002`: `interval_score([210,260], 300)` is `450.00000000000006`, not
`450.0`. That single assertion uses `pytest.approx` and says why; every other number
above compares exactly.

### A bad required slice against a passing mean

48 perfect off-peak points and 12 catastrophic evening-peak points, four folds, one
route. Overall WAPE 0.18 is inside `MAX_WAPE = 0.40`; the verdict is still a failure and
it names the slice:

```
overall: wape=0.18 samples=60 folds=4 status=evaluated (MAX_WAPE=0.4)
passed=False
FAIL: 2 breached, 0 unproven
daypart=evening_peak: wape 0.9 ratio exceeds 0.4 (MAX_WAPE=0.4) on 12 samples across 4 folds
route_daypart=route-A|evening_peak: wape 0.9 ratio exceeds 0.4 (MAX_WAPE=0.4) on 12 samples across 4 folds
```

`test_the_same_slice_fails_whether_or_not_anyone_declared_it_required` asserts the same
failure set with and without the `required=` declaration, so the mechanism does not
depend on anybody remembering to list the slice.

### A trivially wide interval beside a tight one

Twelve points, demand 100, both intervals at level 0.8:

```
tight: coverage=1.0 mean_width=20.0    mean_interval_score=20.0    relative_width=0.2   passed=True
giant: coverage=1.0 mean_width=10000.0 mean_interval_score=10000.0 relative_width=100.0 passed=False
```

Coverage is identical and says nothing. The failure line is
`mean_interval_score 10000 event_count exceeds 200 (MAX_INTERVAL_SCORE_TO_MEAN_ACTUAL=2)`.
`test_the_golden_gate_passes_an_interval_the_slice_report_rejects` runs the same interval
through `evaluate()`, which returns `passed: true` and `interval_coverage: 1.0`.

### Small sample, zero demand, overload absence

```
tiny:    samples=3 folds=3 wape=0.9 status=insufficient_samples
         reason: 3 sample(s) is below MIN_SAMPLES_FOR_GATE=12; reported in full and excluded from the gate
         failures=0 passed=False
route-Z: samples=12 actual_total=0.0 mae=5.0 wape=None status=insufficient_signal
overload on counts: None | target 'synthetic_boardings' is not an occupancy; a fraction
                    of capacity is defined only for 'onboard_load'
```

The three-sample slice keeps its WAPE of 0.9 and its support, gates on nothing, and the
report still does not pass, because `overall` is required and is itself unproven. The
zero-demand slice reports `null`, not `0.0`, and
`test_zero_demand_raises_the_pooled_ratio_it_cannot_flatter_it` asserts the pooled WAPE
rises from 0.0 to 0.0125 when it is added — its errors reach the numerator and nothing
reaches the denominator.

### Determinism

```
bytes equal: True; length 5993; digest 38ae081d615bc7c8fcb58756b9b8d6a33852b927b075dba4005023f92cad3006
```

Two reports over the same 60 points, the second from a `random.Random(11)`-shuffled list,
encoded with `features.records.encode` (sorted keys, no NaN). The payload contains no
`2026-` timestamp and no `/home` path.

### Known limits of this evidence

- Every number above is from arrays written by hand to exercise the mechanism. None of
  it is evidence about forecast quality, and no threshold here has been agreed.
- A slice failure is reported once per axis the points fall in, so a single bad group of
  points produces up to eight failure lines saying the same thing from different views.
  That is honest but verbose; a real report over many entities will not collapse this way.
- `MAX_INTERVAL_SCORE_TO_MEAN_ACTUAL = 2.0` was derived from the calibrated-normal case
  (mean score ~3.5 sigma against a mean demand of whatever the series carries) and is the
  least defensible constant of the six on real data, because a genuinely noisy slice
  legitimately needs wide intervals.
- The peak-hour windows 07-09 and 17-19 are asserted, not measured. Moscow tram peaks
  have not been checked against any data here.

### Recovery

The `slices/` package has no consumer in the running system: the backend never imports
`tramflow_ml`, and `cli.py` is untouched, so `make ml-eval` cannot change behaviour
whether the commits stand or are reverted. Reverting the commits removes the package,
its tests, the `evaluation.py` bridge function and the README section, and leaves every
other area untouched.
