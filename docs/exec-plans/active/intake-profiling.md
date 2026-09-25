# TASK-039: first-data profiling and adaptation toolkit

## 1. Purpose and observable result

An operator who receives the organizer's first data sample runs one read-only
command and learns, without editing anything and without any of our code having
guessed a column name, four things: what the sample contains, what it is missing,
which forecast horizons and targets it could support, and — when we cannot read it
at all — exactly what has to be written down before we can.

Observable:

```bash
uv run --package tramflow-ml tramflow-ml intake --input <dir>
```

- Exit 0: a deterministic JSON report on stdout (`intake.v1`).
- Exit 2: an actionable schema failure on stderr naming the columns found, the
  canonical fields required, which of them could not be mapped, and a fill-in
  profile skeleton the operator can complete and pass back with `--profile`.
- Exit 1: an invariant of the report itself failed (per-stream row counts do not
  reconcile), matching the `ingest` exit-code register.
- The input directory's bytes are identical before and after any run.

## 2. Context

Base `c34e7d9`; worktree
`/home/chessnok/hacks/MosTransport2026Hack-worktrees/intake-profiling`, branch
`agent/intake-profiling`. TASK-039 in `docs/agentic/TASK_TRACKER.md`; blocks
TASK-049 (inspect organizer data) and TASK-050 (real adapters and crosswalks).

Owned files: `ml/src/tramflow_ml/intake/`, the `intake` subcommand in
`ml/src/tramflow_ml/cli.py`, `ml/tests/test_intake_*.py`, this plan, and one
`## Intake profiling` section appended to `ml/README.md`.

Not owned, not edited: `contracts/**`, `backend/**`, `frontend/**`,
`ml/src/tramflow_ml/{ingestion,identity,features}/**`,
`ml/src/tramflow_ml/synthetic.py`, `ml/src/tramflow_ml/evaluation.py`,
`ml/src/tramflow_ml/backtest/` and the tracker. A second agent holds
`backtest/` and `evaluation.py` in a parallel worktree, so horizon
supportability is derived from the measured span and coverage and never from
fold code.

Libraries imported, never modified:

- `tramflow_ml.ingestion.records.ColumnAdapter` — the canonical field → source
  column mapping type. Intake and ingestion must speak one mapping language, or
  TASK-050 would have to write the organizer mapping twice.
- `tramflow_ml.ingestion.normalize` — `STREAM_FIELDS`, `IDENTIFIER_FIELDS`,
  `TIMESTAMP_FIELDS`, `TARGETS`, `UNIT`, `SCHEMA_VERSION`. The field register is
  already defined there; a second copy would drift.
- `tramflow_ml.identity` — `CanonicalCatalog`, `identity_crosswalk`,
  `AlignmentConfig`, `align_event`, and the `Matched` / `Unmatched` /
  `Ambiguous` / `Stale` outcomes. Join coverage reports in that vocabulary.
- `tramflow_ml.features.policy.POLICIES` — the declared lag, rolling-window and
  season reach of each horizon, which is what "enough history" means.

`contracts/data_v1.py` is a test oracle only, reached through the
`sys.path.insert` idiom already used by `ml/tests/test_ingestion.py`. Production
intake code never imports `contracts`.

Terms used below: a **canonical field** is a `data.v1` event field; a **source
column** is whatever the sample calls it; a **profile** is the operator-written
mapping between them; **classification** is the role intake assigns a canonical
field, which decides what may be printed about it.

## 3. Scope and non-goals

In scope: file and column discovery, the actionable unknown-schema failure and
its profile skeleton, per-field missingness, duplicate and conflict rates,
observed date span and per-date coverage, unit/target detection, join coverage
against a catalog, horizon and target supportability, a deterministic report, and
a second fixture schema proving the report describes the data rather than its
encoding.

Non-goals, stated so they are not mistaken for omissions:

- **No organizer column names.** Nothing maps by name similarity, synonym list or
  position. Only an exact canonical-name match auto-maps, which is identity, not
  inference. The real mapping is TASK-049/050 and the skeleton is its input.
- **No fold plan.** The report gives the count of complete buckets left after the
  deepest feature reach — an upper bound on evaluable folds — not a fold schedule.
- No normalization, no writes into the input, no network, no new dependency.
- No CLI wiring for the second fixture schema's profile as a built-in: the
  alternate schema is a test fixture, and shipping it as a named built-in would
  invite someone to reach for it on real data.

## 4. Acceptance

