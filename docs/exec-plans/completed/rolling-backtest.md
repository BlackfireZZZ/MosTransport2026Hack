# TASK-020: history-aware rolling-origin backtesting

## Purpose and observable result

Turn the leakage-safe feature layer of TASK-019 into a *fold index*: a chronological,
reproducible set of rolling forecast origins that a candidate and a baseline are scored
on, plus an experiment manifest that identifies exactly what ran.

Observable result: `run_backtest` returns an outcome whose `manifest_hash` is
byte-identical across two runs on the same config and the same data; whose folds are
non-overlapping and strictly ordered in time; whose every fold carries a complete
horizon of labels; and which reports an explicit non-passing status, naming the horizon
and the required and eligible origin counts, when the data cannot supply enough folds.
Appending or perturbing events after a fold's origin must not move a single byte of that
fold's training view or of its test feature values.

Acceptance, from the tracker card:

1. No overlap, no leakage.
2. Year evaluation requires a complete future year and a minimum number of eligible
   origins.
3. Insufficient history returns an explicit non-passing state.
4. Fold, config and version hashes are reproducible.

## Context

Base `c34e7d9`; worktree `MosTransport2026Hack-worktrees/rolling-backtest`, branch
`agent/rolling-backtest`. Owned files: `ml/src/tramflow_ml/backtest/`,
`ml/tests/test_backtest_*.py`, this plan, and one `## Rolling-origin backtesting`
section appended at the end of `ml/README.md`.

Not edited, by ownership or by constraint: `contracts/**`, `backend/**`, `frontend/**`,
`ml/src/tramflow_ml/{ingestion,identity,features}/**`,
`ml/src/tramflow_ml/synthetic.py`, `ml/src/tramflow_ml/cli.py`,
`ml/src/tramflow_ml/evaluation.py`, `docs/agentic/TASK_TRACKER.md`. A second agent owns
`cli.py` and `intake/` for TASK-039 in a parallel worktree, so this package exposes a
Python API only; CLI and pipeline wiring belong to TASK-058.

`ml/src/tramflow_ml/evaluation.py` is deliberately untouched. It backs the `make ml-eval`
golden gate and its `ForecastCase` shape (three fixed horizons, a baseline series and an
interval per case) is a *report* contract, not a fold contract. Widening it to carry
folds would change the gate's input schema for a task that does not need it. This package
is built beside it and reuses its WAPE definition; a test pins the two definitions
together by comparing against `evaluate()` on the same series, so the duplication cannot
drift silently.

Upstream contracts this layer consumes:

- `tramflow_ml.features.HorizonPolicy` — the three policies, their lags, windows,
  seasons and `cutoff_lead_buckets`, and `policy.cutoff(origin)`, the single definition
  of the availability cutoff.
- `tramflow_ml.features.build_features` / `FeatureRequest` — the only way a feature row
  is produced. The backtest never computes a feature value itself.
- `tramflow_ml.features.periods.step` / `horizon_buckets` / `validate_origin` — real
  calendar arithmetic in `Europe/Moscow`.
- `tramflow_ml.features.CoverageCalendar` — the explicit statement of which civil dates
  the source covers and when each arrived. This is the layer's only source of truth
  about what data exists; it is never inferred from the event rows.
- `contracts/calendar_v1.forecast_buckets` and `contracts/forecast_v1.ForecastArtifact`
  as test oracles only, reached with the existing
  `ROOT = Path(__file__).parents[2]; sys.path.insert(0, str(ROOT))` idiom. Production
  code in `ml/src/` never imports `contracts`; the existing test that asserts this
  covers the new package too, because it scans the whole source tree.

Terms. *Origin* `O` is the instant a forecast is made from; the horizon starts there.
*Cutoff* `C` is the instant after which no information may enter a feature of that fold.
*Embargo* `E` is the number of buckets by which `C` is moved earlier than `O`. *Period*
is one whole horizon length — 24 elapsed hours, one calendar month, twelve calendar
months. *Fold* is one origin together with its train, validation and test windows.
*Eligible* means the fold satisfies every rule and may be scored; an ineligible origin is
not a fold with holes, it is not a fold.

## Scope and non-goals

In scope: period arithmetic for the three horizons, candidate-origin enumeration, the
eligibility rules and their named refusal reasons, the fold set and its hash, the
embargo, a runner that hands one precomputed fold set to every model, a cutoff-restricted
data view a model cannot see past, per-fold MAE and WAPE over observed labels, and a
deterministic experiment manifest.

