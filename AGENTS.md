# AGENTS.md

## Repository mission

We are building a decision-support system for forecasting passenger flow on Moscow surface transport. Priorities are forecast and data correctness, explainability, reliability, delivery speed, and visual polish.

These rules apply to the entire repository. A nested `AGENTS.md` may refine them for its subtree, but it may not weaken the evidence requirements.

## Agent contract map

- Task specification template: `docs/agentic/TASK_SPEC.md`.
- Verification matrix: `docs/agentic/VERIFICATION_MATRIX.md`.
- Permission boundaries: `docs/agentic/PERMISSIONS.md`.
- Agent-to-agent handoff contract: `docs/agentic/HANDOFF.md`.
- Long-running execution plans: `docs/exec-plans/README.md`.
- Subtree-specific rules live in the nearest `backend/AGENTS.md`, `frontend/AGENTS.md`, or `ml/AGENTS.md`.

## Primary rule: evidence before changes

An agent must not modify files until it can state why the change should work correctly.

Before editing, the agent must:

1. State a falsifiable claim: which observable behavior will change and which behavior must remain unchanged.
2. Find an existing contract, test, type, migration, or authoritative source that supports the implementation approach.
3. Select the smallest check capable of disproving the solution: a unit or integration test, build, clean-database migration, SQL plan, or smoke test.
4. Inspect the affected architectural boundaries and use `rg` to find consumers of every changed contract.

Evidence is a reproducible chain: preconditions → implementation → verification → observed result. If the required verification cannot be run, do not apply the change; record the blocker and ask for a human decision.

## Research for complex solutions

Before introducing a new complex technology, algorithm, data model, security mechanism, scaling approach, or non-trivial UX pattern, search for comparable implementations online.

- Prefer official documentation, standards, papers by the technology authors, and engineering reports with measurements.
- For ML, prefer the primary paper, library documentation, and reproducible benchmarks.
- Never copy code blindly. Record the source context, similarities, differences, and risks for our data volume and SLA.
- Include the reasoning in the agent report. Create an ADR under `docs/decisions/` for a decision that is expensive to reverse.
- If internet access is unavailable, do not present model memory as research. State the limitation and rely on repository contracts.

## Required workflow

1. Read `README.md`, `DESIGN.md`, this file, and the nearest relevant architecture documentation.
2. Run `git status`; preserve other people's unfinished work.
3. State the hypothesis and acceptance criteria.
4. Research comparable solutions when the decision is new or complex.
5. Start with a test or contract, or explain why an existing check is sufficient.
6. Make the smallest coherent change in the correct layer.
7. Run focused checks, then `make check`; for infrastructure changes also validate Compose and run the smoke test.
8. Audit the diff for secrets, accidental generated files, boundary violations, and public-contract changes.
9. Report evidence, assumptions, and unverified risks. Never say “should work” without an observed command result.

## Isolate large tasks with git worktrees

A task is large when at least one condition is true:

1. It is expected to modify eight or more files, excluding generated files.
2. It affects three or more areas among `backend`, `frontend`, `ml`, Compose/infrastructure, and `.github`.
3. It changes a public API, database/Alembic schema, authentication or permissions, a production dependency, runtime/deployment/CI, or a data/feature/model contract.
4. It contains at least three independently verifiable implementation milestones or is expected to take more than 90 minutes or one session.
5. Two or more agents will edit files in parallel.

For a large task, the lead agent must automatically run `make agent-create ID=<task-slug> REF=<base-ref>` **before the first file edit** and perform the task in the returned dedicated worktree. Before verified integration, the primary checkout is read-only: inspection, search, and diff review are allowed; direct file edits are not. If the agent is already inside a dedicated worktree—the current path differs from the first `worktree` entry in `git worktree list --porcelain`—do not create a nested worktree.

Safe lifecycle:

1. Record the primary path, base SHA, current branch, and `git status`. Never stash, reset, or move another person's changes automatically.
2. Create a unique `agent/<task-slug>` branch and sibling worktree from the recorded base SHA. If required state exists only as uncommitted changes, stop and request a human decision.
3. Every writing agent works only in its assigned worktree and ownership area. Shared runtime resources must use unique project names, ports, and volumes.
4. Before cleanup, show the worktree status, branch, HEAD, and result location. Run `make agent-remove ID=<task-slug>` only after integration or explicit abandonment and only with a clean status. Never use `--force`, manual recursive deletion, delete an unpushed branch, or clean another agent's worktree.
5. The final report must include the base SHA, worktree path and branch, verification evidence, integration method, and cleanup result or reason for retaining the worktree.

## Parallel agent work

Parallelize independent research, reviews, test runs, and risk analysis through subagents. A file or contract has one owner at a time; parallel agents must not edit overlapping areas. The lead agent integrates results, resolves conflicts, and personally runs the final quality gate.

The required handoff format is defined in `docs/agentic/HANDOFF.md`. Parallel writes are allowed only in non-overlapping worktrees or ownership areas. Final integration and verification may not be delegated.

## Architecture boundaries

- `domain` must not import FastAPI, SQLAlchemy, Pydantic, or other framework code.
- `application` orchestrates use cases through protocols; HTTP and SQL do not belong there.
- `infrastructure` implements repositories, external clients, and ML adapters.
- `api` validates transport contracts and calls application services; handlers contain no business logic.
- Frontend features access HTTP only through `src/api` and feature hooks, never through direct `fetch` calls.
- `components/ui` contains local shadcn primitives without product logic.
- Training and batch inference remain separate from the online web worker.

A boundary exception requires an ADR, a rollback or migration plan, and a contract test.

## Data and ML

- Raw validations and telemetry are immutable; corrections create a new transformation version.
- Every dataset records its date range, feature version, `Europe/Moscow` timezone, and leakage protections.
- Time-series splits are chronological; random splits are forbidden.
- A baseline is mandatory. Accept a new model only when it improves agreed metrics across multiple temporal slices.
- Forecasts retain `model_version`, `generated_at`, horizon, and uncertainty intervals.
- Feature changes require schema tests and boundary tests for dates, time, and timezone behavior.

## Database and API

- Change the schema only through a new Alembic migration. Verify upgrade on a clean database and document recovery for destructive changes.
- APIs are backward-compatible by default. Removing a field requires a new version or deprecation period.
- Never read large tables without a time range and aggregation key.
- For expensive queries, verify indexes and run `EXPLAIN (ANALYZE, BUFFERS)` on representative data.
- Logs must not contain passenger identifiers or secrets.

## Frontend and design

- `DESIGN.md` is the source of truth for tokens, density, typography, states, and visualization.
- The dispatcher screen is a work surface: filters and results remain visible without a marketing hero.
- Every interactive state has loading, empty, error, and keyboard-accessible behavior.
- Color is never the only carrier of meaning. Numbers use tabular numerals.
- Add UI primitives through the shadcn CLI or official source and keep them local to the repository.

## Definition of done

A change is complete only when acceptance criteria are met; tests and static checks pass; migrations and contracts are synchronized; documentation is updated; no hidden fallback masks an error; and the report includes commands with their observed results.