1. Read-only: SHA-256 of every file under `--input` is unchanged after a run, and
   no entry is added or removed. `--output` inside `--input` is refused.
2. An unknown schema exits 2 with a message that names the stream, the file, the
   observed columns, the required canonical fields, the unmapped ones with a
   one-line statement of what each must carry, the unused columns, and a profile
   skeleton whose unmapped entries are `null`.
3. No raw passenger identifier reaches the report. The rule is stated in §5 and
   tested against a fixture whose identifier columns carry card-number-shaped
   values: none of those values appears anywhere in the report bytes.
4. Two fixture schemas — the tiny synthetic JSONL fixture and a CSV rendering of
   the same events with different column names and a `%d.%m.%Y %H:%M:%S`
   timestamp format — produce byte-identical `streams` and `supportability`
   sections. Only the `source` section, which describes the encoding, differs.
5. The report states per horizon whether it is supportable and, when it is not,
   the required and the observed span in the same units.
6. Determinism: two runs on the same input, and a run on a byte-identical copy of
   the input at a different absolute path, produce identical report bytes.
7. `make ml-check` clean; `make check` exit 0.

Unchanged behaviour: `ingest`, `generate-synthetic` and `evaluate` keep their
current output and exit codes; the intake package has no consumer in `backend/`.

## 5. Decisions

1. **Mapping is explicit or identical, never inferred.** A canonical field maps to
   a source column when the profile says so, or when a column carries exactly the
   canonical name. Any other correspondence is an operator decision recorded in a
   profile. A required field with no mapping is a schema failure, not a null
   column.

2. **Identifier suppression is by role, never by value.** A canonical field is an
   *identifier* when it is in `ingestion.normalize.IDENTIFIER_FIELDS`
   (`event_id`, `route_id`, `direction_id`, `stop_id`, `vehicle_id`,
   `entity_version`, `source_version`). A source column that maps to nothing is not
   profiled at all — only named under `unused_columns` — because intake does not
   know what it holds and the safest summary of an unknown column is none. An
   identifier is
   summarised only by: present/missing counts, missing rate, distinct-value count,
   minimum and maximum character length, and a character-class signature drawn
   from a fixed code-defined alphabet (`digits`, `letters`, `alnum`,
   `alnum_punct`, `other`). Never a value, never a sample, never a most-frequent
   value, never a hash of a value.

   The general invariant behind it: **every string in the report is either a
   constant defined in our code, a column or file name read from the sample's
   schema, or a derived number/ISO-8601 date.** Column and file names are echoed
   deliberately — requirement 2 of this task is that the failure names the columns
   it found — and they are schema, not passenger data. Values are never echoed,
   including from enumerated fields: `target` and `unit` counts are reported only
   for members of the code-defined allowlists (`TARGETS`, `UNIT`), and anything
   outside them is counted as `other` without being quoted.

3. **Classification decides what may be printed**, in four kinds:
   `identifier` (above), `timestamp` (min and max instant, parse-failure count),
   `measure` (min, max, and for integers the sum — `stop_sequence`, `latitude`,
   `longitude`), `enumerated` (counts per allowlisted member plus `other`;
   `schema_version`, `target`, `unit`, `synthetic`).

4. **Missing has one definition across encodings**: the key is absent, the value
   is JSON `null`, or the value is a string that is empty or only whitespace.
   Without this, a CSV — where every column exists on every row — could never
   reconcile against a JSONL fixture that omits keys.

5. **CSV values are coerced** to int, float and bool exactly as
   `ingestion.normalize` coerces them, so a measure's min/max reconcile across
   encodings instead of comparing strings to numbers.

6. **Duplicates are keyed on `event_id`** and split the way ingestion splits them:
   a repeated key with an identical canonical payload is a *repeat*, a repeated
   key with a different payload is a *conflict*. Reusing that split means the
   intake report predicts what `ingest` will later count, instead of offering a
   second, differently-defined duplicate rate.

7. **Join coverage uses the identity vocabulary and an identity crosswalk.** With
   no organizer crosswalk in existence, coverage is measured with
   `identity_crosswalk(catalog, …)`, which maps each canonical id to itself; the
   report records `crosswalk: "identity"` so the number is never mistaken for a
   certified join rate. Outcomes are `matched` by kind, `unmatched` by reason,
   `ambiguous`, `stale` — the `tramflow_ml.identity` literals, no new words.
   Rows are aligned one at a time and tallied, so memory does not grow with the
   sample; `quality_report` takes a materialised sequence and a first sample may
   be large.

