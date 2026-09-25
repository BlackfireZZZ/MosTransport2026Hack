# TramFlow ML

Authoritative product requirements: [../docs/product/TASK.md](../docs/product/TASK.md). Prioritize tram passenger-flow forecasts for day/month/year, route/stop/time aggregation, and an updating Moscow map. OD, multimodal modeling, and what-if are optional team extensions.

Изолированное `uv`-окружение для offline-подготовки признаков, обучения и backtesting. Оно намеренно не импортируется backend-процессом.

```bash
make sync-ml
make dev-ml
make ml-check
```

Перед добавлением модели зафиксируйте dataset version, временные split-границы, baseline, метрики и model card. Публикация результата в serving tables должна быть отдельным атомарным шагом.

Golden evaluation проверяет, что кандидат превосходит наивный baseline на каждом
горизонте и сохраняет согласованное покрытие интервалов:

```bash
uv run --package tramflow-ml tramflow-ml evaluate
```

## Synthetic fixtures

`generate-synthetic` writes deterministic validation/telemetry fixtures for testing
ingestion, aggregation and evaluation mechanics. They are synthetic boarding-event
counts, never observed Moscow demand or occupancy. Keep large outputs outside git.

```bash
uv run --package tramflow-ml tramflow-ml generate-synthetic --output /tmp/synthetic-tiny
uv run --package tramflow-ml tramflow-ml generate-synthetic --mode million --output /tmp/synthetic-million
```

Output directory (must not exist beforehand): `entities.json`, `validations.jsonl`,
`telemetry.jsonl`, `generation.json`, then `manifest.json` last. A directory without
`manifest.json` (possibly with a stray `.manifest.json.tmp`) is a failed run kept
for diagnosis; consumers must require the manifest. `manifest.source_hash` is the SHA-256 of the inventory (name → SHA-256 and
byte size of the first four files); the manifest is not part of its own hash.
Same `--seed`, dates and injection periods produce byte-identical files; wall clock
and output path never influence content.

Count semantics (`generation.json` → `counts`; periods are one-based over unique events):

| Option | Default | Effect |
|---|---|---|
| `--events` / `--mode` | 64 tiny, 1 000 000 million | Number of unique validations `N`; `--events` overrides the mode. |
| `--duplicate-every d` | 17 | Every `d`-th unique event is written twice: `⌊N/d⌋` exact duplicate rows. `0` disables. |
| `--late-every l` | 11 | Every `l`-th event has `available_at` one day after `event_at`; otherwise one minute. `0` disables. |
| `--telemetry-every k` | 5 | Every `k`-th unique event emits one telemetry row. Must be `>= 1`. |
| `--gap-every-days g` | 13 | Every `g`-th calendar day in `[start, end)` has no source coverage and no events (`gap_dates`). `0` disables; `1` is rejected. |

`unique_validations` excludes duplicates. Events span the remaining covered dates
with both endpoints used when `N > 1`; a covered date with no events means observed
zero, a gap date means missing coverage. Timestamps are ISO-8601 with the
`Europe/Moscow` offset. `cell_totals` (route, direction, stop, date, hour) and
`hour_totals` sum to `N` for independent reconciliation. File order is event time,
not an availability guarantee.

## Historical ingestion

`ingest` normalizes a fixture directory (`entities.json`, `manifest.json`,
`validations.jsonl`, `telemetry.jsonl`; or `.csv` streams with `--format csv`)
into `data.v1` event rows in bounded, resumable chunks (TASK-017, RQ-01).

```bash
uv run --package tramflow-ml tramflow-ml ingest --input /tmp/synthetic-tiny --output /tmp/ingest-tiny
uv run --package tramflow-ml tramflow-ml ingest --input /tmp/synthetic-million --output /tmp/ingest-million --chunk-size 10000
```

