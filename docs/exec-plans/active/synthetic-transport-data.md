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

Paused at user request on 2026-09-23. Implementation and CLI are checkpointed in
`agent/synthetic-transport-data`; not merged into main and not marked done.

Observed lead verification before checkpoint:
- `pytest ml/tests/test_synthetic.py -q`: 20 passed (wire schemas/catalog, counts,
  determinism/hash, calendar dates, gaps, destination preservation, failed writes,
  CLI outside repository cwd).
- `make ml-check`: Ruff/mypy passed, 70 tests passed.
- `make check`: exit 0; 292 backend passed / 10 SQL skipped, 70 ML passed,
  47 frontend and 119 reference-contract tests passed; architecture, types/lint,
  golden evaluation, production build, API drift and Compose passed.
- `git diff --check`: passed. No new dependencies or generated datasets committed.

Remaining before TASK-016 completion/integration:
1. Independent review of generator and CLI; address findings with regression tests.
2. Run the predeclared million-event budget measurement outside git and independently
   reconcile stream hashes/counts; performance is currently unverified.
3. Document CLI/count/gap semantics in ml/README.md and preserve measured evidence.
4. Run any affected focused checks and lead final gate; integrate onto latest main
   while preserving its session handoff/tracker changes.

Primary main contains completed contracts at b36ece3. Worktree and branch retained
with no runtime containers or generation jobs running. No push performed. Resume
this task before starting TASK-017; do not regenerate or discard another worktree.
