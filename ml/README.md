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
