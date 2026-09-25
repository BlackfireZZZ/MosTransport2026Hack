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
(`7e412bb0…` for `day/hour`, `b3ad914c…` for `month/day`, `58e57f49…` for `year/month`).
All three are pinned by `test_the_published_digest_still_describes_the_committed_fixture`,
so a change that moves one fails the suite instead of leaving this paragraph stale. The
`year/month` value superseded `408d4580…` when the `*_units` columns were clipped at the
cutoff; see the correction in the completed execution plan.

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
`predict(fold, data) -> Sequence[float]` (`FoldModel` is a `Protocol`, so a typed caller
is structurally checked). It is handed a `FoldView` and a `FoldData` that were both cut
at the fold's cutoff: the cutoff-visible train and validation observations and the
label-free feature rows (`FeatureRow.feature_dict()`). Precisely what it does *not*
receive: the full observation set, any coverage calendar, and the fold's
`label_covered_units`/`label_total_units` — the last because with
`minimum_label_unit_ratio` below 1.0 they state how much of the *horizon* the source
covers, which a forecaster at the cutoff could not know. It does receive the origin and
the window boundaries, which are the question being asked. Coverage reaches a model only
through the feature columns (`*_coverage`, `*_units`), which the feature layer clips at
the cutoff. Every test row and its nested `features` mapping is a `MappingProxyType`,
because the same `FoldData` instance is handed to every model and a mutable row would let
the first model rewrite the second's input in silence. Predictions must be finite and
non-negative, which is what `contracts/forecast_v1.ForecastPoint` accepts.

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
| `insufficient_train_history` | validation would start before the data; or fewer than `minimum_train_buckets` buckets in the train window; or fewer than that many *covered* buckets in it |

Every candidate origin is recorded either as a fold or as a refusal naming its horizon,
its origin and the numbers behind the decision, and both reach the fold hash. A refusal
that is not reported is indistinguishable from an origin nobody considered.

Non-passing states. `run_backtest` *returns* a state; it does not raise and it never
reports an empty pass.

| Status | When | `passed` |
|---|---|---|
| `evaluated` | at least `minimum_origins` eligible folds, all scored, at least `minimum_origins_with_demand` of them carrying demand | `True` |
| `insufficient_history` | fewer eligible origins than required. The reason names the horizon, the required count, the eligible count and the refusal breakdown | `False` |
| `insufficient_signal` | enough folds, but fewer than `minimum_origins_with_demand` carry any demand, so WAPE is undefined on the rest | `False` |

`HorizonOutcome.__post_init__` refuses to construct an `evaluated` outcome with too few
folds, too few folds carrying demand, no model results at all, or a model that scored
fewer folds than were eligible — so "scored nothing, reported success" is unconstructible
rather than merely untested. `minimum_origins` must be at least 1 for the same reason. `passed` is a statement about the *fold set*, not about model quality —
whether a candidate beats its baseline is TASK-022's question.

Defaults, all configuration and none of them certified. `minimum_origins` is 3: one fold
cannot distinguish a candidate that is better from one that was lucky once, and two
cannot say which way. `minimum_origins_with_demand` defaults to `minimum_origins` but is a separate knob, so
raising one to demand more folds does not silently tighten the other.
`minimum_train_buckets` defaults to the policy's own look-back,
`max(max(lags), max(rolling_windows), season_step × season_periods)` — 168 hourly, 364
daily, 36 monthly — because that is exactly the history every declared column needs. It
counts buckets the coverage calendar actually **covers**, not calendar distance: a train
window spanning three years of which the source covers one day is not three years of
history, and a fold standing on it would report success with every lag, window and season
missing.
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
the versions, **the model names and versions in the order they were compared**, and the
results. Timestamps are normalised to UTC before hashing, so two
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
and `manifest_hash`. For the gapless two-year fixture on the month horizon, scored by
`zero@0.1.0` then `constant-one@0.1.0` in that order — the model set is part of
`manifest_hash`, so a published value means nothing without it:

