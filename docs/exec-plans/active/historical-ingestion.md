# TASK-017: bounded historical ingestion with restart and quarantine

## Purpose and observable result

`tramflow-ml ingest --input <fixture dir> --output <run dir>` turns a synthetic
fixture directory (TASK-016 format: `entities.json`, `validations.jsonl`,
`telemetry.jsonl`, `manifest.json`) into normalized `data.v1` event streams plus
a quarantine stream and an ingestion manifest whose counts reconcile exactly to
the input row count. The run can be killed after any chunk and resumed; the
resumed run produces byte-identical outputs and an identical manifest. Peak
memory depends on the configured chunk size and the small entity catalog, not
on the number of input rows.

## Context

Base `4478d43` (merge of TASK-016) in worktree
`/home/chessnok/hacks/MosTransport2026Hack-worktrees/historical-ingestion`,
branch `agent/historical-ingestion`. Input format and count semantics are
documented in `ml/README.md` ("Synthetic fixtures") and produced by
`ml/src/tramflow_ml/synthetic.py`. Row shape is `contracts/data_v1.py`
(`ValidationEvent`, `TelemetryEvent`, `EntityCatalog`; strict, `extra="forbid"`,
identifier pattern `^[A-Za-z0-9_.:/-]+$`, 1–128 chars, timezone-aware
timestamps, `available_at >= event_at`, target/synthetic agreement, finite
latitude/longitude in range). The dataset manifest is
`contracts/forecast_v1.DatasetManifest`. Contracts are test oracles only; the
production package does not import `contracts` (same rule as TASK-016).

Terms: *input row* = one physical line of an event file. *valid* = normalized
and written. *duplicate* = same `event_id` and identical normalized payload as
an earlier kept row (policy: keep first, count later). *conflicting duplicate*
= same `event_id`, different payload; quarantined, never silently dropped.
*quarantined* = any row not written to a normalized stream, with a reason code.

Ownership: `ml/src/tramflow_ml/ingestion/` (new package), an `ingest`
subcommand in `ml/src/tramflow_ml/cli.py`, `ml/tests/test_ingestion*.py`, this
plan, and one "## Historical ingestion" section in `ml/README.md`. Nothing else;
`identity.py` belongs to another agent.

## Scope and non-goals

In scope: offline chunked readers (JSONL and single-line-per-record CSV through
one adapter interface), a configurable column adapter with a built-in synthetic
adapter, streaming SHA-256 of inputs, versioned normalization, atomic
checkpoints with resume, bounded on-disk deduplication, quarantine with reason
counts, reconciliation, and an ingestion manifest written last.

Non-goals: organizer adapters (no samples yet), identity alignment, any
distributed or database stack, aggregation/features, multi-line quoted CSV
fields, and timing fields inside hashed outputs.

## Acceptance

- (a) Per stream, `input_rows == valid + duplicates + quarantined`, where
  quarantined includes conflicting duplicates. Hand-counted: tiny fixture
  (64 unique + 3 duplicates → 67 validation rows, 12 telemetry rows) yields
  valid 64 / duplicates 3 / quarantined 0 and 12 / 0 / 0.
- (b) A run interrupted after chunk *k* and resumed produces the same SHA-256
  for `validations.jsonl`, `telemetry.jsonl`, `quarantine.jsonl` and
  `manifest.json` as an uninterrupted run. Manifest and outputs contain no
  wall-clock or path-dependent fields.
- (c) Peak RSS of the million-event run stays under the declared ceiling and
  is of the same order as a 100 000-event run with the same chunk size.
- Resume with a changed input file, changed normalization version or changed
  chunk size fails loudly before touching outputs.
- Existing `evaluate` and `generate-synthetic` commands, their tests and
  outputs are unchanged.

## Predeclared budget (million-event fixture, declared before measuring)

Input: `tramflow-ml generate-synthetic --mode million` (1 058 823 validation
lines = 1 000 000 unique + 58 823 duplicates; 200 000 telemetry lines;
`source_hash f68c2eb0…`). Chunk size 10 000. Machine: x86_64, 16 logical CPUs,
Python 3.13.9.

| Measure | Declared ceiling |
|---|---|
| Wall time (`/usr/bin/time -v`, uninterrupted run) | ≤ 240 s |
| Peak RSS | ≤ 256 MiB |
| Throughput (all input rows / wall) | ≥ 5 000 rows/s |
| Expected counts | validations 1 000 000 valid, 58 823 duplicates, 0 quarantined; telemetry 200 000 valid, 0, 0 |