Out of scope: any model (TASK-021, TASK-023), the operational slice and interval report
(TASK-022), calibration (TASK-024), a CLI subcommand or pipeline wiring (TASK-058, and
`cli.py` is another agent's file this sprint), and any change to the golden evaluation
gate. No new dependency: pure standard library.

## Acceptance

- Two `run_backtest` calls with the same config and the same observations produce
  identical `config_hash`, `fold_hash`, `data_hash` and `manifest_hash`. Nothing hashed
  reads the wall clock, a filesystem path, or a set or dict iteration order.
- `build_fold_set` computes the fold set once. `run_backtest` accepts models and hands
  each of them the same `FoldSet` object; no code path recomputes folds per model. Two
  models record the same fold ids and the same test row keys.
- A candidate origin whose horizon ends after the end of the data span is reported
  `horizon_beyond_data`, never truncated. A horizon containing a bucket with no label at
  all is `incomplete_labels`. A horizon whose covered civil-date ratio is below
  `minimum_label_unit_ratio` is `diluted_labels`. An origin with less than the required
  train history is `insufficient_train_history`. Every refusal names the origin and the
  reason.
- When eligible origins are fewer than `minimum_origins`, the outcome status is
  `insufficient_history`, `passed` is `False`, and the reason names the horizon, the
  required count and the eligible count. A run that evaluated zero folds can never
  report `passed=True`.
- Appending events after a fold's horizon end leaves that fold's entire encoded result
  byte-identical. Appending or perturbing events after the origin but inside the horizon
  leaves the fold's train view and every test *feature* value byte-identical while the
  labels legitimately move.
- Behaviour that must not change: `evaluation.py`, `make ml-eval`, the CLI, `features`,
  `ingestion`, `identity`, `synthetic`, and every existing test.

## Progress and decisions

### 1. The cutoff is the feature layer's cutoff, never a second implementation

A fold's cutoff is `C = policy.cutoff(O)` moved back by the embargo, and the embargo is
applied by deriving an *effective policy*
`replace(policy, cutoff_lead_buckets=policy.cutoff_lead_buckets + E)`. That effective
policy is what the fold hands to `FeatureRequest`, so `build_features` enforces the
cutoff with exactly the code TASK-019 tested. There is no second expression of
`event_at < C and available_at <= C` and no second expression of "a history bucket is
usable only when `bucket_end <= C`" in this package, so the two cannot drift apart.

`HorizonPolicy` is a frozen dataclass whose `__post_init__` revalidates, so `replace`
returns a new, validated policy and mutates nothing.

### 2. Period arithmetic, reusing `periods.step`

One horizon period is expressed as a whole number of buckets in a granularity the
feature layer already steps correctly:

| Horizon | Period step | Buckets per horizon |
|---|---|---|
| `day` | 24 × `hourly` | 24 |
| `month` | 1 × `monthly` | 28–31 daily |
| `year` | 12 × `monthly` | 12 monthly |

`horizon_end(O) = period_step(O, horizon, +1)`, and a test asserts it equals
`horizon_buckets(O, horizon)[-1].end` and `contracts.calendar_v1.forecast_buckets(O,
horizon)[-1][1]` for a leap February, a 31-day month, a 12-month year and a Moscow DST
day. The `day` period is 24 *elapsed* hours because that is what `calendar_v1` says a day
horizon is; on 2011-03-27 that is not the next Moscow midnight, and the test pins it.

Nothing approximates a month as 30 days or a year as 365.

### 3. Candidate origins tile the data span; folds do not overlap

Candidate origins are period-aligned: Moscow midnight of a civil date for `day`, the
first of a month at midnight for `month`, January 1 at midnight for `year`. That
satisfies `validate_origin` for all three horizons and tiles the span. Consecutive
candidates are `origin_stride` periods apart, default 1, so by construction the test
windows of successive folds are contiguous half-open intervals that never overlap. A
test asserts pairwise disjointness of the test windows and strict ordering of the
origins.

Origins are enumerated forward from the first period boundary at or after the start of
the data span, so the enumeration does not depend on how many origins turn out to be
eligible.

### 4. Eligibility rules, and what "not a fold" means

An origin becomes a fold only when all of these hold. The first failing rule, in this
order, is recorded as the refusal reason:

1. `horizon_beyond_data` — `horizon_end(O)` must be at or before the end of the data
   span, where the span ends at Moscow midnight after the last covered civil date. A
   horizon running past the data is not a fold with missing labels; it is not a fold.
   This is the rule that makes "a year fold needs a complete future year" true.
2. `incomplete_labels` — every bucket of the horizon must carry a label. A bucket with no
   available civil date is `missing`, and a horizon with a hole in it cannot be scored
   against truth that is not there.
3. `diluted_labels` — the covered civil dates of the horizon, divided by its total civil
   dates, must be at least `minimum_label_unit_ratio`. Rule 2 alone would accept a
   monthly label bucket built from one day out of 31, because that bucket is `observed`;
   the ratio is the same `*_units` discipline the feature layer carries into the feature
   vector, applied to the labels.
4. `insufficient_train_history` — the number of buckets between the start of the data
   span and the cutoff must be at least `minimum_train_buckets`.

The eligibility decision for every candidate origin, eligible or not, is recorded in the
fold set and reaches the manifest. A refusal that is not reported is indistinguishable
from an origin that was never considered.

### 5. Insufficient history is a status, not an exception and not an empty pass

`run_backtest` returns a `BacktestOutcome` whose `status` is `evaluated` or
`insufficient_history` and whose `passed` is `status == "evaluated"` for every horizon.
The reason string names the horizon, the required origin count and the eligible count.
The card says the run *returns* an explicit non-passing state, so this is a return value
and not a raised exception; a raise would be lost by any caller that catches broadly,
and the manifest of a refused run is itself evidence worth keeping.

The failure mode being defended against is the opposite one: a run that evaluates zero
folds and reports success. `HorizonOutcome.__post_init__` refuses to construct an
`evaluated` outcome with fewer folds than `minimum_origins`, so `passed=True` with no
folds is unconstructible rather than merely untested.

### 6. Minimum origins defaults to 3

Rationale. One fold measures a single draw and cannot distinguish a candidate that beats
the baseline from a candidate that beat it once. Two folds can disagree but cannot show
which way. Three is the smallest number of chronologically separated origins at which
"the candidate is better on every slice" is a statement about behaviour rather than about
luck, and `AGENTS.md` already requires a new model to improve "agreed metrics across
multiple temporal slices". It is configurable per horizon because the year horizon will
almost certainly not reach it on organizer data — which is precisely the situation the
non-passing state exists to report rather than to paper over.

### 7. Minimum train history defaults to the policy's own look-back

`minimum_train_buckets` defaults to `max(max(lags), max(rolling_windows),
season_step × season_periods)` buckets of the policy. That is not a magic number: it is
exactly the history the feature layer needs before every declared column can be
non-missing, computed from the policy rather than restated. An explicit integer overrides
it, and the effective value is what reaches the config hash.

### 8. The embargo defaults to 0 buckets, and this needs stating plainly

The embargo exists to stop information crossing the train/test boundary through a channel
the cutoff does not see. In this pipeline there is no such channel:

- Labels are per-bucket event counts with no smoothing, no centred window and no
  interpolation, so a label of a test bucket is a function of that bucket alone.
- Features are already clipped at `C`, and a history bucket is used only when
  `bucket_end <= C`, so a bucket straddling the boundary is missing rather than partial.
- Late publication — the real reason a naive cutoff leaks — is already modelled twice and
  more precisely than an embargo could: by `HorizonPolicy.cutoff_lead_buckets` and by the
  coverage calendar's per-date publication instants.

A nonzero default would therefore discard a bucket of genuinely available information at
every origin, making every model look worse than it is in production and making the
backtest less faithful, in exchange for guarding a channel that does not exist here. So
the default is 0, the knob is present and reaches the config hash, and the condition for
raising it is recorded: raise it as soon as a target is defined over a window rather than
a bucket, or as soon as an organizer source is found to revise already-published dates.

This is the one default in this plan where a reviewer could reasonably choose otherwise;
it is called out in the handoff for that reason rather than buried here.

### 9. Train, validation and test are whole periods separated by the embargo

For origin `O`, horizon length one period, embargo `E` buckets:

- `test = [O, horizon_end(O))` — the horizon buckets.
- `C = policy.cutoff(O)` moved back `E` buckets.
- `validation_end` is the latest period boundary at or before `C`, found by walking back
  from `O` in whole periods. `validation = [period_step(validation_end, -k), validation_end)`
  for `k = validation_periods`, default 1.
- `train = [span_start, step(validation_start, granularity, -E))`.

Validation windows are whole periods so that the model-selection task has the same shape
as the test task; with `E = 0` the windows are contiguous and nothing is wasted. With
`E > 0` a partial period is dropped rather than shortened, because a shortened validation
window would be a different task from the test one.

Ordering `train_end <= validation_start < validation_end <= C <= O < test_end` is asserted
in `Fold.__post_init__`, so a fold with an overlap cannot be constructed.

### 10. Shared folds are structural, not conventional

`build_fold_set` is the only producer of a `FoldSet`. `run_backtest` takes models and a
fold set, iterates folds in the outer loop and models in the inner loop, and passes each
model the same `Fold` and the same `FoldData`. A model receives no observations, no
coverage calendar and no origin it could build a fold from: `FoldData` exposes only the
cutoff-visible observations, the `as_of(C)` coverage view and the test feature table,
and every one of those was produced once per fold before any model was called. A model
that wanted to leak would have to be handed data it is never handed.

### 11. Labels are separated from features, as in TASK-019

`FeatureTable.feature_digest` covers the model-visible part only; `digest` covers the
labels too. `FoldData.test_features` hands the model the feature rows; the labels stay in
the fold result and are compared with predictions by the runner. So a model physically
cannot read the label of the bucket it is predicting.

### 12. Hashes

Four hashes, all SHA-256 over canonical JSON (sorted keys, compact separators) using the
feature layer's `encode`:

- `config_hash` — the rules per horizon, including the resolved defaults, the target and
  unit, and every policy's full parameter tuple. Two configs that differ anywhere differ
  here.
- `data_hash` — the sorted observation tuples plus the sorted coverage dates and
  publication instants. Computed incrementally so a million rows do not have to be one
  JSON document. It answers "same data?" without which "same manifest" would be vacuous.
- `fold_hash` — the ordered fold descriptors and every refusal.
- `manifest_hash` — over the three above plus the versions and the results.

No wall clock, no path, no `generated_at`. A manifest that changed every run would
identify nothing.

### 13. Immutability and style

Every record is a frozen slotted dataclass or a `TypedDict`; mappings handed out are
`MappingProxyType`; inputs are never mutated. Functions stay under 50 lines and modules
under 400.

### 14. A day period is aligned to the hour, not to the civil day

This plan first said day origins were Moscow midnights. Checking the DST case before
writing the code showed that does not hold together. A `day` horizon under `calendar.v1`
covers 24 *elapsed* hours, so on 2011-03-27 — a 23-hour Moscow day — a horizon starting at
midnight ends at 01:00 the next day. Tiling by civil day would then make consecutive test
windows overlap by an hour, which the acceptance criterion forbids; tiling by 24 elapsed
hours keeps them exactly contiguous but lets origins drift off midnight after a
transition.

The tiling wins, because non-overlap is an acceptance criterion and midnight alignment is
not, and because "a day is 24 elapsed hours" is what the contract actually says —
`calendar_v1.forecast_buckets` accepts any exact Moscow hour as a day origin. So
`PERIOD_ALIGNMENT["day"]` is `"hourly"`. The cost is real and is recorded under open
risks: across a DST transition, day folds stop being service days, which would shift the
calendar features of every subsequent fold. Moscow has had no DST since 2014 and the
fixtures span 2024-2026, so this affects historical spans only. A test pins the behaviour
on 2011-03-27 rather than leaving it to be rediscovered.

### 15. A third non-passing state: `insufficient_signal`

Not in the brief, added because it closes the same hole from the other side. A horizon can
have plenty of eligible folds whose labels are all zero — a sparse entity, or a fixture
with no events in the test window. WAPE is undefined there, and `evaluation.py` raises
rather than invent a score. Raising would kill a whole run over one empty fold, so a fold
with no demand reports `wape=None` and the horizon reports `insufficient_signal` when
fewer than `minimum_origins` folds carry any demand. Without it, a run over an empty
dataset would have reported `passed=True` on folds that measured nothing — the same
failure the card's third acceptance criterion is about.

## Research evidence

No new algorithm. Rolling-origin evaluation with a purge/embargo gap is standard
time-series practice; the specific decisions here are all forced by contracts already in
this repository — `calendar_v1.forecast_buckets` for horizon boundaries,
`forecast_v1.ForecastArtifact` for the horizon → granularity mapping,
`data_v1.EventRow.visible_at` for availability, and `AGENTS.md` for chronological splits
and mandatory baselines. No internet research was performed, so nothing here is presented
as external evidence; where a default had to be chosen rather than derived (embargo,
minimum origins) the reasoning is written out above instead of being attributed.

## Validation and recovery

Plan, in order:

1. Hand-built unit fixtures per property: period arithmetic against `horizon_buckets` and
   `forecast_buckets` for a leap February, a 31-day month, a 12-month year and a Moscow
   DST day; candidate-origin enumeration; pairwise-disjoint test windows; the embargo
   moving the cutoff and the train/validation boundary; each of the four refusal reasons
   in isolation.
2. Future availability: an origin whose horizon ends one bucket past the data is refused,
   and the fold set does not contain a truncated horizon.
3. Leakage: build a fold set, then append events after the horizon end and assert the
   whole encoded result is unchanged; then perturb inside the horizon and assert the
   train view and every test feature value are unchanged while the labels move. A
   negative control moves an `available_at` across the cutoff and asserts the feature
   values *do* change, so the test cannot pass by ignoring its input.
4. Insufficient history: a span too short for `minimum_origins` returns
   `status="insufficient_history"`, `passed=False`, and a reason naming horizon, required
   and eligible; and a constructed zero-fold `evaluated` outcome is refused.
5. Shared folds: two models with different behaviour record identical fold ids and
   identical test row keys, and the fold set object handed to both is the same instance.
6. Determinism: two `run_backtest` calls give identical manifest hashes; a changed
   embargo, minimum, or observation set changes the corresponding hash.
7. Real path: `synthetic` → `ingestion` → `features` → folds, recording fold counts,
   origins and eligibility decisions for all three horizons.
8. `make ml-check`, `make ml-eval`, `make check`, `git diff --check`.

Baseline before any change, observed: `make check` exit 0; backend ruff clean, mypy 42
files, 292 passed / 10 skipped; ML ruff clean, mypy 32 files, 265 passed; golden
evaluation `"passed": true`; frontend 8 files / 47 tests, built in 614ms; reference
contracts mypy 3 files, 119 passed; `docker compose config --quiet` clean.

### Observed results

- `make ml-check`: exit 0. `ruff check ml` → "All checks passed!"; `mypy ml/src` →
  "Success: no issues found in 42 source files" (32 before, 10 added); `pytest ml/tests`
  → **381 passed in 26.59s** (116 new backtest tests; 265 pre-existing, unchanged).
  After the review batch: **409 passed in 43.76s** — 139 backtest tests (folds 41,
  history 21, availability 18, shared 15, manifest 14, leakage 14, fixtures 13, 3 more in
  `test_backtest_folds` unchanged) plus 4 new coverage-perturbation tests in the feature
  layer's own leakage suite.
- `make ml-eval`: exit 0, `"passed": true`, overall WAPE 0.0220 against baseline 0.1222,
  interval coverage 1.0 — byte-identical to the pre-change run, as expected from an
  untouched `evaluation.py`.
- `make check`: **exit 0**. Architecture boundaries passed; backend ruff clean, mypy 42
  files, **292 passed / 10 skipped in 16.01s**; ML ruff clean, mypy 42 files,
  **381 passed**; golden evaluation `"passed": true`; frontend **8 files / 47 tests** and
  `built in 702ms`; OpenAPI snapshot current and generated TypeScript current; reference
  contracts ruff clean, mypy 3 files, **119 passed**; `docker compose config --quiet`
  clean.
- Baseline for comparison, run before any edit: `make check` exit 0, ML mypy 32 files,
  265 passed; every other number above unchanged.

Fold index on the real path, `synthetic` → `ingestion` → `features` → folds, 12 entities,
default rules (embargo 0, minimum origins 3, minimum label ratio 1.0, look-back 168h /
364d / 36m):

| Fixture | Horizon | Eligible | Refused, by reason | First … last origin |
|---|---|---|---|---|
| default `SyntheticConfig()`: 2024-01-01…2026-01-01, 64 unique validations, 56 gap dates | day | 667 | `incomplete_labels` 56, `insufficient_train_history` 8 | 2024-01-09 … 2025-12-31 |
| | month | 0 | `incomplete_labels` 24 | — |
| | year | 0 | `diluted_labels` 2 (338/366 = 0.9235; 337/365 = 0.9233) | — |
| gapless: `gap_every_days=0, events=2000`, same span | day | 723 | `insufficient_train_history` 8 | 2024-01-09 … 2025-12-31 |
| | month | 11 | `insufficient_train_history` 13 | 2025-02-01 … 2025-12-01 |
| | year | 0 | `insufficient_train_history` 2 | — |
| gapless 8-year: `events=20000`, 2018-01-01…2026-01-01 | day | 2 914 | `insufficient_train_history` 8 | 2018-01-09 … 2025-12-31 |
| | month | 83 | `insufficient_train_history` 13 | 2019-02-01 … 2025-12-01 |
| | year | 4 | `insufficient_train_history` 4 | 2022-01-01 … 2025-01-01 |

Observed refusal text, verbatim, on the two-year gapless fixture:

```
year: 0 eligible origins, 3 required; 2 candidate origins refused
(insufficient_train_history=2); no fold was scored
```

and on the gapped fixture, `(diluted_labels=2)` and `(incomplete_labels=24)` respectively.
Both runs return `status="insufficient_history"`, `passed=False`, `scored=0`,
`wape=None` for every model.

Determinism, two `run_backtest` calls per row plus, for the gapped fixture, a build from a
second independent ingestion of the same source. Every row was scored by `zero@0.1.0`
then `constant-one@0.1.0`, in that order: `manifest_hash` covers the model names and
versions, so a published value without its model set cannot be reproduced. The first
version of this table omitted it, which both checkers caught.

| Fixture / horizon | `config_hash` | `fold_hash` | `manifest_hash` (both runs) |
|---|---|---|---|
| gapped, month | `da8ffcae72422a69…` | `a80efc226688b4c4…` | `d74bc3a7238f0e0e97c089ea218e6aef720e7e63c12435afe2b6fa6e548f8775` |
| gapped, year | `89e1be3ee4605ae4…` | `a29495ab648a7d7c…` | `40eb72abb5878c85b23019f5400da9145bdd602d38cc1e8218dafcb82973b42e` |
| gapless 2y, month | `da8ffcae72422a69…` | `755ca80bd8af1e72…` | `21a3b973a5ee94eeea49c0a3eaca2dd73884e8f349d96d79b0e18292655797f9` |
| gapless 2y, year | `89e1be3ee4605ae4…` | `6e1cf66e370d01f6…` | `75d72874b4d90c8bed53457233f54f90f4a95d594c5973d3c082921d215ebb44` |
| gapless 8y, month | `da8ffcae72422a69…` | `96ae9be3f8bb0710…` | `cacff4e0121322bda1df8c08994f1a9e2b3f5c84434d34e948175707f21fe28a` |
| gapless 8y, year | `89e1be3ee4605ae4…` | `553c1f5378dcc021…` | `51ac6a3dbb9ca73857f4d32038a65661ad68cb24bff467448aed1900ff509a74` |

`data_hash` agreed across the two independent ingestion runs of the gapped fixture
(`beef6cab5201b8a1993521de829cd93bea34b812e8cc2e6bd75a46f2ef45d3f8`) and across repeats
of the gapless ones (`bc572e95e28d5234…`, `8b66caa2e3e611dd…`). The `config_hash` is
identical across fixtures for the same rules and differs between month and year rules,
which is what it is for. Reversing the input event order leaves `data_hash` and every
downstream hash unchanged. `test_backtest_fixtures.py` now pins the gapless-2y month row —
all four hashes plus the model list — so the published numbers cannot go stale in silence.

Scoring sanity, gapless 8-year, 83 month folds and 4 year folds, a constant-zero model
against a constant-one model on identical folds: both score the same 30 312 (month) and
576 (year) rows against the same `actual_total` (17 288 and 9 997); the zero model's WAPE
is exactly 1.0 in both, which it must be, and the constant-one model's differs (0.9612 and
0.9424). Same folds, different answers, different errors.