| Hash | Value |
|---|---|
| `config_hash` | `da8ffcae72422a69b31add316766c715fe5e1929ed88df40ec2f40fa9073ee53` |
| `data_hash` | `bc572e95e28d52341e3283f00330ba38f198b27c9170d0ff9a6b834ea00d1704` |
| `fold_hash` | `755ca80bd8af1e72b570fae7abee5b2c40994619a011a919c05b96868317ec39` |
| `manifest_hash` | `21a3b973a5ee94eeea49c0a3eaca2dd73884e8f349d96d79b0e18292655797f9` |

`test_backtest_fixtures.py` pins all four, so they cannot go stale unnoticed; swapping the
two models leaves `fold_hash` alone and moves `manifest_hash`, which is the point of
recording the model set.

Not certified before organizer data: every default above, the eligibility thresholds, and
the number of viable real yearly folds — which the table shows is a property of how much
coverage the organizer supplies, not of this code. `passed` does not mean a model is good.
Per-fold MAE and WAPE are the minimum needed to compare two models on identical folds;
the operational slices, the worst-slice report and interval quality are TASK-022, and no
model lives here (TASK-021, TASK-023). WAPE is `None`, never `0.0`, for a fold with no
demand. `fold_metrics` and `evaluation.py` share no code: they are semantically aligned on
the ratio `Σ|error| / Σactual` — pinned by a case scored both ways — and deliberately
diverge on zero demand, where the golden gate raises and a fold reports `None` so that one
empty fold cannot kill a whole run. Both behaviours are tested.

## Intake profiling

`intake` reads a data sample and reports what is in it. It is the first thing to run
on an organizer extract (TASK-039, RQ-01–03) and the input to the real column mapping
(TASK-049/TASK-050).

```bash
uv run --package tramflow-ml tramflow-ml intake --input /tmp/synthetic-tiny
uv run --package tramflow-ml tramflow-ml intake --input /tmp/sample --profile sample.json \
  --catalog /tmp/sample/entities.json --output /tmp/intake-report.json
```

**Read-only.** Every file under `--input` is opened `"rb"` and nothing is written
there: no normalization, no move, no temporary file, no marker. `--output` is refused
when it resolves inside `--input`. The report goes to stdout, and to `--output` as
well when one is given.

Per stream (`validations`, `telemetry`) the report carries: physical `rows`, `readable`
rows and `unreadable` rows by reason; per canonical field a summary whose shape follows
that field's classification; `duplicates` keyed on `event_id`; the observed `date_span`;
and `join_coverage`. `supportability` then states, from the measured span and coverage
alone, which horizons and targets the sample could carry.

Classification decides what may be printed about a field:

| Classification | Fields | What is reported |
|---|---|---|
| `identifier` | `event_id`, `route_id`, `direction_id`, `stop_id`, `vehicle_id`, `entity_version`, `source_version` | present/missing counts and rate, distinct-value count, min and max length, and a character-class signature (`digits`, `letters`, `alnum`, `alnum_punct`, `other`) |
| `timestamp` | `event_at`, `available_at` | present/missing, count of values that would not parse, first and last instant in `Europe/Moscow` |
| `measure` | `stop_sequence`, `latitude`, `longitude` | present/missing, `unparsed` (not a number), `out_of_contract` (a number `ingest` will quarantine), minimum, maximum, and the sum for an integer-contract field with neither |
| `enumerated` | `schema_version`, `target`, `unit`, `synthetic` | a count per allowlisted member, plus one `other` count |

**Identifier suppression.** An identifier is summarised by shape and never by value:
no sample row, no example of a bad row, no most-frequent value, no hash of a value.
The accumulator itself keeps only 8-byte digests, so it holds nothing it could print.
An enumerated value outside its allowlist is counted as `other` and never quoted.

**No cell of the sample is ever quoted, including one that arrives labelled as a
column name.** Intake cannot know that a CSV's first line is a header, and a JSON
object can be keyed by anything.