## Decisions

1. **Package layout.** `tramflow_ml/ingestion/` with `records.py` (types,
   constants, errors), `readers.py` (streaming hash, offset-tracking line
   chunks, JSONL/CSV decoders), `normalize.py` (catalog index and rule checks),
   `dedup.py` (SQLite index), `checkpoint.py` (atomic checkpoint, resumable
   output writers), `pipeline.py` (`ingest`, manifest). Each file stays well
   under 400 lines.
2. **Input immutability.** Every input file is hashed with SHA-256 in fixed
   1 MiB blocks before processing; hash and byte size are stored in the
   checkpoint and manifest. Resume re-hashes and refuses on mismatch
   (`InputChangedError`).
3. **Normalization `normalization.v1`.** Output rows contain exactly the
   `data.v1` contract fields, canonical JSON (`sort_keys`, compact separators,
   `ensure_ascii=False`, trailing newline — the TASK-016 encoding). Timestamps
   are parsed (ISO 8601 by default, optional `strptime` format and
   assumed timezone for naive sources) and re-emitted as ISO 8601 in
   `Europe/Moscow`. Booleans, integers and floats are coerced from strings only
   for CSV sources; JSONL sources must carry native JSON types.
4. **Adapter.** `ColumnAdapter(name, columns, constants, timestamp_format,
   assume_timezone)`: canonical field → source column, fixed values for columns
   absent from the source, and timestamp options. The built-in `synthetic`
   adapter is the identity mapping. Readers share one interface: a binary line
   iterator with byte offsets plus a per-line decoder (`json.loads` or
   `csv.reader` on the single line, header from line 0). Multi-line quoted CSV
   fields are unsupported because byte-offset resumption needs one record per
   physical line; `pandas.read_csv(chunksize=…)` gives no offsets and, per
   PRE_HACKATHON_ANALYSIS, does not bound the rest of the pipeline anyway.
5. **Chunks and checkpoint.** Streams are processed in order (`validations`,
   then `telemetry`) in chunks of `chunk_size` lines. After each chunk:
   outputs are appended and flushed, the SQLite index is committed with the
   chunk's commit sequence number, then `checkpoint.json` is written via
   tmp + `os.replace`. The checkpoint stores normalization version, chunk
   size, input hashes, per-stream byte offset / row index / counts / reason
   counts, the commit sequence, and per-output byte length plus SHA-256 of that
   prefix. Resume truncates each output to its checkpointed length, re-hashes
   the prefix and refuses if it differs, deletes SQLite rows with a commit
   sequence beyond the checkpoint (covers a crash between SQLite commit and
   checkpoint replace), and continues from the stored offset. Because rows are
   processed in file order with deterministic encoding, the result is
   byte-identical to an uninterrupted run.
6. **Bounded deduplication.** An on-disk SQLite table
   `seen(event_id PRIMARY KEY, payload_hash, commit_seq)` with
   `PRAGMA cache_size = -8192` (8 MiB page cache), `journal_mode = WAL`. Per
   chunk one batched lookup (`IN` lists of 500 ids), in-memory resolution of
   intra-chunk repeats, one `executemany` insert. Exactness matters for
   reconciliation: a fixed-size hashed set would misclassify unique rows as
   duplicates on collisions, so it was rejected. Memory is bounded by chunk
   size plus the SQLite cache; disk grows with unique ids.
7. **Quarantine.** `quarantine.jsonl` rows: `stream`, `row_index`, `reason`,
   `detail`, `raw` (the raw line decoded with replacement). Reason codes:
   `decode_error`, `missing_field`, `invalid_type`, `invalid_value`,
   `invalid_timestamp`, `availability_before_event`, `unknown_entity`,
   `conflicting_duplicate`. Counts per stream and reason go to the manifest.
8. **Reconciliation and manifest.** `manifest.json` (`ingestion.v1`) is written
   last via tmp + replace and holds normalization version, chunk size, adapter
   and format, the propagated source manifest, input inventory, per-stream
   counts, output inventory and an `output_hash` over the encoded inventory.
   `ingest` raises `ReconciliationError` when any stream fails the identity;
   the CLI exits 1 for that, 2 for usage/input errors, 0 on success. Timing is
   printed by the CLI only, never written to hashed files.
