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

   **Column names are untrusted too, and are judged a line at a time.** A per-cell
   test cannot work: a datum can look like a name (`MSK4276380155129043` is a valid
   identifier), so the safe set and the word-like set overlap. What makes a header a
   header is that *every* cell of it is word-like (`str.isidentifier`); one failure
   condemns the line, and every cell is then rendered as `<column N: LEN SIGNATURE>`,
   including cells that would have passed alone. The same holds for a JSON Lines key
   set. Real names are still used for matching, so a profile that names a column works
   whether or not the name prints. A CSV profile may declare `has_header: false`, which
   both stops row one being eaten as a header and addresses the columns positionally as
   `column_1`, `column_2`, ….

   The invariant, stated at the width it actually holds: **no cell of the sample is
   ever quoted, including one that arrives labelled as a column name.** Beyond
   code-defined constants and derived numbers and instants, the report does carry
   word-like column names, file names in the sample directory, the catalog's
   `entity_version`, and the exact minimum and maximum of each measure field. The last
   of those are real single-row values — GPS coordinates for telemetry — so
   TASK-049/TASK-050 must not map a column carrying personal data onto a measure field.

3. **Classification decides what may be printed**, in four kinds:
   `identifier` (above), `timestamp` (min and max instant, parse-failure count),
   `measure` (min, max, and for integers the sum — `stop_sequence`, `latitude`,
   `longitude`), `enumerated` (counts per allowlisted member plus `other`;
   `schema_version`, `target`, `unit`, `synthetic`).

4. **Missing has one definition across encodings**: the key is absent, the value
   is JSON `null`, or the value is a string that is empty or only whitespace.
   Without this, a CSV — where every column exists on every row — could never
   reconcile against a JSONL fixture that omits keys.

5. **Values are canonicalised by field contract, not by observed Python type.**
   CSV strings are coerced to int, float and bool, and an integer-contract field
   accepts `0.0` as `0` so a CSV written from a float-typed column reconciles with
   the same fact in JSON. Coercion is deliberately *more permissive* than
   `ingestion.normalize`, which is why a second count exists: `out_of_contract`
   reports values the pipeline will quarantine (`stop_sequence` negative or
   non-integral, a coordinate out of range), so `unparsed: 0` is never a clean bill
   on a column `ingest` will reject wholesale.

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
   buckets of `P`'s granularity, and one forecast period is a further
   `TARGET_BUCKETS[H]` buckets (24 hourly, 31 daily, 12 monthly; the month uses the
   longest calendar month so the verdict cannot flip on which month a sample ends
   in). `H` is supportable when (a) the observed span yields
   `reach + TARGET_BUCKETS[H]` complete buckets and (b) the observed civil dates
   cover at least `MIN_COVERAGE_RATIO` of the span. A bucket is complete only when
   it lies wholly inside `[first_instant, last_instant]`, at every granularity.
   Both thresholds are reported next to the observed values, so a "no" always
   carries the two numbers that produced it. The surplus is reported as
   `evaluable_buckets_upper_bound`: an upper bound on folds, not a fold plan.

9. **A target is supportable** when the stream carries a `target` value from
   `TARGETS` together with the single `UNIT` this layer can produce. `target` and
   `unit` are required fields, so discovery refuses before supportability is reached
   if they are unmapped; the verdict therefore always describes values that were
   actually read, never an assumed default.

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

### Review record (2026-09-25)

Independent review of `9fd34af`: **REJECT**, with one CRITICAL and one HIGH. The
acceptance validation of the same commit passed all six criteria — it planted canary
tokens in `event_id`, `vehicle_id` and unmapped columns, grepped stdout, stderr and the
report file across the success path and six failure paths, found zero leaks, and
reproduced the `43178877…c36596` digest from a fixture it generated itself. It passed
because **every fixture it built had a CSV header.** The reviewer tried a headerless
one. That is the gap: the validation explored the space the implementation had defined,
and the defect lived in an assumption neither the code nor the tests had written down.