Output directory: `validations.jsonl`, `telemetry.jsonl` (canonical JSON lines,
exactly the contract fields, timestamps re-emitted in `Europe/Moscow`),
`quarantine.jsonl` (`stream`, `row_index`, `reason`, `detail`, `raw`, plus
`raw_base64` only when the source line is not valid UTF-8), then
`manifest.json` (`ingestion.v1`) last. The manifest carries `normalization_version`,
the SHA-256 and byte size of every input, the propagated source manifest, per-stream
counts and an `output_hash`. Nothing in the outputs depends on wall clock or paths.

Counting contract per stream: `input_rows == valid + duplicates + quarantined`.
A repeated `event_id` with an identical normalized payload is a *duplicate* (first
kept, later ones counted); a repeated `event_id` with a different payload is
quarantined as `conflicting_duplicate`. The command exits 1 when the identity fails,
2 for input or usage errors. Reason codes: `decode_error`, `missing_field`,
`invalid_type`, `invalid_value`, `invalid_timestamp`, `availability_before_event`,
`unknown_entity`, `conflicting_duplicate`.

Restart: after every chunk the outputs are flushed, the SQLite `event_id` index is
committed and `checkpoint.json` is replaced atomically. Rerunning the same command
on a directory that holds `checkpoint.json` resumes from it and produces
byte-identical files; it refuses if any input hash, the normalization version, the
adapter, the format or the chunk size changed. The adapter is compared by name, so
editing a `ColumnAdapter` without renaming it is not detected; give a changed mapping
a new name. A checkpoint that is not valid `ingestion-checkpoint.v1` — a missing or
mistyped key, a missing stream — is refused as an input error (exit 2) instead of
being read as far as it parses. A directory with `manifest.json` is complete and is
never overwritten; a directory with unrelated files is refused. `checkpoint.json` and
`dedup.sqlite` are removed only after `manifest.json` is written, so a crash in that
last step leaves both behind next to a complete manifest; deleting them by hand is
safe and a rerun refuses the directory as already complete.
Memory is bounded by `--chunk-size` plus an 8 MiB SQLite cache, not by row count
(million-event run: 57 MB peak RSS, same as a 100 000-event run).

CSV sources need one record per physical line (quoted line breaks are unsupported
because resumption is by byte offset); strings are coerced to integers, booleans and
floats. A `ColumnAdapter` maps canonical field → source column, supplies constants
for absent columns and sets `timestamp_format` / `assume_timezone` for naive
timestamps. Only the built-in `synthetic` adapter is exposed on the CLI, so CSV
sources are reachable through the Python API (`ingest(IngestionConfig(..., source_format="csv",
adapter=...))`) and are covered by tests there, not through `tramflow-ml ingest`;
organizer adapters wait for real samples. A UTF-8 byte-order mark before the CSV
header is ignored.

## Identity alignment

`tramflow_ml.identity` joins source validation/telemetry rows to canonical catalog
ids through an explicit, versioned crosswalk and per-source clock rules. It is a
pure-Python API (CLI wiring is a later task) and never guesses: each row becomes an
`AlignedEvent` whose `match` is `Matched` (kind `exact_id`, `name_route_direction`
or `geo_nearest`), `Unmatched(reason)`, `Ambiguous(field, candidates)` or
`Stale(lag_seconds)`.

```python
from tramflow_ml.identity import (
    AlignmentConfig, CanonicalCatalog, SourceEvent, align_events, load_crosswalk, quality_report,
)

catalog = CanonicalCatalog.from_dict(entities_json)          # entities.json shape (data.v1)
crosswalk = load_crosswalk(crosswalk_json, catalog)          # unknown canonical ids raise
config = AlignmentConfig.from_dict({"clocks": {"validations": {"timezone": "UTC"}}})
aligned = align_events(catalog, crosswalk, config, source_events)
report = quality_report(crosswalk, aligned).to_dict()
```

Crosswalk payload: `crosswalk_version`, `entity_version` (must equal the catalog),
`routes`, `directions`, `stops` (source id → canonical id), `stop_names`
(`name` + `route_id` + `direction_id` → `stop_id`, for sources that only carry a
name), `stop_positions` (canonical stop → `latitude`/`longitude`) and `vehicles`
(half-open `[valid_from, valid_to)` route assignments, ISO-8601 with offset).