Leakage, on a hand-built month fold at origin 2025-06-01 over 2023-2026: appending 40
post-horizon events leaves `feature_digest`, all 60 encoded test feature rows and both
observation partitions byte-identical; appending 20 events inside the horizon leaves all
of those byte-identical while `actual_total` rises. The negative control does fire —
moving one event's `available_at` from 2025-05-31T09:01 to 2025-06-02 changes
`feature_digest` (`e73ae507…` → `a5583aba…`) and removes that event from the validation
partition. An embargo of 7 daily buckets moves the cutoff to 2025-05-25, changes the
feature digest and shrinks the train partition.

One test defect was found and corrected on first run, with no change to the
implementation: the leakage negative control asserted the moved event left
`train_observations`, but a 2025-05-31 event belongs to the *validation* window
`[2025-05-01, 2025-06-01)`, not to train `[2023-01-01, 2025-05-01)`. The assertion now
names the validation partition, which is the sharper statement anyway. Two further test
defects were mine and not the code's: `dataclasses.replace(observation, event_at=+1h)`
broke the `available_at >= event_at` invariant the feature layer enforces, and shortening
a coverage calendar without shortening the events made `aggregate` refuse a date it did
not cover — both correct refusals.

## Review record (2026-09-25)

Independent acceptance validation ACCEPT — all five criteria met by reproduction: test
windows enumerated pairwise over a ten-year coverage (day 3645 folds, month 107, year 6)
with **zero** overlapping pairs and zero ordering violations; 23 month folds audited row
by row for anything handed to a model with `event_at >= cutoff` or `available_at > cutoff`,
**zero** found; every fold count, origin range, refusal breakdown, status string and the
`config_hash`/`fold_hash`/`data_hash` families reproduced exactly.

