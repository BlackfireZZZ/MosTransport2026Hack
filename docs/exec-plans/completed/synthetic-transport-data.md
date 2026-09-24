# TASK-016: reproducible synthetic transport fixtures

## Purpose and acceptance

Produce deterministic multiyear validation/telemetry JSONL and provenance with
known totals, explicit gaps, directions, peaks, late rows and exact duplicate copies.
Same config/seed/version yields byte-identical files and SHA-256. Output is synthetic
boarding-event counts, never observed occupancy. Tiny and million-event CLI modes.
Existing evaluation behavior and HTTP code stay unchanged.

## Context and ownership

Base b36ece31a47e5530f350e21ecde68f34f97fb94a; primary clean.
Worktree `/home/blackfire/Hackatons/MosTransport2026Hack-worktrees/synthetic-transport-data`,
branch `agent/synthetic-transport-data`. Implementation agent owns synthetic.py;
lead owns CLI, tests and docs, final integration. Contract schemas are test oracles;
no production import of repository-only contracts or sys.path mutation.

## Contract and research

Unique validation count N; duplicates after every dth unique event produce floor(N/d)
extra rows. Late every lth event; telemetry every kth unique event. Zero disables
late/duplicate/gap injection; telemetry interval must be positive. Every configured
Nth calendar day has missing source coverage and no generated events. At least one
day must remain. Events span the remaining dates, endpoints included for N>1.
Event-time file order is not a feature-availability guarantee. Catalog has repeated
visits and same-name distinct stops; no passenger/card identifiers.

Files: entities.json, validations.jsonl, telemetry.jsonl, generation.json, manifest.json.
The inventory maps the first four names to SHA-256/byte size; canonical inventory
hash is manifest source_hash. Manifest is written last, not included in its own
hash. All bytes/config/timestamps independent of wall clock/output path. Destination
must not exist; partial failed output remains without manifest for diagnosis.
Consumer must require/validate manifest; no production atomic publisher claim.

Official Python hashlib docs support incremental byte hashing; random docs clarify
runtime sequence compatibility limits. Use versioned SHA-256 seed/index choices,
not global random state. Existing data.v1/DatasetManifest schemas and calendar
fixtures are the cross-boundary evidence. No new dependencies.
Sources: https://docs.python.org/3.13/library/hashlib.html and
https://docs.python.org/3.13/library/random.html (read via HTTPS with timeout).

## Verification / declared scale budget

Before execution: one million unique validations plus configured duplicates and
telemetry over 2024–2025 must finish within 120 wall seconds, peak RSS <=256 MiB,
and total output <=2 GiB on this x86_64 / 16 logical CPU environment. Capture
`/usr/bin/time -v` and file hashes; files live under /tmp outside git. This budget
checks fixture generation only, not historical ingestion/model accuracy/SLA.

Focused hand-counted/schema/hash/reproducibility/calendar/CLI/failure tests first,
then ML gate and make check. Independent review; root final gate and fast-forward
integration from clean recorded base. No deployment/DB/dependency change.

## Progress

Paused at user request on 2026-09-23 with implementation and CLI checkpointed in
`agent/synthetic-transport-data` at `65f455c`.

Observed lead verification at that checkpoint:
- `pytest ml/tests/test_synthetic.py -q`: 20 passed (wire schemas/catalog, counts,
  determinism/hash, calendar dates, gaps, destination preservation, failed writes,
  CLI outside repository cwd).
- `make ml-check`: Ruff/mypy passed, 70 tests passed.
- `make check`: exit 0; 292 backend passed / 10 SQL skipped, 70 ML passed,
  47 frontend and 119 reference-contract tests passed; architecture, types/lint,
  golden evaluation, production build, API drift and Compose passed.
- `git diff --check`: passed. No new dependencies or generated datasets committed.

Resumed 2026-09-24 on a new machine (uv 0.12.18, Python 3.13, Node 24.21).

### Million-event budget measurement (2026-09-24)

`/usr/bin/time -v tramflow-ml generate-synthetic --mode million --output <outside git>`
on x86_64 (`nproc` 16):

| Measure | Declared ceiling | Observed |
|---|---|---|
| Wall time | 120 s | 13.95 s (user 13.14 s, sys 0.79 s) |
| Peak RSS | 256 MiB | 42.0 MB (`Maximum resident set size 42000 kB`) |
| Output size | 2 GiB | 543 MB (validations 479 529 182 B, telemetry 87 877 784 B) |

Counts: unique 1 000 000, duplicates 58 823 = ⌊10⁶/17⌋, late 90 909 = ⌊10⁶/11⌋,
telemetry 200 000 = ⌊10⁶/5⌋; `validations.jsonl` has 1 058 823 lines,
`telemetry.jsonl` 200 000; 56 gap dates; `cell_totals` (10 785 cells) and
`hour_totals` both sum to 1 000 000. `source_hash`
`f68c2eb03a4381ea000618bc00290dc1730181297bf1491c9d9b93cc6abcb96b` was reproduced
by an independent script that re-hashed the four files and re-encoded the inventory.
The independent reviewer repeated the run (11.97 s, 30.9 MiB peak via `getrusage`)
into a different directory and obtained the same `source_hash`; 2 000 sampled rows
per stream plus catalog and manifest validated against `contracts.data_v1` /
`contracts.forecast_v1`. Two tiny runs into different paths produced identical
SHA-256 for all five files. This measures fixture generation only.

### Independent review and fixes (2026-09-24)

Review found no correctness defect. Addressed: `generate_dataset` split into
calendar/event/stream/report/manifest helpers with `TypedDict` return payloads so
the CLI's key access is type-checked; exact `hour_totals` oracles replaced a loose
peak inequality; dead re-validation removed; `.manifest.json.tmp` failure signal and
the `HOURS` weighting documented; CLI now reports `OSError` as a usage error, with
a subprocess test for invalid config and an in-process test for write failure.
Output bytes unchanged:
default, `--events 1000 --seed 7` and million runs before/after the refactor were
`diff -r` empty / same `source_hash`. `ml/README.md` documents CLI and count
semantics.

### Final gate

See tracker card for dated `make check` results at integration.