The unit of trust is the **line**, not the cell. A per-cell test can only ask "does
this look like a name?", and a datum is perfectly capable of looking like one:
`MSK4276380155129043`, `A4276380155129043` and `Ivanov` are all valid identifiers, so
no predicate can separate them from real column names — the safe set and the word-like
set overlap. What distinguishes a header is that *every* cell of it is word-like
(`str.isidentifier`, unicode included, so `маршрут` passes and anything with a space, a
separator or a leading digit does not). So if any cell of the line fails, the whole line
is data and every cell is rendered by shape at its position — `<column 2: 28 alnum>` —
including the cells that happen to look like names. Position is what keeps the checklist
actionable: the operator still learns which column needs mapping. The same rule applies
to a JSON Lines stream, where the unit is the key set rather than a header line.

A real header, where every cell is word-like, reads exactly as it always did. The cost
falls on a genuine header with a spaced or hyphenated name — `route_id,Stop Name` — which
is shown entirely by shape; the operator can read their own file, and a profile naming
the real column still works, because matching never goes through the label. Widening the
per-cell test to admit those names would be worse: it would let a headerless line of
uniformly name-shaped cells pass as a header.

One case the rule does not close: a headerless file in which *every* cell is word-like
(`Ivanov,Petrov,Sidorov`) still prints those cells. The line rule narrows that class
sharply — one digit-leading, punctuated or spaced cell anywhere in the line condemns it
— but does not eliminate it. Comparing row one's shapes against row two's was considered
and rejected: a genuine header `stop_id` and its data `synthetic:stop:1` share the
`alnum_punct` signature, so the comparison false-positives on real headers.

What the report *does* contain, beyond constants defined in our code and derived
numbers and instants: word-like column names and file names read from the sample's
schema; the names of every file in the sample directory when the streams cannot be
located; the `entity_version` and validation text of the entity catalog; and the exact
minimum and maximum of each measure field. Those minima and maxima are real values
from single rows — for telemetry they are literal GPS coordinates. They are not
passenger identifiers, but **TASK-049/TASK-050 must not map an organizer column
carrying personal data onto a measure field**, because a measure's range prints.

**Mapping is explicit or identical, never inferred.** A canonical field maps to a
source column only when a profile says so, or when a column carries exactly the
canonical name. Nothing maps by name similarity, position or a synonym list. Without
`--profile` intake uses the built-in `canonical` shape (`validations.jsonl` /
`telemetry.jsonl`, or the `.csv` spelling; both present at once is an ambiguity it
refuses). A profile is `intake-profile.v1`:

```json
{
  "schema_version": "intake-profile.v1",
  "name": "alternate-fixture",
  "source_format": "csv",
  "files": {"validations": "boardings.csv", "telemetry": "positions.csv"},
  "columns": {"event_id": "row_key", "event_at": "happened", "stop_id": "platform_code"},
  "constants": {},
  "timestamp_format": "%d.%m.%Y %H:%M:%S",
  "assume_timezone": "Europe/Moscow"
}
```

`columns` maps canonical field → source column; `constants` supplies a field the
source omits when one value is right for every row; `timestamp_format` is a `strptime`
pattern (`null` for ISO-8601) and `assume_timezone` names the zone naive timestamps
are read in. It is the same vocabulary as `ingestion.ColumnAdapter`, so one mapping
serves both tools. `has_header` (CSV, default `true`) declares whether the first line
is a header: set it to `false` for a headerless extract, and every line is then data
and the columns are addressed as `column_1`, `column_2` and so on. One `columns` map
serves both streams, so a headerless CSV whose two streams have different column
layouts cannot be described by one profile — give the two streams the same layout, or
wait for per-stream columns.

An explicit `columns` entry always takes effect. On CSV, a declared column absent from
the header is refused by name, because the header is the schema and the column cannot
be read. On JSON Lines there is no schema, so a declared key that no row carries is
simply a field that is always missing, reported as `missing_rate: 1.0` and listed under
`declared_columns_never_seen`. Canonical-name auto-mapping needs the column to be
observed somewhere in the file — every key of every line is read, not a leading
sample, so a field that first appears in row 251 is found — and a required field that
appears nowhere and is not declared is refused with the checklist rather than reported
as wholly missing, because reporting it would silently replace the checklist this tool
exists to produce.

