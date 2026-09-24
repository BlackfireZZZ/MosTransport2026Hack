# TASK-019: leakage-safe aggregates and horizon-specific features

## Purpose and observable result

Turn ingested `data.v1` event rows into a route/direction/stop × calendar-bucket
feature table that a backtest can trust. Observable result: `build_features` returns
rows whose aggregate totals equal totals computed independently from the fixture,
whose every feature value is derived only from data available at an explicit cutoff,
and whose digest is byte-identical across runs. Appending or perturbing rows after
the cutoff must not change a single byte of the produced table.

Acceptance, from the tracker card:

1. Fixture sums match independently computed totals.
2. Future data perturbation cannot change past features.
3. `missing` differs from `0.0`.
4. Year/month boundaries use calendar periods, not 30-day steps.

## Context

Base `3e4ad59`; worktree `MosTransport2026Hack-worktrees/horizon-features`, branch
`agent/horizon-features`. Owned files: `ml/src/tramflow_ml/features/`,
`ml/tests/test_features_*.py`, this plan, and one `## Feature engineering` section in
`ml/README.md`. Not edited: `contracts/`, `backend/`, `frontend/`,
`ml/src/tramflow_ml/{synthetic.py,cli.py,evaluation.py}`,
`ml/src/tramflow_ml/{ingestion,identity}/`, the tracker, the session handoff.
CLI wiring is a later task (TASK-058). Pure Python, no new dependency.

Upstream contracts the layer consumes:

- `ml/src/tramflow_ml/ingestion/` writes `validations.jsonl` / `telemetry.jsonl` with
  exactly the `data.v1` fields, timestamps re-emitted with the `Europe/Moscow` offset,
  and `manifest.json` last. The feature layer reads those lines; it never re-reads the
  raw fixture.
- `ml/src/tramflow_ml/identity/` fixes the service-day convention: `Europe/Moscow`
  civil date, `AlignedTime.service_day_shifted`, clock offsets applied in UTC. The
  feature layer uses the same `ZoneInfo("Europe/Moscow")` and civil-date rule and
  reuses `CanonicalCatalog` to enumerate entities (read-only import).

Terms: *bucket* is a half-open `[start, end)` Moscow interval; *entity* is
`(route_id, direction_id, stop_id)`; *cutoff* `C` is the instant after which no
information may enter a feature; *coverage* is the explicit set of Moscow civil dates
the source claims to cover; *missing* is the absence of information, distinct from an
observed zero.

Oracles, used by tests only and reached with the existing
`ROOT = Path(__file__).parents[2]; sys.path.insert(0, str(ROOT))` idiom:

- `contracts/calendar_v1.forecast_buckets` — the authoritative day/month/year bucket
  boundaries. `features.calendar` must reproduce them without importing contracts.
- `contracts/calendar_v1.service_date`, `in_window` — civil date and half-open window.
- `contracts/data_v1.EventRow.visible_at` — the availability rule
  (`event_at < cutoff and available_at <= cutoff`).
- `contracts/data_v1.ObservedAggregate` — the `coverage`/`value` shape our aggregate
  cell must satisfy (`missing` ⇔ `value is None`).
- `contracts/forecast_v1.ForecastArtifact` — horizon → granularity mapping
  (day→hourly, month→daily, year→monthly).

Production code in `ml/src/` must never import `contracts`; a test asserts this.

## Scope and non-goals

In scope: entity buckets, coverage-aware aggregation, calendar features, lags,
rolling and seasonal statistics, three availability policies (day/hour, month/day,
year/month), a deterministic digest, tests, and the README section.

Out of scope: any model, any CLI command, any backend or serving change, holiday
calendars, weather, events, occupancy, OD. Real historical weather and event data are
not available at the cutoff for a forecast origin and therefore cannot become
features; the card records that as the pre-data risk and no placeholder column is
created for them.

## Acceptance

- `aggregate_cells` summed per `(route, direction, stop, date, hour)` equals
  `generation.json` → `cell_totals` entry for entry, and the grand total equals
  `counts.unique_validations`, which the generator computed and the feature code
  never sees.
- A feature value is `None` exactly when the information does not exist at the
  cutoff; no code path substitutes `0.0`.
- Rebuilding after appending or perturbing post-cutoff events yields the identical
  digest; moving an event's `available_at` across the cutoff changes it.
- Every bucket boundary equals `contracts.calendar_v1.forecast_buckets` for the same
  origin and horizon, including a leap February, a 31-day month, a 12-month year and
  a historical Moscow DST day.
- Behaviour that must not change: `ingestion`, `identity`, `synthetic`, `evaluation`,
  the CLI, and every existing test.

## Progress and decisions

1. **Bucket policy.** The aggregation key is
   `(route_id, direction_id, stop_id, [bucket_start, bucket_end))` in
   `Europe/Moscow`, half-open. Granularity follows the horizon exactly as
   `ForecastArtifact` requires: `day → hourly`, `month → daily`, `year → monthly`.
   Direction is part of the key, never collapsed, because the same stop carries
   different demand per direction and `identity` refuses to infer a direction.
   `stop_sequence` is not part of the key: a stop visited twice on a loop aggregates
   to one cell, because the forecast contract keys on
   `(route_id, stop_id, horizon, bucket_start)`.