9. **Run directory rules.** `manifest.json` present → refuse (already
   complete). `checkpoint.json` present → resume. Otherwise start fresh,
   truncating the known output names. Foreign files in the run directory cause
   a refusal so an unrelated directory is never clobbered.

## Progress

- 2026-09-24: plan written; budget declared above before any measurement.
- 2026-09-24: package `ml/src/tramflow_ml/ingestion/` (records, readers,
  normalize, dedup, checkpoint, pipeline), `ingest` CLI subcommand, 17 tests in
  `ml/tests/test_ingestion.py` / `test_ingestion_cli.py`, README section.
  Deviation from decision 6: the SQLite primary key is `(stream, event_id)` so an
  id reused across streams is never mistaken for a duplicate. Deviation from
  decision 4: `pandas.read_csv` is not used at all; the `csv` module decodes one
  physical line at a time so CSV and JSONL share the same offset-tracking reader.
  Interruption tests inject the failure after the SQLite commit and after the
  checkpoint replace, which exercises the index rollback path.

### Million-event measurement (2026-09-24, observed after the declaration)

Input `source_hash f68c2eb03a4381ea000618bc00290dc1730181297bf1491c9d9b93cc6abcb96b`
regenerated into scratch (generation 11.70 s, 39.8 MB peak). Ingestion with the
default chunk size 10 000 under `/usr/bin/time -v`:

| Measure | Declared ceiling | Observed |
|---|---|---|
| Wall time | ≤ 240 s | 35.64 s (user 33.98 s, sys 1.21 s) |
| Peak RSS | ≤ 256 MiB | 57.3 MB (`Maximum resident set size 57332 kB`) |
| Throughput | ≥ 5 000 rows/s | 35 437 rows/s (1 258 823 input rows) |
| Counts | 1 000 000 / 58 823 / 0; 200 000 / 0 / 0 | exactly as declared, `reconciled: true` for both streams |

Outputs: `validations.jsonl` 452 888 896 B
(`c3128e8e0b9a65060ef8adef8742bf5e35ceaf06b685d4cbee2240e3cd21d558`),
`telemetry.jsonl` 87 877 784 B (`306bde40…`), empty `quarantine.jsonl`,
`manifest.json` `e990cc3d…`, `output_hash 7b4ac39e…`.

Memory independence (acceptance c): a 100 000-event fixture (105 882 + 20 000
rows) with the same chunk size peaked at 57.2 MB versus 57.3 MB for 12× more
rows; the SQLite index file grew on disk instead.

Restart (acceptance b): the same million command was killed with SIGKILL after
12 s (`checkpoint.json` at `commit_seq 46`, 460 000 validation rows processed,
WAL and index present). Rerunning the identical command resumed (21.52 s,
57.0 MB peak) and produced the same four SHA-256 digests and a byte-identical
`manifest.json` (`cmp` empty). The unit tests repeat this at crash points 1, 4
and 7 on the tiny fixture and after an index commit without a checkpoint.

### Verification

- `pytest ml/tests/test_ingestion.py ml/tests/test_ingestion_cli.py`: 17 passed.
- `make ml-check`: ruff and mypy strict clean, 89 passed.
- `make sync-backend && make check`: first attempt failed only at
  `frontend-check` because the worktree had no `frontend/node_modules`
  (a global ESLint 6 ran); after `make frontend-install` it passed with exit 0:
  architecture, backend 292 passed / 10 SQL skipped, ML 89 passed, golden
  evaluation, frontend 47 passed and production build, API drift, 119
  reference-contract tests, Compose.
- `git diff --check`: clean. No new dependency, no generated data committed.
- Not verified: organizer data (no samples), and the RSS ceiling on a machine
  with a different SQLite build; the 8 MiB cache pragma is the only tunable.

## Validation / recovery

Commands to run and record: `pytest ml/tests/test_ingestion*.py`, `make
ml-check`, million run under `/usr/bin/time -v` into
`/home/chessnok/.claude/jobs/398af623/tmp/ingest-*`, one interrupted+resumed
million run compared by SHA-256, `make sync-backend && make check`,
`git diff --check`. Recovery: a run directory without `manifest.json` is
incomplete; rerunning the same command resumes from `checkpoint.json` or, when
the checkpoint is absent, starts over. Deleting the run directory is always a
safe full restart. No database, dependency or deployment change.