Independent review ACCEPT WITH FINDINGS. The reviewer built its own negative controls and
all of them fired, so the leakage suite is not passing vacuously. It independently
endorsed two judgement calls rather than overruling them: the day-period alignment (it
confirmed `calendar_v1` says a day horizon "accepts any exact Moscow hour and covers 24
elapsed hours", so civil-day tiling is not available at all and the trade recorded in
decision 14 is the only one consistent with the contract), and the embargo default of 0
(it checked every premise in decision 8 against the code). `insufficient_signal` was
judged correct and kept.

| Severity | Finding | Fix |
|---|---|---|
| HIGH | `insufficient_train_history` compared a pure calendar distance against the requirement, so coverage holes inside the train window were invisible. Reproduced: coverage `{2023-01-01} ∪ {2025-04-30…2025-12-31}` (247 of 1096 dates) gave 8 eligible month folds, `month@2025-05-01` with `train_buckets=821` and **one** covered train day, `status="evaluated"`, `passed=True` — every lag, window and season `None` and the run reporting success. A false pass on the axis acceptance criterion 3 exists to guard, through a different door than a short span | Covered buckets are now counted with the same `CoverageView.units` machinery `_label_refusal` uses, and the calendar distance is kept only as a cheap pre-filter. The grid is walked once per horizon into a prefix-count array and every window answered by two bisections, so the per-fold cost stays constant. `Fold` carries `train_covered_buckets`, which reaches the fold hash. The reproduction is now a test asserting the exact refusal `1 of 821 train buckets are covered, 364 required` |
| HIGH | TASK-019 defect surfacing here, fixed under an explicit lift of the `features/` restriction: `unit_counts` was not gated by `ends_by(cutoff)` unlike `available_value`, and `CoverageView.available()` answers `True` for any covered date when the calendar carries no `published_at`, so a bucket after the cutoff answered truthfully about the future through the `*_units` columns | `unit_counts` takes the cutoff and returns `(0, total)` for a bucket that has not finished; the total is a pure calendar fact and leaks nothing. Committed separately as `6f28a04` so it can be recorded against TASK-019. A coverage-calendar perturbation was added to `ml/tests/test_features_leakage.py`, which is where the axis was missing — that suite perturbs events, and this is a perturbation of the coverage statement — and a `YEAR_MONTH` case to `test_backtest_leakage.py`, since `carries_unit_ratio` is monthly-only and `MONTH_DAY` never exercises those columns |
| HIGH | `FoldData.test_features` rows and their nested `features` mapping were plain mutable dicts, and the runner hands one `FoldData` to every model by design, so the first model could rewrite the second's input silently — defeating the branch's headline claim, with `test_backtest_shared.py`'s object-identity proof making the mutation contagious | Both levels wrapped in `MappingProxyType`. A `Vandal` model now attempts `row["route_id"] = "HACKED"` and `row["features"]["lag_1d"] = 999999.0` on every fold, counts the refusals, and a recorder scored after it confirms it saw pristine rows |
| MEDIUM | Six published `manifest_hash` values did not reproduce, found by both checkers independently. Everything else in those rows reproduced byte for byte; the validator localised the cause instead of guessing, brute-forcing 2016 model-identity combinations against the two zero-fold rows with zero hits. `manifest_hash` covers the model names and versions and the evidence never recorded which models ran | Re-run and corrected above, with the model set (`zero@0.1.0` then `constant-one@0.1.0`) recorded alongside. `test_backtest_fixtures.py` pins the gapless-2y month row — `config_hash`, `data_hash`, `fold_hash`, `manifest_hash` and the model list — and a second test asserts that swapping the two models leaves `fold_hash` alone and moves `manifest_hash` |
| MEDIUM | `FoldData`'s docstring and the README both claimed a model "never receives the observation set, the coverage calendar or the origin". False: a `CoverageView` carries its whole `CoverageCalendar` (1096 dates reachable), and `fold.origin` plus `label_covered_units`/`label_total_units` were `predict` arguments. Not a target leak, but with `minimum_label_unit_ratio < 1.0` the label-unit counts state how much of the horizon the source covers | Both claims corrected, and both alternatives taken rather than one: `FoldData` no longer carries any coverage object at all — coverage reaches a model only through the feature columns the feature layer clips — and `predict` receives a `FoldView`, a projection of `Fold` that leaves the label-unit counts behind. `Fold.view()` is the only constructor, so a field added to `Fold` does not reach a model until someone adds it there on purpose |
| MEDIUM | The plan and README claimed `fold_metrics` "reuses `evaluation.py`'s WAPE verbatim" and that a test "pins the two definitions together". They share no code and deliberately diverge on zero demand, and the pin was one hand-written case exercising neither the divergence nor cross-fold pooling | The claim is downgraded to what is true — semantically aligned on `Σ\|error\| / Σactual`, deliberately divergent on zero demand — and the pin strengthened: a test asserts the golden gate *raises* on zero demand where a fold reports `None`, and another asserts pooling two folds equals scoring their concatenation. Refactoring `evaluation.py` to share the summation was considered and rejected: it backs the `make ml-eval` gate and the divergence is intentional |
| LOW | `_validate_passing` never checked that `results` was non-empty or matched `eligible_origins`, so a hand-built `HorizonOutcome` could report `passed=True` with nothing scored — unreachable from `run_backtest`, but the docstring claimed unconstructible "by any code path" and the class is a public export | `_validate_scored` added; two tests construct both shapes and assert the refusal |
| LOW | `minimum_origins` gated both eligible origins and origins carrying demand, so raising it for more folds silently tightened an unrelated gate | `minimum_origins_with_demand` added, defaulting to `minimum_origins`, carried into the config hash and reported on the outcome as `required_origins_with_demand` |
| LOW | `config.py` accepted an `int` for `minimum_label_unit_ratio`, so `1` and `1.0` hashed differently for one configuration | Normalised with `float()` in `__post_init__`; a test asserts the two spellings hash alike |
| LOW | Speculative exports with no consumer | `PERIOD_STEP` and `FoldMetrics.has_demand` removed; `FoldModel` converted from a base class to a `Protocol`, so it now structurally checks a typed caller instead of merely documenting. `BacktestData.of` kept: it accepts iterables where the dataclass declares tuples and has seven call sites |