When a required field cannot be mapped, intake refuses and prints, per stream: the
file, every column it found, what it did map, what a profile supplied as a constant,
every unmapped canonical field with a one-line statement of what that field must
carry, the columns it did not use, and a fill-in profile whose unmapped entries are
`null`. That message is the adapter checklist; completing it and rerunning with
`--profile` is the whole workflow.

Join coverage speaks the `identity` vocabulary — `matched` by kind, `unmatched` by
reason, `ambiguous`, `stale` — and is measured against `identity_crosswalk`, which
maps every canonical id to itself. The report records `"crosswalk": "identity"` for
that reason: on a sample not already keyed by catalog ids the figure is a statement
about how far the ids are from ours, not a certified join rate. Rows that carry no
`event_id`, or whose `event_at` will not parse, are counted under `unalignable`
instead of being silently dropped. Without a catalog the section is
`"measured": false` with the reason, never a zero.

Supportability is one stated rule, not a judgement per sample. For horizon `H` with
policy `P`, the deepest history reach is
`max(max(P.lags), max(P.rolling_windows), P.season_step * P.season_periods)` buckets of
`P`'s granularity, and one forecast period is 24 hourly, 31 daily or 12 monthly buckets
more; `H` is supportable when the observed span yields that many complete buckets *and*
at least half of the span's civil dates carry rows. A bucket counts only when it lies
wholly inside the observed span: a sample whose first row lands at 23:00 has not
observed that day, and the bucket holding the last row is never complete either. Both thresholds appear next to the
observed values, so every "no" carries the numbers that produced it — the tiny
synthetic fixture reports `insufficient_history: policy 'year/month' reads 36 monthly
buckets of history and forecasts 12 more, so it needs 48; the observed span of 731 days
yields 24`. `evaluable_buckets_upper_bound` is the surplus: an upper bound on how many
buckets could be evaluated, not a fold plan. A target is supportable when the sample
declares it and carries only the one producible unit, `event_count`.

Measures are read against the contract `ingestion.normalize` enforces — `stop_sequence`
a non-negative integer, latitude within ±90, longitude within ±180 — and a value outside
it is counted as `out_of_contract` rather than waved through, so the profile says in
advance how many rows the pipeline is going to reject. Numbers are canonicalised before
they are summarised or digested: an integer-contract field accepts `0.0` as `0`, which
is how a CSV written from a float-typed column spells every integer. Without that, the
same fact would read differently for having passed through pandas, and one `event_id`
spelled `0` in one file and `0.0` in another would be reported as a conflicting
duplicate it is not.

Counting contract per stream: `rows == readable + unreadable` and
`readable == unkeyed + distinct_keys + repeated + conflicting`, and when a catalog is
present `readable == join total + unalignable`. Exit codes match `ingest`: 0 on
success, 1 when one of those identities fails, 2 for a usage, input or schema problem.
A schema refusal prints the checklist without the argparse usage block so the
checklist is not buried; the code is still 2.

Determinism: the report carries no wall clock and no absolute path — file basenames
only — and every mapping is emitted with sorted keys. The same sample profiled twice,
and a byte-identical copy of it at a different absolute path, produce identical report
bytes. The same events rendered in a second schema — CSV instead of JSON Lines,
renamed columns, `%d.%m.%Y %H:%M:%S` instead of ISO-8601 — produce byte-identical
`streams` and `supportability` sections; only `source`, which describes the encoding,
differs. Missing has one definition across encodings for that reason: a key that is
absent, a JSON `null`, or a blank string.

Memory grows with the number of distinct `event_id` and distinct identifier values,
not with the row count: intake keeps one dictionary entry per distinct key, holding two
8-byte digests rather than the values. It is a sample profiler, not a pipeline —
`ingest` uses SQLite for the same job at scale — so profile a slice of a very large
extract rather than all of it.