Rules that make the acceptance failure modes explicit:

| Situation | Outcome |
|---|---|
| Two stops share a name on the pattern and no qualified `stop_names` entry | `Ambiguous("stop", …)` |
| Direction missing or unknown | `Unmatched`; a direction is never inferred from the stop |
| Stop visited twice on a pattern without `stop_sequence` or `previous_stop_id` | `Ambiguous("stop_sequence", …)` |
| Vehicle assignment at event time disagrees with the source route | `Unmatched("vehicle_route_conflict")`; fires only when a covering assignment interval exists for the vehicle, so unassigned vehicles never veto and route/direction always come from the source row |
| GPS is the join key (no `stop_id`/`stop_name`) and `abs(fix_at - event_at)` exceeds `gps_staleness_seconds` | `Stale`, not joined; a fix newer than the event counts too. A row carrying `stop_id` joins `exact_id` regardless of `fix_at` |
| Naive timestamp falls in a DST gap or overlap of the source zone | `Unmatched("nonexistent_local_time")` / `Unmatched("ambiguous_local_time")`; `time` is `UnresolvedLocalTime`, no instant is guessed |
| Two pattern stops within `geo_tolerance_metres` | `Ambiguous`; none within → `Unmatched` |
| `available_at` missing and no `availability_lag_seconds` | `Unmatched("availability_missing")` |

Clock alignment: naive timestamps are read in the source `timezone` (a wall time
that names zero or two instants is rejected as above), then `offset_seconds` is
applied in UTC and the result is emitted in `Europe/Moscow`.
`AlignedTime` keeps both the source and adjusted `event_at`/`available_at` and sets
`service_day_shifted` when the offset moves the Moscow civil date. Source rows are
frozen and never mutated. The quality report lists streams by `source_id`; rates
exist per outcome (matched, unmatched, ambiguous, stale) and sum to one, while
match kinds and unmatched reasons are counts only. Dict output has sorted keys.

Thresholds and mappings are configuration: real organizer identifiers, name
conventions and GPS tolerances cannot be certified before samples arrive.

## Feature engineering

`tramflow_ml.features` turns ingested `data.v1` event rows into one feature table per
forecast horizon (TASK-019, RQ-01–03). It is a pure-Python API; CLI and pipeline wiring
belong to a later task. A table holds one row per `(route_id, direction_id, stop_id)`
entity and per calendar bucket of the horizon, plus a header naming the feature version,
the policy, the forecast origin and the availability cutoff that was applied.

```python
from tramflow_ml.features import (
    YEAR_MONTH, CoverageCalendar, FeatureRequest, build_features,
    load_entity_keys, load_observations,
)

observations = load_observations(ingest_dir / "validations.jsonl")
coverage = CoverageCalendar.from_range(date(2024, 1, 1), date(2026, 1, 1), gaps=gap_dates)
table = build_features(FeatureRequest(
    policy=YEAR_MONTH,
    origin=datetime(2025, 1, 1, tzinfo=MOSCOW),
    entities=load_entity_keys(fixture_dir / "entities.json"),
    observations=observations,
    coverage=coverage,
    target="synthetic_boardings",
    unit="event_count",
))
```

Bucket policy: the key is the entity plus a half-open `[bucket_start, bucket_end)`
interval in `Europe/Moscow`, and granularity follows the horizon exactly as
`ForecastArtifact` requires. Direction is part of the key and is never collapsed;
`stop_sequence` is not, so a stop visited twice on a loop aggregates into one cell.

| Policy | Horizon | Buckets | Lags | Rolling windows | Season |
|---|---|---|---|---|---|
| `day/hour` | one day | 24 hourly | 1, 2, 24, 48, 168 h | 24 h, 168 h | 4 × 24 h |
| `month/day` | one calendar month | 28–31 daily | 1, 7, 14, 364 d | 7 d, 28 d | 4 × 7 d |
| `year/month` | one calendar year | 12 monthly | 1, 2, 3, 12 m | 3 m, 12 m | 3 × 12 m |