2. **Missing representation.** `AggregateCell.value` is `int | None` with
   `coverage: "observed" | "missing"`, and `coverage == "missing"` iff
   `value is None` — the `ObservedAggregate` invariant. A feature value is
   `float | None`; `None` is the single missing representation and never 0.0.
   Partial coverage is not hidden: a cell also carries `covered_units` and
   `total_units` (Moscow civil dates the bucket spans), so a month bucket with a
   one-day source gap is `observed` with `covered_units < total_units` rather than
   silently complete. Unknown entity capacity is `None`, not 0.0.
3. **Coverage is an input, not an inference.** `CoverageCalendar` holds the explicit
   set of Moscow civil dates the source covers. A bucket with zero covered dates is
   `missing`; a covered bucket with no events is `observed` with value 0. Without a
   coverage calendar the layer cannot tell "no passengers" from "no data", so the
   calendar is required, not optional.
4. **Aggregates stay sparse.** Cells exist only where events landed; any other bucket
   is resolved on demand against the coverage calendar. Two years of hourly buckets ×
   every entity is never materialised, so memory is bounded by the event count plus
   the queried feature window.
5. **Availability cutoff.** A policy maps a forecast origin to one cutoff
   `C = origin - cutoff_lead` (default lead 0). An observation may enter a feature
   only when `event_at < C and available_at <= C`, byte-for-byte the
   `EventRow.visible_at` rule. A history bucket is usable only when its
   `bucket_end <= C`: a bucket still running at the cutoff is `missing`, never a
   partial sum. That makes intra-horizon lags explicitly missing instead of leaking —
   for the day/hour policy `lag_1h` is available only for the first target hour.
6. **Rolling statistics are anchored at the cutoff**, not at the target bucket: the
   window is the `w` buckets ending at the last bucket with `bucket_end <= C`. Every
   row of one horizon therefore shares the same past window, which is what a
   forecaster actually knows, and no anchor can reach forward. `sum`, `mean` and `max`
   are computed over the observed buckets only, in chronological order for float
   determinism; `observed` and `coverage` expose how much of the window existed, and
   a window with zero observations is `None` everywhere, not 0.0.
7. **Seasonal features use whole calendar steps** of the policy's season (24 hours,
   7 days, 12 months) taken backwards from the target bucket, each step filtered by
   the same availability rule.
8. **Calendar arithmetic is calendar arithmetic.** Hour steps move by whole UTC hours
   (every historical Moscow offset is a whole hour, so this equals wall-clock hour
   truncation and stays correct across a DST transition). Day steps move the civil
   date and recombine at Moscow midnight. Month steps move
   `year * 12 + month - 1` and recombine at midnight on the first. No 30-day or
   365-day approximation exists anywhere in the package; a test compares every
   boundary with `forecast_buckets`.
9. **Determinism.** Entities are sorted by `(route_id, direction_id, stop_id)`,
   buckets chronologically, feature names by definition order of the policy. The
   digest is SHA-256 over canonical JSON (sorted keys, compact separators) of the
   whole table plus its header. No wall clock, no path, no dict insertion order, no
   set iteration reaches the output.
10. **Immutability.** Every record is a frozen dataclass or a `TypedDict` built
    fresh; inputs are never mutated. Mappings handed out are wrapped in
    `MappingProxyType`.

Implemented 2026-09-25 as `ml/src/tramflow_ml/features/` — `records.py` (215 lines),
`build.py` (155), `periods.py` (125), `history.py` (122), `__init__.py` (117),
`calendar_features.py` (112), `policy.py` (95), `aggregate.py` (80), `events.py` (77),
`coverage.py` (46) — every function under 50 lines, largest module 215 lines. Tests:
`ml/tests/test_features_{calendar,aggregate,history,leakage,missing,fixtures}.py`
(86 tests).

Three test defects were found and corrected on first run, with no change to the
implementation:

1. `test_month_buckets_are_calendar_days_not_thirty` asserted
   `end != origin + 30 days` for every month, which is false for April — April has
   exactly 30 days. The assertion became the exact equivalence
   `(end == origin + 30 days) == (days == 30)`, which still refuses a fixed 30-day
   month for February, January and March.
2. The DST assertion compared `end` with `origin + timedelta(hours=24)` on an aware
   Moscow datetime. That is wall-clock arithmetic and returns 2011-03-28T00:00+04:00,
   not 24 elapsed hours. It now compares in UTC and additionally asserts that the
   wall-clock form differs, which is the point of the case.
3. `test_an_event_published_after_the_cutoff_is_not_a_feature` read `rows[0]`, the
   00:00 bucket, while the event was at 08:00; it now selects the row by bucket start.

A fourth defect was caught before running: a draft of the missing test referenced a
`lag_96h` column that the `day/hour` policy does not declare. The test was rewritten to
contrast `lag_24h` (an observed zero) with `lag_48h` (missing) inside one row, which is
the sharper assertion anyway.