8. **Horizon supportability has one stated rule.** For horizon `H` with policy `P`
   (`features.policy.POLICIES`), the deepest history reach is
   `max(max(P.lags), max(P.rolling_windows), P.season_step * P.season_periods)`
   buckets of `P`'s granularity, and one further bucket is the forecast target.
   and one forecast period is a further `TARGET_BUCKETS[H]` buckets (24 hourly,
   31 daily, 12 monthly; the month uses the longest calendar month so the verdict
   cannot flip on which month a sample ends in). `H` is supportable when (a) the
   observed span yields `reach + TARGET_BUCKETS[H]` complete buckets and (b) the
   observed civil dates cover at least `MIN_COVERAGE_RATIO` of the span. Both
   thresholds are reported next to the observed values, so a "no" always carries
   the two numbers that produced it. The surplus is reported as
   `evaluable_buckets_upper_bound`: an upper bound on folds, not a fold plan.

9. **A target is supportable** when the stream carries a `target` value from
   `TARGETS` together with the single `UNIT` this layer can produce, and the
   `target`/`unit` fields were mapped at all. An unmapped `target` column makes
   every target undetermined rather than assumed.

10. **Determinism**: the report carries no wall clock, no absolute path (file
    basenames only), and every mapping is emitted with sorted keys. Floats appear
    only as measured minima/maxima and rates rounded to a fixed number of decimal
    places.

11. **Exit codes follow `ingest`**: 0 success, 1 a failed invariant of the run
    itself, 2 usage or input error — and an unreadable schema is an input error.

## 6. Research evidence

No new algorithm, technology or dependency: the work is composition of contracts
that already exist in this repository (`ingestion.normalize` field register,
`identity` outcome vocabulary, `features.policy` horizon reach). Under the root
`AGENTS.md` rule on research, no external search is claimed and none was needed;
the authority for every rule above is a file in this checkout, cited in §2.

The one judgement not taken from a repository contract is `MIN_COVERAGE_RATIO`.
It is a threshold, not a fact, and is therefore a named constant reported next to
the value it judges, in the same spirit as the identity tolerances.

## 7. Validation and recovery

Planned, each recorded below with observed output:

- `make ml-check` — ruff, mypy strict, pytest.
- `make check` — full gate, with the counts it prints.
- `tramflow-ml intake` against the tiny synthetic fixture: the full report.
- The same against the alternate CSV schema, with the reconciliation side by side.
- The same against a deliberately unknown schema: the verbatim failure.
- Two runs plus a relocated copy: identical report bytes.

Recovery: the package has no consumer; reverting the commits removes the
subcommand and the package and leaves `ingest`, `generate-synthetic` and
`evaluate` untouched.

### Progress

Implemented 2026-09-25 as `ml/src/tramflow_ml/intake/` — `records` (types,
classification, field contracts), `profile` (the `intake-profile.v1` document and
the fill-in skeleton), `discover` (file and column discovery, the actionable
refusal), `fields` (the four accumulators), `join` (identity-vocabulary tally),
`supportability` (span, horizons, targets) and `report` (the run). Largest module
is `report.py` at 337 lines; the longest function is 31 lines (`_policy_support`). Tests:
`ml/tests/test_intake_{report,schemas,failures,privacy,cli}.py`, 46 cases.

Two things changed from the plan as written, both recorded above:

1. Decision 8 originally required `reach + 1` buckets. That is wrong for a year
   horizon, whose forecast period is twelve monthly buckets, not one. The rule now
   adds a whole forecast period (`TARGET_BUCKETS`) and the month uses 31 days so
   the verdict cannot flip on which month a sample happens to end in.
2. Decision 2 originally said an unmapped source column is *treated as* an
   identifier. It is stronger and simpler not to profile it at all: an unmapped
   column is named under `unused_columns` and nothing else is computed from it, so
   there is no accumulator that could hold its values.

One test was wrong on first run and was corrected without touching the
implementation: `test_failure_quotes_no_value_from_the_sample` used a fixture row
whose route value was `14`, which collides with the literal `14` in
`unmapped, required (14):`. The assertion was right and the fixture was careless;
the value became `A-14` so the blanket "no cell of the sample appears in the
message" assertion stays blunt rather than being narrowed to selected values.

### Validation

All commands run from the worktree with the mandated literal `PATH` prefix.

- `make bootstrap` (`sync-all` + `frontend-install`): resolved the workspace and
  `npm ci` added 395 packages, `found 0 vulnerabilities`. `sync-ml` was never run
  alone.