Not decided before organizer data: the column mapping itself, which is the point —
intake builds the checklist and refuses to guess, and certifying the real mapping is
TASK-049/TASK-050. Nor is it decided which horizon we will actually forecast: the
policies intake measures against (lags, rolling windows, seasons) are the team proposal
from `features/policy.py` and are configuration, so a supportability verdict moves when
they do. `MIN_COVERAGE_RATIO` is a threshold, not a measurement. The join rate under
the identity crosswalk is not a real join rate. And a target that is *supportable* is
not thereby the target: which quantity the organizer actually measures is TASK-049.

## Slice and interval reporting

`tramflow_ml.slices` answers the question the golden gate and the rolling backtest
deliberately do not: is this candidate good *where it has to be*. `make ml-eval` slices
by horizon only, and `BacktestOutcome.passed` is a statement about the fold set, not
about quality. Neither is changed by this package — `evaluation.py` is untouched and its
output is byte-for-byte what it was.

The input is a `ScoredPoint`: one forecast already placed beside its outcome. The layer
never predicts and never invents an attribute — entity, horizon, bucket, fold, target,
unit, optional event tag, optional interval, optional baseline, optional capacity.
`None` is the only spelling of missing, as in `features`.

### The slices

Every point falls into every axis it can support, and axes are derived from the point,
never supplied, so a slice cannot be relabelled to escape a verdict.

| Axis | Value | Note |
|---|---|---|
| `overall` | `all` | always present, always required |
| `horizon` | `day`/`month`/`year` | |
| `fold` | `fold_id` | one origin, exempt from the fold floor — see below |
| `route` | `route_id` | both operating sides pooled |
| `direction` | `route_id\|direction_id` | a bare `direction_id` is meaningless across routes (ADR-0006) |
| `stop` | `stop_id` | a physical place, so it spans both sides |
| `entity` | `route_id\|direction_id\|stop_id` | the forecast key |
| `daypart` | `morning_peak`/`evening_peak`/`offpeak` | hourly buckets only |
| `route_daypart` | `route_id\|daypart` | "the evening peak on this route" is a cross, not an axis |
| `entity_daypart` | `route_id\|direction_id\|stop_id\|daypart` | the forecast key crossed with the operating period |
| `event` | the caller's tag | absent when the point carries none |

`MORNING_PEAK_HOURS` is 07–09 and `EVENING_PEAK_HOURS` is 17–19 Europe/Moscow. Only the
`day` horizon has hourly buckets, so `month` and `year` points are in **no** daypart
slice rather than in a fabricated one: a monthly bucket has no evening peak.

A `fold` slice is one origin by construction, so `MIN_FOLDS_FOR_GATE` cannot apply to it
(`SINGLE_ORIGIN_AXES`). That floor exists because one origin is not a temporal
generalisation; the `fold` axis exists precisely to expose a model that collapsed on one
origin, so gating it on having two would make it unable to report the thing it is for.
The sample floor still applies.

`entity_daypart` is there because the diluting axes are not enough. On one route with six
stops over four folds, where `stop-1` is 100% wrong at the evening peak and everything
else is perfect, `overall` reads 0.033, `stop=stop-1` reads 0.2, `daypart=evening_peak`
reads 0.167 and `entity=route-A|dir-N|stop-1` reads 0.2 — every one of them inside
`MAX_WAPE`. Only the cross reads 1.0. ADR-0006 records that tram load is sharply
asymmetric between directions, which is the same argument: the cut that exposes a
failure is the forecast key crossed with the operating period, not either alone.

`fold × horizon` is deliberately **not** produced: `backtest.folds.fold_id` is
`f"{horizon}@{origin}"`, so on any fold set this repository generates that cross is one
to one with `fold` and would only duplicate it.

#### What the axes cannot see

These are limits of a fixed-axis slicer, not of the judging logic, and no amount of
threshold work removes them:

- **A subgroup that shares every cut axis with well-predicted points is invisible by
  construction.** If the bad rows have the same route, direction, stop, daypart, horizon
  and fold as the good ones, every slice containing them also contains the good ones and
  every slice reads the same diluted number. A pass is therefore never proof that no such
  subgroup exists.