Availability cutoff: each policy derives one cutoff `C` from the forecast origin
(`C = origin` unless `cutoff_lead_buckets` moves it earlier for a late-publishing
source). An event reaches a feature only when `event_at < C and available_at <= C` —
the `data.v1` rule, closed on availability and half-open on the event — and a history
bucket is used only when its `bucket_end <= C`, so a bucket still running at the cutoff
is missing rather than a partial sum. A lag that reaches into the horizon is therefore
explicitly missing: under `day/hour`, `lag_1h` exists only for the first target hour.
Rolling windows are anchored at the last bucket that has fully elapsed at `C`, not at
the target bucket, so every row of one horizon shares the past a forecaster actually
has and no anchor can reach forward. Labels (`target_value`) come from the full series
and are not features; the leakage guarantee covers `feature_digest`.

Coverage is cutoff-aware, not only event-aware. `CoverageCalendar` optionally records
the instant each civil date's data arrived; a date not yet published at `C` counts as
unavailable, so a bucket built only from such dates is `missing`. Without that, filtering
unpublished rows upstream would leave the bucket looking like a confident zero — a whole
day of real boardings reported as no demand. The same calendar is read through two
views: `as_of(C)` for history and `complete()` for labels, so an as-of history never
requires the caller to hand in a mutilated calendar. A date the calendar does not cover
at all is still an input defect and stops the run. The resolution of this mechanism is
one civil date: a source that delivers a date and then trickles individual rows into it
later still reads as an observed zero for the buckets those rows belong to, because the
date itself was stated as delivered. Per-row publication metadata would be needed to
close that, and no organizer format for it exists yet.

Missing convention: `None`, never `0.0`. An `AggregateCell` is `coverage="missing"`
with `value=None` exactly when no available date falls in the bucket, which is the
`ObservedAggregate` invariant, and both `AggregateCell` and `FeatureRow` enforce it on
construction rather than only describing it. A bucket whose dates are available but
carry no events is `coverage="observed"` with `value=0` — a real zero, distinct from
missing in the digest. A rolling window with no observation is `None` for sum, mean and
max with `coverage=0.0`; a capacity that is unknown, or known only after `C`, is `None`.

Partial coverage inside a bucket is carried in the feature vector, not only on the cell.
Each lag, rolling window and season of a policy whose buckets span more than one civil
date also emits a `*_units` ratio: the fraction of that bucket's (or window's) civil
dates that are available at `C`. A February with one covered day reports
`lag_12m_units ≈ 0.034` against `1.0` for a complete one, so a diluted month can no
longer read as a quiet one. Only `year/month` carries these columns: an hourly or daily
bucket is exactly one civil date, so the ratio there would be `1.0` whenever the value
exists and would repeat what the value already says. `covered_units`/`total_units` remain
on every `AggregateCell` regardless.

Calendar periods are real calendar arithmetic. Hour steps move whole UTC hours, day
steps move the civil date and recombine at Moscow midnight, month steps move
`year * 12 + month - 1`. Nothing approximates a month as 30 days or a year as 365:
February 2024 yields 29 daily buckets, 2024 yields 12 monthly buckets spanning 366
days, and `lag_12m` lands on the same calendar month a year earlier. `bucket_hours` is
measured on the instants, so the Moscow DST days 2011-03-27 and 2014-10-26 report 23
and 25 hours; Moscow has had no DST since 2014, but the arithmetic does not rely on it.
Timestamps are normalized to Moscow through UTC, because `astimezone` returns a value
unchanged when its `tzinfo` is already the target zone: a datetime merely *tagged*
`Europe/Moscow` can otherwise keep a wall time that names no instant, and two spellings
of one instant would disagree. The rule on midnights is stated rather than enumerated:
any civil date whose Moscow midnight is nonexistent or ambiguous is refused instead of
resolved to a guess, the same rule `identity/clock.py` applies to naive source times.
Which dates those are belongs to the tz database and changes with it — a sweep of
1900–2040 on the current database finds seven, not the four an earlier version of this
section named. Hourly bucketing is unaffected by such dates and needs no whole-hour
offset: it is done in UTC, and at a sub-hour historical offset (1918 Moscow ran at
+04:31:19) an hourly bucket start legitimately carries minutes and seconds. Where
`contracts/calendar_v1.forecast_buckets` would resolve such a midnight silently, this
layer refuses; a service day it cannot locate is an error, not a default.