| Severity | Finding | Fix |
|---|---|---|
| CRITICAL | C1 — `read_csv_header` takes the first physical line as the header unconditionally, so a headerless CSV's row-one cells become "column names" and are echoed verbatim; `4276380155129043` appeared four times in one refusal, and with a profile also in the report file. The identifier digest machinery was bypassed because the value arrived labelled as *schema*, the one category the invariant permitted printing. | Column names are untrusted, and — after C1b below — are judged a line at a time. `intake/columns.py` renders a condemned line's cells as `<column N: LEN SIGNATURE>`; real names are still used for matching, so profiles are unaffected. A CSV profile may declare `has_header: false`, which stops row one being consumed as a header and addresses columns as `column_1…`. |
| CRITICAL | C1b — the first fix judged names **one cell at a time**, so `ZZLEADCARDZZ4276380155129040` printed four times: `"…".isidentifier()` is `True` for letters followed by digits. The defect was the shape of the rule, not the strictness of the predicate — a transit card serial with a letter prefix, a ticket reference, a surname and a device tag are all valid identifiers. `isidentifier` happened to reject all five cells the first reviewer planted, which is why the fix looked complete: it was calibrated to those cells rather than to the class. Tightening further cannot work, because the safe set and the word-like set genuinely overlap. | The unit of trust is the **line**. A header is a line whose *every* cell is word-like; one failure condemns the line and every cell is shown by shape and position, including cells that would have passed alone. The same rule covers a JSON Lines key set. The "looks headerless" diagnosis now fires whenever any cell fails, which is the case worth catching — it did not fire on the mixed fixture before. A genuine header is untouched. Two alternatives were rejected: widening the per-cell test to admit `Stop Name` would let a headerless line of uniformly name-shaped cells pass as a header, and comparing row one's shapes against row two's false-positives on real headers, since `stop_id` and `synthetic:stop:1` share the `alnum_punct` signature. |
| HIGH | H1 — `_json_keys` unioned keys over the first 200 lines, so a 400-row file whose `vehicle_id` starts at row 251 was **refused** for a field it carries; worse, writing exactly the profile the checklist asks for gave an identical refusal, because the mapping check also consulted the 200-line key set. The only escape was to fabricate a constant. | The key set is now the whole file, and an explicit `profile.columns` entry always takes effect regardless of what was observed. The sampling limit is gone rather than disclosed. On JSON Lines a declared key no row carries is reported as `missing_rate: 1.0` and listed under `declared_columns_never_seen`; on CSV, where the header is the schema, it is refused by name (M6). |
| MEDIUM | M1 — `as_number` accepted `-1` and `2.5` for `stop_sequence` and `999.0` for `latitude` and reported `unparsed: 0`, a clean bill on rows `ingest` quarantines wholesale. Plan decision 5 claimed coercion matched `ingestion.normalize` "exactly"; it did not. | `MeasureContract` per field (non-negative integer; ±90; ±180) and a second count, `out_of_contract`, beside `unparsed`. The `sum` is withheld when either is non-zero. Decision 5 now states that coercion is deliberately more permissive and says why the second count exists. |
| MEDIUM | M2 — a CSV spelling integers as `0.0`, which is what `pandas.to_csv` emits for a float-typed column, flipped the `integral` flag, nulled `sum`, and made `streams` unequal against the same facts in JSON. The same split fed the payload digest, so one `event_id` written `0` in one file and `0.0` in another counted as a *conflicting duplicate* that is not one. | Numbers are canonicalised by field contract before being summarised or digested; `integral` is keyed off the contract, not the observed type. `canonical_text` does the same for identifiers so `14` and `14.0` are one value. A `float_integers` variant of fixture B is now part of the reconciliation suite. |
| MEDIUM | M3 — hourly and daily counted partial first and last civil dates as complete while monthly refused a part-month, so an 8-day span starting at 23:00 reported 192 complete hourly buckets. | One rule at every granularity: a bucket counts only when it lies wholly inside `[first_instant, last_instant]`. `ObservedSpan` carries the instants. The tiny fixture's counts move from 17544/731/24 to 17519/729/22. |
| MEDIUM | M4 — the `--output` write sat outside the `try`, so an unwritable path raised a raw `PermissionError`/`IsADirectoryError` against a documented 2/1/0 register. | The write is wrapped; an `OSError` becomes `cannot write --output …` and exit 2. Two tests. |
| MEDIUM | M5 — a duplicate CSV column gave `validations.csv: validations.csv: CSV header needs unique non-empty names` and never said which column repeated. | Intake reads the header itself and names the colliding positions and label: `the header repeats a column name at positions 1 and 3 (a)`. |
| MEDIUM | M6 — a typo'd column in a profile was silently ignored. | On CSV the refusal now leads with `profile.columns names columns absent from <file>: [...]`. |
| LOW | L1 zero-byte file diagnosed as an encoding problem. L2 the invariant sentence was wider than the truth. L3 `UnreadableReason` unreferenced with an unproducible member. L4 `UNPARSED_VALUE` unreferenced while the literal was hard-coded. L5 the `_TRUE_STRINGS` copy was undocumented. L6 decision 9 described unreachable behaviour. L7 decision 8 held two contradictory rules from an editing artifact. L8 `coerce` was a dead parameter on two of four `Accumulator` implementations. | L1 says "is empty". L2 the README and decision 2 now state the invariant at the width it holds and name what the report *does* carry — including that a measure's exact min/max are single-row values, with the warning TASK-049/TASK-050 inherits. L3/L4 dead names removed, the constant used. L5 documented as a deliberate copy rather than a private import. L6/L7 rewritten. L8 `coerce` moved to the two constructors that use it. |

Accepted with reasoning rather than implemented: the reviewer suggested a JSON Lines
file missing a required key everywhere could report `missing_rate: 1.0` instead of
refusing. It does so once the key is declared in a profile, which is one line, but an
*undeclared* absent field still refuses — reporting it would silently delete the
checklist that is this task's central deliverable, since a wholly foreign JSONL is
exactly the case where every canonical name is absent. Both behaviours are tested.

Residual risk, disclosed rather than closed: a headerless file in which *every* cell is
word-like (`Ivanov,Petrov,Sidorov`) still prints those cells. The line rule narrows the
class sharply — one digit-leading, punctuated or spaced cell anywhere condemns the line —
but cannot eliminate it without a structural signal, and the only cheap structural signal
available false-positives on real headers.

One limitation the fix introduced and did not close: a headerless CSV is addressed
positionally through a single `columns` map shared by both streams, so two streams with
different column layouts cannot be described by one profile. The refusal is actionable
(M6 names the absent columns) and the README states the boundary; per-stream columns
would be the fix if real data needs it.