- **A report built without entity identification can cut far fewer axes.** With
  `entity=None` the `route`, `direction`, `stop`, `entity`, `route_daypart` and
  `entity_daypart` axes are all absent, leaving `overall`, `horizon`, `fold`, `daypart`
  for hourly buckets, and `event` where the caller tagged one. A catastrophic route then
  reads as the overall dilution on every axis that remains. Entity identification is
  caller-supplied metadata; this layer cannot synthesise it, and per ADR-0006 must not
  infer direction.

### The metrics and their units

Error totals come from `backtest.metrics.fold_metrics`, unchanged, so WAPE has one
definition across the offline path and folds pool by their summed quantities rather than
by averaging averages.

| Metric | Unit |
|---|---|
| `actual_total`, `error_total`, `mae`, `mean_actual`, `mean_width`, `mean_interval_score` | the target's unit |
| `wape`, `baseline_wape`, `coverage`, `level`, `relative_interval_width`, `actual_overload_rate`, `predicted_overload_rate` | `ratio` |
| `samples`, `folds`, `covered`, `actual_overloaded`, `predicted_overloaded` | `count` |

Every slice carries `samples`, `folds`, and a `units` mapping naming the unit of each
metric individually, beside the `unit` field that gives the target's own unit. The two are
not the same thing and must not be confused: applying the target unit to `wape` is simply
wrong, so the report says which metrics it applies to. Failure records carry the same
per-metric unit. A number without its support is not reportable, so support travels with
every number through `to_dict()` and through every failure line.

The nested `interval` and `overload` dictionaries carry `samples` but no `folds`. Both are
`null` unless *every* point of the slice qualifies, so their sample count always equals
the slice's and the slice's fold count applies to them unchanged; a second copy would be a
field that can only ever agree.

A baseline comparison needs a baseline on every point, so one missing baseline disables
`wape_vs_baseline` for every slice that point belongs to — `overall` included. The reason
is recorded in `baseline_absent_reason` with the count, so "no baselines this run" and
"one row of five thousand" read differently. `interval_absent_reason` and
`overload_absent_reason` are its two siblings.

### Why coverage alone is never reported

An interval of `[0, 10000]` on demand of 100 has perfect coverage and no information.
Coverage is therefore reported only together with mean width and the mean
**interval (Winkler) score**

```
IS = (upper - lower) + (2/α)·(lower - y)·1{y < lower} + (2/α)·(y - upper)·1{y > upper}
```

with `α = 1 - level`, in the target's unit, lower is better. It is the standard proper
scoring rule for a central prediction interval (Winkler 1972; Gneiting & Raftery 2007
§6.2) and it is what makes width and coverage trade against each other at a stated rate
instead of being two thresholds someone can play off. On twelve points with demand 100,
a `[90, 110]` interval and a `[0, 10000]` one both have coverage 1.0; their mean scores
are 20 and 10000.

Interval quality is suppressed, with the reason on the record, when only some points in
a slice carry bounds, or when the points declare different levels or different methods —
a coverage figure pooled across two nominal levels describes neither.

**The nominal level is itself gated.** Both interval checks are stated relative to the
level the producer declares, so a low enough declaration makes both vacuous: at level
0.02 the coverage requirement would be negative and `2/α` is 2.04, which makes every miss
nearly free. Twelve points with demand 100, predicted 70, and an "interval" of
`[70, 70]` — a point estimate wearing an interval's clothes — passed at level 0.02 and
failed at level 0.80, on identical predictions. `MIN_INTERVAL_LEVEL` now fails any judged
slice whose declared level is below it, the coverage check is skipped rather than computed
against a negative requirement, and `GateThresholds` refuses a `MAX_COVERAGE_SHORTFALL`
that is not below `MIN_INTERVAL_LEVEL`, since such a pair could only produce a
requirement that judges nothing.

### Zero demand and small samples