Two fold counts were checked for movement under the HIGH coverage fix and did not move:
the gapped fixture's 667 day folds still carry at least 168 covered hourly buckets each,
and its month and year candidates were already refused earlier in the rule order. The
gapless fixtures have no holes. Only `fold_hash` moved, because `train_covered_buckets`
joined the fold descriptor.

Two earlier hints from the lead were stale and the reviewer checked and dismissed them:
the `fold` bindings are `predict` interface parameters, and the `replace` import is used.

## Open risks

- **Day folds are not service days across a DST transition.** Decision 14 chose exact
  24-hour tiling over civil-day alignment. On a span containing a Moscow DST change the
  day origins drift off midnight and stay drifted, so `hour_of_day` and `is_weekend` no
  longer line up with the service day for every later fold. Moscow has had no DST since
  2014, so this is a historical-data risk only; if organizer data predates 2014 the fix is
  a per-horizon choice between tiling and alignment, and the overlap it reintroduces would
  have to be declared.
- **`minimum_train_buckets` makes the year horizon expensive.** The default is the
  policy's look-back, and `YEAR_MONTH` declares `seasonal_3x12m`, so a year fold needs 36
  monthly train buckets plus a year of validation plus a complete future year — five years
  of coverage before the first fold exists. That is honest about what the features need,
  but it means the number of viable real yearly folds is a property of the organizer's
  coverage, and the card's pre-data risk stands: we still do not know it. The knob to relax
  is `minimum_train_buckets`, and doing so must be a recorded decision because it changes
  the config hash.