Only counted targets are accepted: `synthetic_boardings` and `validation_count`, both
in `event_count`. An observation is one event with no magnitude, so a passenger-valued
target from `forecast_v1` is refused at the `FeatureRequest` and `aggregate` boundaries
rather than silently relabelling a row count as a passenger load.

Determinism: entities are sorted by `(route_id, direction_id, stop_id)`, buckets run
chronologically, feature names follow the policy's declared order, and
`FeatureTable.digest` is SHA-256 over canonical JSON of the whole table. Nothing reads
the wall clock, a filesystem path, or a set or dict iteration order; reversing the input
event order changes nothing. On the tiny synthetic fixture (64 unique validations, 12
entities), the hourly aggregate reproduces all 64 `cell_totals` entries of
`generation.json` cell for cell, and repeated builds — including from a second
independent ingestion run of the same fixture — give identical digests
(`7e412bb0…` for `day/hour`, `b3ad914c…` for `month/day`, `408d4580…` for `year/month`).
That fixture spans 2024–2026, where Moscow is a fixed +03:00, so it does not exercise
the DST-sensitive part of bucketing; that rests on the hand-written calendar tests.

Not certified before organizer data: the bucket policy, the lag sets, the rolling
windows, the seasons and the cutoff leads are the team proposal and are configuration.
Historical weather and event data are absent on purpose, because they are not available
at a forecast origin and therefore cannot be features; no placeholder column exists for
them. There is no holiday calendar — `is_weekend` is the civil weekday and is not a
holiday proxy. For real data the coverage calendar must come from the organizer's own
coverage statement, not from our row counts.

## Rolling-origin backtesting

`tramflow_ml.backtest` turns the feature layer into a *fold index*: a chronological set
of rolling forecast origins that a candidate and a baseline are scored on, plus an
experiment manifest that identifies exactly what ran (TASK-020, RQ-02). It is a
pure-Python API — there is no `tramflow-ml` subcommand for it, and CLI and pipeline
wiring belong to TASK-058.

```python
from tramflow_ml.backtest import BacktestConfig, BacktestData, FoldRules, run_backtest
from tramflow_ml.features import MONTH_DAY, YEAR_MONTH, CoverageCalendar, load_entity_keys, load_observations

config = BacktestConfig(
    rules=(FoldRules(policy=MONTH_DAY), FoldRules(policy=YEAR_MONTH)),
    target="synthetic_boardings",
    unit="event_count",
)
data = BacktestData.of(
    load_entity_keys(fixture_dir / "entities.json"),
    load_observations(ingest_dir / "validations.jsonl"),
    CoverageCalendar.from_range(date(2024, 1, 1), date(2026, 1, 1), gaps=gap_dates),
)
outcome = run_backtest(config, data, [candidate, baseline])   # models, in the caller's order
outcome.passed, outcome.reasons, outcome.manifest.manifest_hash
```

A model is anything carrying `name`, `version` and
`predict(fold, data) -> Sequence[float]`. It is handed a `FoldData` that was already cut
at the fold's cutoff: the cutoff-visible train and validation observations, the `as_of(C)`
coverage view and the label-free feature rows (`FeatureRow.feature_dict()`). It never
receives the observation set, the coverage calendar or the origin, so it cannot build a
different fold, and it cannot read the label it is asked to predict. Predictions must be
finite and non-negative, which is what `contracts/forecast_v1.ForecastPoint` accepts.

Fold rules. One origin `O` yields three whole-period windows and one cutoff:

| Window | Boundaries |
|---|---|
| `test` | `[O, horizon_end(O))` — the horizon buckets, the labels |
| cutoff `C` | `O` moved back by the policy's `cutoff_lead_buckets` plus the embargo |
| `validation` | the `validation_periods` whole periods ending at the latest period boundary `<= C` |
| `train` | `[first whole bucket of the data, validation_start − embargo)` |

