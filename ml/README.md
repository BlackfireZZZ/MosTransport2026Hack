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
| `measure` | `stop_sequence`, `latitude`, `longitude` | present/missing, non-numeric count, minimum, maximum, and the sum when every value is an integer |
| `enumerated` | `schema_version`, `target`, `unit`, `synthetic` | a count per allowlisted member, plus one `other` count |

**Identifier suppression.** An identifier is summarised by shape and never by value:
no sample row, no example of a bad row, no most-frequent value, no hash of a value.
The accumulator itself keeps only 8-byte digests, so it holds nothing it could print.
The invariant across the whole report is stronger than the identifier rule: **every
string in the output is either a constant defined in our code, a column or file name
read from the sample's schema, or a derived number or ISO-8601 instant.** An
enumerated value outside its allowlist is counted as `other` and never quoted, and the
unknown-schema failure names columns but quotes no cell. Column and file names are
deliberately echoed — a failure that does not name what it found is not actionable —
and they are schema, not passenger data.

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
serves both tools.

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
at least half of the span's civil dates carry rows. Both thresholds appear next to the
observed values, so every "no" carries the numbers that produced it — the tiny
synthetic fixture reports `insufficient_history: policy 'year/month' reads 36 monthly
buckets of history and forecasts 12 more, so it needs 48; the observed span of 731 days
yields 24`. `evaluable_buckets_upper_bound` is the surplus: an upper bound on how many
buckets could be evaluated, not a fold plan. A target is supportable when the sample
declares it and carries only the one producible unit, `event_count`.

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