- **`minimum_label_unit_ratio = 1.0` is strict on real data.** The default refuses a
  horizon with any uncovered civil date. On the gapped fixture that removes every month
  and year fold. Real organizer coverage will have holes; lowering the ratio is the
  intended response, and the `diluted_labels` refusal already reports the exact figure to
  lower it to. What must not happen is lowering it silently — it is in the config hash.
- **Per-fold observation filtering is O(n) per fold.** `_partition` walks the whole
  observation set for every fold. On 2 914 day folds over a million rows that is billions
  of comparisons. The fixtures here are small and the work is offline, but a real day-horizon
  backtest will need a per-bucket index before it is usable. No consumer needs it yet
  (TASK-021 is the first), so it is not built.
- **`data_hash` sorts every encoded observation in memory.** Roughly 150 bytes a row, so a
  million-row dataset holds ~150 MB transiently. Correct and simple; an order-independent
  streaming fold would remove it if a larger dataset arrives.
- **`passed` is about folds, not quality.** A caller reading `outcome.passed` as "the
  candidate is good" would be wrong, and nothing in the type system stops them. The README
  says so twice; TASK-022 owns the quality verdict.
- **The covered-bucket prefix array is built per horizon over the whole span.** Hourly
  granularity over ten years is ~87 600 entries, walked once. Bounded and fine for any
  realistic offline span, but it is memory proportional to span × granularity, and a
  much longer hourly history would want the date-interval form instead.
- **A documented TASK-019 digest moved.** `year/month` is now
  `58e57f490b3315b195dc3b480bc5b14dea44c390f796256b1388b9680db30156`, superseding
  `408d45807ce37fe661b2edb3e888e5afae19cc015cb093c6f485a7f687ab8445`, and its
  `feature_digest` `fb7bf53b…` supersedes `3e8a211c…`. `day/hour` and `month/day` are
  unchanged. The values in `ml/README.md`, `docs/exec-plans/completed/horizon-features.md`
  and the TASK-019 tracker entry are deliberately **not** rewritten here — that is the
  lead's record against TASK-019. TD-001 already notes that no test pins them, which is
  why nothing failed; pinning them would have caught this.

Recovery: the package has no consumer yet, so reverting the commits removes it cleanly
and no other area changes behaviour. `evaluation.py`, `cli.py` and every other package are
untouched, so `make ml-eval` and the golden gate cannot be affected by a revert either.