- `make ml-check`: `ruff check ml` → `All checks passed!`; `mypy ml/src` →
  `Success: no issues found in 40 source files`; `pytest ml/tests` →
  `311 passed in 6.99s` (46 intake tests, 265 pre-existing).
- `make check`: exit 0. `Architecture boundaries passed.`; backend ruff clean,
  mypy `no issues found in 42 source files`, `292 passed, 10 skipped in 14.54s`;
  ML as above; golden evaluation `"passed": true`; frontend `8 passed (8)` files /
  `47 passed (47)` tests and a production build `built in 601ms`; contract check
  `OpenAPI snapshot is current`; reference contracts ruff clean, mypy 3 files,
  `119 passed`; `docker compose config --quiet` silent.
- Tiny synthetic fixture (64 unique validations, 67 rows, 12 telemetry rows,
  2024-01-01 – 2025-12-31): `rows 67 = readable 67`, `distinct_keys 64`,
  `repeated_rows 3`, `conflicting_rows 0` — the three injected duplicates that
  `generation.json` declares. `date_span` 731 days with 64 observed dates
  (`coverage_ratio 0.087551`). Join coverage 67/67 and 12/12 `exact_id`, zero
  unmatched, ambiguous, stale or unalignable. All three horizons report
  `supportable: false`; `year` additionally carries
  `insufficient_history: policy 'year/month' reads 36 monthly buckets of history
  and forecasts 12 more, so it needs 48; the observed span of 731 days yields 24`.
  `synthetic_boardings` is supportable; `validation_count` is
  `absent: no row declares the target 'validation_count'`.
- Second schema (same events as CSV, sixteen renamed columns,
  `%d.%m.%Y %H:%M:%S` naive Moscow timestamps, files `boardings.csv` /
  `positions.csv`): `streams` and `supportability` compared equal as whole
  sections (`a["streams"] == b["streams"]` → `True`,
  `a["supportability"] == b["supportability"]` → `True`). Rows 67/67, distinct
  keys 64/64, repeats 3/3, span 2024-01-01 – 2025-12-31 on both, first `event_at`
  `2024-01-01T18:57:00+03:00` on both, `stop_sequence` sum 99/99, matched
  `exact_id` 67/67 and 12/12, year buckets 24 observed against 48 required on
  both. Only `source` differs: profile `canonical` vs `alternate-fixture`, format
  `jsonl` vs `csv`, `timestamp_format` `None` vs `%d.%m.%Y %H:%M:%S`, file
  `validations.jsonl` vs `boardings.csv`, `event_id` column `event_id` vs
  `row_key`.
- Unknown schema (`ticket_no,line,platform,ts,tram` CSV): exit 2, stdout empty,
  and the stderr checklist names all five columns, all fourteen required
  canonical fields with a one-line contract each, `mapped (0): -`,
  `columns not used (5): …`, the statement that nothing is mapped by similarity,
  a skeleton whose sixteen `columns` entries are `null`, and the deferral to
  TASK-049/TASK-050. No cell value from the sample appears in it.
- Read-only and determinism: SHA-256 of all 5 fixture files taken before and after
  three runs — `diff` empty. Two runs on the same directory plus one on a copy at
  a different absolute path all produced
  `43178877b5e089743d5df996d5bb76dde4ba95f0c2dfeee207b649894ec36596`.
- Privacy: a fixture whose `event_id`, `vehicle_id` and `source_version` carry
  card- and ticket-shaped values produces a report containing none of them; every
  identifier summary carries exactly the eight permitted keys; a `unit` value
  outside the allowlist is counted as `other` and never quoted.

Recovery: the package has no consumer; reverting the commits removes the
subcommand and the package and leaves `ingest`, `generate-synthetic` and
`evaluate` untouched.

### Not verified

- No real organizer sample exists, so the actionable failure is judged on an
  invented foreign schema. Whether its wording is the right wording for the real
  extract is TASK-049's finding, not this task's claim.
- `MIN_COVERAGE_RATIO = 0.5` is asserted, not measured. Nothing tells us that half
  the dates is the right bar; it is a named constant reported next to the value it
  judges so a reader can disagree with it in one place.
- Memory was not measured on a large sample. Intake keeps one dictionary entry per
  distinct `event_id`; the million-event fixture was not profiled, and the README
  says to profile a slice instead.
- Join coverage under the identity crosswalk is only meaningful for a sample
  already keyed by catalog ids. On real data the figure will be near zero until
  TASK-050 supplies a crosswalk, which is the honest answer, not a defect.