## Research evidence

No new algorithm is introduced: lags, rolling windows and a per-origin availability
cutoff are standard time-series practice, and the calendar-period requirement comes
from the repository's own `contracts/calendar_v1.py`, which is the authoritative
source used as the test oracle. The one design point worth naming is that the cutoff
is applied to two independent timestamps (`event_at` and `available_at`) rather than
one, which is already decided by `contracts/data_v1.EventRow.visible_at` and the
`availability_policy: "event-and-availability.v1"` field of `DatasetManifest`; this
plan implements that existing decision rather than making a new one. No internet
research was performed, so nothing here is presented as external evidence.

## Validation and recovery

Plan, in order:

1. Hand-calculated unit fixtures per property, run first: calendar boundaries against
   `forecast_buckets` (including 2024-02 leap February, a 31-day month, a year of 12
   calendar months, and the Moscow 2011-03-27 DST transition, which is why hour steps
   are taken in UTC), aggregation on a tiny hand-counted event list, the availability
   rule against `EventRow.visible_at`, missing vs zero, and lag/rolling behaviour.
2. Aggregation oracle on the synthetic fixture: totals recomputed from
   `generation.json` → `cell_totals` (produced by the generator, not by the feature
   code) must equal the sum over our aggregate cells, per cell and in total.
3. Leakage: build a table at cutoff `C`, then append events after `C` and perturb the
   values of existing post-`C` events, rebuild, and assert the digest is unchanged.
   Then move an event's `available_at` from before `C` to after `C` and assert the
   digest *does* change, so the test cannot pass by ignoring its input.
4. Determinism: two builds from the same inputs produce the same digest.
5. `make ml-check`, then `make check`, then `git diff --check`.

Observed results:

- `make ml-check`: `ruff check ml` → "All checks passed!"; `mypy ml/src` → "Success: no
  issues found in 32 source files"; `pytest ml/tests` → **237 passed in 8.34s**
  (86 new feature tests: calendar 25, leakage 21, aggregate 13, history 10, missing 9,
  fixtures 8; 151 pre-existing).
- `make check`: **exit 0**. Architecture boundaries passed; backend ruff clean, mypy 42
  files, **292 passed / 10 skipped**; ML ruff clean, mypy 32 files, **237 passed**;
  golden evaluation `"passed": true`; frontend **8 files / 47 tests** passed and
  production build `built in 687ms`; contract check current (OpenAPI snapshot and
  generated TypeScript); reference contracts ruff clean, mypy 3 files,
  **119 passed**; `docker compose config --quiet` clean.
- Reconciliation, synthetic → ingestion → features on the tiny fixture
  (`SyntheticConfig()`, 2024-01-01 … 2026-01-01, seed 42, 12 entity keys):

  | Quantity | Independent source | Feature layer |
  |---|---|---|
  | validation rows written | ingestion manifest `input_rows` 67, `duplicates` 3, `quarantined` 0, `valid` 64 | 64 observations read |
  | hourly cells | `generation.json` `cell_totals`: 64 cells, sum 64 | 64 cells, sum 64, **equal cell for cell** |
  | daily cells | sum 64 | 64 cells, sum 64 |
  | monthly cells | sum 64, grouped by `date[:7]` | 64 cells, sum 64, **equal group for group** |
  | generator `counts.unique_validations` | 64 | `AggregateIndex.total` 64 |

- Determinism, two builds from the same inputs plus a build from a second independent
  ingestion run of the same fixture (`output_hash` identical, `d7ddfe0d3c673657…`):

  | Policy | Rows × columns | Cutoff | `digest` (all three runs) |
  |---|---|---|---|
  | `day/hour` | 288 × 25 | 2025-06-10T00:00:00+03:00 | `7e412bb01ce0072aa68d77bfde177581c185abdeaed8e95dbaf926b82735b999` |
  | `month/day` | 360 × 25 | 2025-06-01T00:00:00+03:00 | `b3ad914c0ca53de67cb57fe785c296d042d5cd614de43566f636807489cb4170` |
  | `year/month` | 144 × 22 | 2025-01-01T00:00:00+03:00 | `1bf64c53cbbbf66d4c1541644b29b92f9ec8e7c1b379250deabd8a90d5314ef5` |

  Corresponding `feature_digest` values: `2f7067776b125aad…`, `0e84576dcd94e5fe…`,
  `afc4d7af8e395eb4…`. Run 1, run 2 and the second-ingestion build agreed on every
  digest.
- Leakage, per policy: appending 40 post-cutoff events and replacing 3 post-cutoff
  events with 60 leaves `feature_digest` and every row's encoded feature dict
  byte-identical; events after the horizon end leave even the full `digest` identical;
  reversing the input order changes nothing. The negative control passes too — moving
  one event's `available_at` across the cutoff *does* change `feature_digest`, so the
  test cannot succeed by ignoring its input. `Observation.visible_at` agrees with
  `EventRow.visible_at` on all nine event/lag combinations tested.
- `git diff --check`: no whitespace errors.

Recovery: the package has no consumer yet, so reverting the commits removes it
cleanly and no other area changes behaviour.