- **Zero demand is not zero error.** WAPE is undefined when the denominator is zero, so
  a slice whose actual total is zero reports `wape: null` and status
  `insufficient_signal`, exactly as `backtest/metrics.py` does — never `0.0`, never an
  epsilon. MAE stays defined and is still reported. Such a slice cannot flatter a pooled
  ratio: its errors reach the numerator and nothing reaches the denominator.
  (`evaluation.py` instead *raises* on zero demand. That is deliberate and unchanged: in
  a curated five-case golden file a zero-demand horizon is an authoring mistake, whereas
  a real slice with no demand is data.)
- **Small samples are marked, never suppressed and never silently averaged.** Below
  `MIN_SAMPLES_FOR_GATE` scored points the status is `insufficient_samples`; below
  `MIN_FOLDS_FOR_GATE` distinct folds it is `insufficient_history`, reusing the
  backtest's word for its meaning — too few independent origins. Either way the slice
  keeps every metric and its support, is listed in full, and is excluded from the gate. A
  three-sample WAPE is noise; hiding it defeats the point of the report, and failing on
  it makes the gate unbelievable.
- **An ungated slice is counted and the worst of it is named.** The floors are about
  scarcity, but they can also be dodged by *placement*: eighteen rows is well over the
  sample floor, and putting them all on one origin once made them `insufficient_history`
  and invisible. The `fold` axis closes the crude form of that — a bad origin with nothing
  to dilute it is now a judged `fold` slice that fails — but a bad origin carrying enough
  well-predicted rows still passes on every axis. Every report therefore ends with a line
  like `18 slices ungated: 6 below the sample floor, 12 below the fold floor, 0 without
  demand; worst ungated WAPE 1 on direction=route-B|dir-N`, on a pass as well as a
  failure. Ties on the worst WAPE go to the larger slice, then to key order, because the
  same rows appear under several axis names.

### Overload metrics and absent capacity

Anything expressed as a fraction of capacity needs a capacity that is known and a target
that is a load. `overload` is `null`, with the reason recorded beside it, unless the
target is `onboard_load`, the unit is `passengers`, and **every** point in the slice
carries a positive capacity. There is no default capacity anywhere in this package. The
serving path currently has the opposite defect — `ForecastPointModel.capacity` defaults
to `180.0` against a response schema demanding `gt=0`, so an unknown capacity is served
as a fabricated number — and this package does not replicate it.

Overload is **reported and not gated**. The feature layer can only produce
`event_count`, so no slice this repository can build today carries an overload figure at
all, and a threshold over a quantity nothing yet produces would be a number invented to
look rigorous. A model that never predicts an overload on a route that is always
overloaded is therefore visible in the report and does not fail the gate. Gating it
belongs with the task that first produces a load target.

### The verdict

```
passed = no failure and no unproven slice
```

- Every slice whose status is `evaluated` is judged. A bad slice cannot escape by nobody
  having listed it.
- A **required** slice must additionally exist and be judgeable. A required slice with no
  points is `missing`; one too small, too short or without demand keeps its own status.
  Either way it is `unproven`, and absence never buys a pass. A required key naming an
  axis no point can emit is refused when the report is built, rather than becoming a
  permanent `unproven` that blames the data for a typo.
- `overall` is always required, so a report too small to judge does not pass either.

The gate is not unconditional, and three things bound it. It judges only slices with
status `evaluated`, so the floors decide what it looks at — the ungated line above exists
because of that. It judges only the axes listed earlier, so a subgroup sharing every axis
with well-predicted points is invisible to it. And overload is measured but not gated.
Read a pass as "nothing the configured axes and thresholds can see is wrong", never as
"nothing is wrong".

An excellent overall number removes nothing from either list. On 48 perfect off-peak
points and 12 catastrophic evening-peak ones across four folds, overall WAPE is 0.18 —
inside `MAX_WAPE` — and the verdict is:

```
FAIL: 3 breached, 0 unproven
daypart=evening_peak: wape 0.9 ratio exceeds 0.4 (MAX_WAPE=0.4) on 12 samples across 4 folds
entity_daypart=route-A|dir-N|stop-1|evening_peak: wape 0.9 ratio exceeds 0.4 (MAX_WAPE=0.4) on 12 samples across 4 folds
route_daypart=route-A|evening_peak: wape 0.9 ratio exceeds 0.4 (MAX_WAPE=0.4) on 12 samples across 4 folds
every slice was judged
```

### Thresholds, all provisional

| Constant | Value | Judges |
|---|---|---|
| `MIN_SAMPLES_FOR_GATE` | 12 | scored points needed before a slice is judged |
| `MIN_FOLDS_FOR_GATE` | 2 | distinct origins needed before a slice is judged |
| `MAX_WAPE` | 0.40 | slice WAPE |
| `MAX_WAPE_RATIO_TO_BASELINE` | 1.0 | slice WAPE against its own baseline's |
| `MAX_COVERAGE_SHORTFALL` | 0.10 | how far empirical coverage may fall below the nominal level |
| `MAX_INTERVAL_SCORE_TO_MEAN_ACTUAL` | 2.0 | mean interval score against the slice's mean demand |
| `MIN_INTERVAL_LEVEL` | 0.8 | the nominal level a judged interval must declare |
| `MIN_INTERVAL_SCORE_ALLOWANCE` | 8.0 (target units) | absolute interval score never called too wide |

**Not one of these is certified.** They were chosen so the mechanism could be
demonstrated on synthetic points. The report prints `"certified": false` beside them and
every failure carries the constant's name and value next to the observed number, so a
breach can be told apart from a badly chosen constant. Agreeing them against organizer
data is TASK-051. The interval score is compared with mean demand rather than with MAE
because a perfectly predicted slice has MAE 0, and an `evaluated` slice always has
positive demand — zero demand is `insufficient_signal` before it reaches the gate.

`MAX_INTERVAL_SCORE_TO_MEAN_ACTUAL` is the weakest of the seven, and it is weak in both
directions because a ratio to mean demand is a cap on the coefficient of variation.
Integer counts cannot be sharper than a few units, so a two-passenger bucket with a
`[0, 7]` interval is behaving correctly and the ratio alone failed it on every axis at
once; `MIN_INTERVAL_SCORE_ALLOWANCE` is the absolute floor that stops the gate firing on
correct behaviour, because a gate that does that is the one that gets switched off. The
opposite error is still open and is **not** fixed here: at mean demand 1000 an interval of
`[60, 1940]` scores 1880 against a limit of 2000 and passes, with
`relative_interval_width 1.88` printed beside it. Tightening the ratio to catch that would
re-break the low-demand case, so the real fix is to score against a reference interval
rather than against demand — which needs the baselines TASK-021 owns. Until then, read
`relative_interval_width` yourself; the gate will not catch a wide interval on a busy
slice.

Determinism: points are sorted canonically before any float is summed, so the report is a
function of the point set and not of the caller's ordering. Two points tying on that
order would still sum by input order, so a repeated `(entity, horizon, bucket, fold)` is
refused — a bucket is scored once per fold, as `forecast_v1` also requires of a published
artifact. The payload carries no wall clock and no absolute path, and
`SliceReport.digest` is the SHA-256 of it.

**Nothing calls this in anger yet.** `make ml-eval` still runs the old golden gate, and
`grep -rl tramflow_ml.slices` finds only the tests. A model that fails catastrophically
on one slice cannot fail `make check` through this package today; it can only fail these
unit tests on hand-built arrays. Wiring `build_report` into the publication pipeline is
TASK-058.

**What synthetic results do not establish.** Every demonstration above runs on arrays
constructed by hand to exercise the mechanism. A passing report on synthetic points says
that the reporting works, and says nothing whatever about whether any model forecasts
Moscow tram demand well. No threshold here has been agreed with anyone; no interval here
has been calibrated (TASK-024); no baseline here is the organizer's incumbent (TASK-021);
and the peak hours, the slice list and the required-slice list are our proposal, not an
operational requirement. Real evidence needs real data on untouched temporal slices,
which is TASK-051.