`train.end <= validation.start < validation.end <= C <= O < test.end` is asserted on
construction, so a fold whose windows overlap cannot exist. Origins are period-aligned
and `origin_stride_periods` apart (default 1), so successive test windows are exactly
contiguous and never overlap.

Period arithmetic is the feature layer's calendar arithmetic. A period is 24 elapsed
hours, one calendar month or twelve calendar months — `horizon_end` equals
`horizon_buckets(...)[-1].end` and `contracts.calendar_v1.forecast_buckets(...)[-1][1]`
for a leap February, a 31-day month, a 12-month year and a Moscow DST day, and a test
pins all four. Nothing is approximated as 30 or 365 days. A `day` period is 24 *elapsed*
hours because that is what `calendar.v1` says a day horizon is, so a day origin is any
exact Moscow hour and, across a DST transition, successive day origins stop landing on
midnight (2011-03-27 is followed by an origin at 01:00). Contiguity is preserved;
civil-day alignment is not. Moscow has had no DST since 2014, so this affects historical
spans only.

The cutoff is never reimplemented here. The embargo is applied by deriving an effective
policy — `replace(policy, cutoff_lead_buckets=lead + embargo)` — and handing *that* to
`build_features`, so `event_at < C and available_at <= C` and "a history bucket only when
`bucket_end <= C`" stay in exactly one place. A runtime check refuses a fold whose
declared cutoff differs from the cutoff the feature layer applied.

Eligibility. An origin becomes a fold only if every rule holds; the first failure, in
this order, is the recorded reason:

| Reason | Meaning |
|---|---|
| `horizon_beyond_data` | the horizon ends after the data does. Not a fold with missing labels — not a fold. Nothing is truncated |
| `incomplete_labels` | some horizon bucket has no label at all |
| `diluted_labels` | covered horizon dates over total horizon dates is below `minimum_label_unit_ratio` (default `1.0`) |
| `insufficient_train_history` | fewer than `minimum_train_buckets` train buckets, or validation would start before the data |

Every candidate origin is recorded either as a fold or as a refusal naming its horizon,
its origin and the numbers behind the decision, and both reach the fold hash. A refusal
that is not reported is indistinguishable from an origin nobody considered.

Non-passing states. `run_backtest` *returns* a state; it does not raise and it never
reports an empty pass.

| Status | When | `passed` |
|---|---|---|
| `evaluated` | at least `minimum_origins` eligible folds, all scored, at least `minimum_origins` of them carrying demand | `True` |
| `insufficient_history` | fewer eligible origins than required. The reason names the horizon, the required count, the eligible count and the refusal breakdown | `False` |
| `insufficient_signal` | enough folds, but too few carry any demand, so WAPE is undefined on the rest | `False` |

`HorizonOutcome.__post_init__` refuses to construct an `evaluated` outcome with too few
folds or too few folds carrying demand, so "scored nothing, reported success" is
unconstructible rather than merely untested. `minimum_origins` must be at least 1 for the
same reason. `passed` is a statement about the *fold set*, not about model quality —
whether a candidate beats its baseline is TASK-022's question.

Defaults, all configuration and none of them certified. `minimum_origins` is 3: one fold
cannot distinguish a candidate that is better from one that was lucky once, and two
cannot say which way. `minimum_train_buckets` defaults to the policy's own look-back,
`max(max(lags), max(rolling_windows), season_step × season_periods)` — 168 hourly, 364
daily, 36 monthly — because that is exactly the history every declared column needs.
`minimum_label_unit_ratio` is `1.0`: the test window is the ground truth, and a hole in it
means the measured error is measured against truth that is not there.

The embargo defaults to **0 buckets**, and the reasoning is worth reading before changing
it. An embargo guards a channel the cutoff cannot see. There is no such channel here:
labels are per-bucket counts with no smoothing or interpolation, a history bucket is used
only once fully elapsed, and late publication is already modelled more precisely by
`cutoff_lead_buckets` and by the coverage calendar's per-date publication instants. A
nonzero default would throw away genuinely available information at every origin and make
every model look worse than it is in production. Raise it as soon as a target is defined
over a window rather than a bucket, or an organizer source is found to revise
already-published dates.

Determinism. Four SHA-256 hashes over canonical JSON: `config_hash` (the rules with every
default resolved, plus each policy's full parameters), `data_hash` (the observations as
sorted canonical lines, plus the coverage dates, publication instants and capacities),
`fold_hash` (the ordered folds and every refusal) and `manifest_hash` over all three plus
the versions and the results. Timestamps are normalised to UTC before hashing, so two
spellings of one instant give one hash, and reversing the input event order changes
nothing. The manifest carries no `generated_at`, no path and no wall clock at all — a
manifest that changed every run would identify nothing. A test asserts the serialised
manifest contains no clock word and no filesystem path.

Leakage. The fold set is computed from the coverage calendar and the configuration alone
and never reads an event, so it cannot move when the data does. On a fold at origin
2025-06-01, appending 40 post-horizon events leaves the fold's `feature_digest`, every
test feature row and both observation partitions byte-identical; appending 20 events
*inside* the horizon leaves all of those identical while the labels legitimately rise. The
negative control passes too: moving one event's `available_at` across the cutoff does
change the feature digest and does drop that event from the validation partition, so the
test cannot succeed by ignoring its input.

Shared folds. `build_fold_set` is the only producer of a `FoldSet`; `run_backtest` builds
it once, loops folds outside and models inside, and hands every model the same `Fold` and
the same `FoldData` object. A test asserts two models record identical fold ids, identical
test row keys, and identical `id()` for every fold and data object they were given.

Observed on the real path (`synthetic` → `ingestion` → `features` → folds), 12 entities,
default rules:

| Fixture | Horizon | Eligible | Refused | Origins |
|---|---|---|---|---|
| default, 2024–2026, 64 events, gaps every 13 days | day | 667 | 56 `incomplete_labels`, 8 `insufficient_train_history` | 2024-01-09 … 2025-12-31 |
| | month | 0 | 24 `incomplete_labels` | — |
| | year | 0 | 2 `diluted_labels` (338/366 and 337/365 dates) | — |
| gapless, 2024–2026, 2 000 events | day | 723 | 8 `insufficient_train_history` | 2024-01-09 … 2025-12-31 |
| | month | 11 | 13 `insufficient_train_history` | 2025-02-01 … 2025-12-01 |
| | year | 0 | 2 `insufficient_train_history` | — |
| gapless, 2018–2026, 20 000 events | day | 2 914 | 8 | 2018-01-09 … 2025-12-31 |
| | month | 83 | 13 | 2019-02-01 … 2025-12-01 |
| | year | 4 | 4 | 2022-01-01 … 2025-01-01 |

Two years of history therefore support **no year fold at all**: a year fold needs three
years of monthly look-back, one year of validation and one complete future year, so five
years of coverage is the floor. The gapped fixture supports no month fold either, because
a gap day every 13 days puts a hole in every month. Both runs report
`status="insufficient_history"` with the horizon, the requirement, the eligible count and
the refusal breakdown, and `passed=False`. Two `run_backtest` calls, and runs built from
two independent ingestions of the same fixture, produce identical `data_hash`, `fold_hash`
and `manifest_hash` (gapless month horizon:
`f3ff88096bcde293199fddee42974e372aff1ccf10f2d451ab4408edf6a13791`).

Not certified before organizer data: every default above, the eligibility thresholds, and
the number of viable real yearly folds — which the table shows is a property of how much
coverage the organizer supplies, not of this code. `passed` does not mean a model is good.
Per-fold MAE and WAPE are the minimum needed to compare two models on identical folds;
the operational slices, the worst-slice report and interval quality are TASK-022, and no
model lives here (TASK-021, TASK-023). WAPE is `None`, never `0.0`, for a fold with no
demand, matching `evaluation.py`, and a test pins the two definitions together.
