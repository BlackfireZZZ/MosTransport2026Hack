# Agent task tracker

This is the repository-local index of agent work. Read it before selecting a task
and update it when ownership, status, blockers, or verification evidence changes.
All entries and task specifications use English. An entry records work; it does
not authorize actions outside the user's scope or [permission boundaries](PERMISSIONS.md).

## Classification

| Field | Values and meaning |
|---|---|
| ID | Stable `TASK-NNN` identifier; never reuse an ID. The integration owner allocates IDs to avoid parallel collisions. |
| Type | `feature`, `bug`, `research`, `docs`, `maintenance`, `debt` |
| Area | One or more of `backend`, `frontend`, `ml`, `data`, `infra`, `ci`, `docs` |
| Priority | `P0`: active incident or correctness blocker; `P1`: blocks an agreed milestone; `P2`: normal planned work; `P3`: optional improvement |
| Risk | `R0`–`R3` as defined in [PERMISSIONS.md](PERMISSIONS.md); priority does not grant authority. |
| Owner | One named integration owner, or `unassigned`; record delegated file ownership in the specification. |
| Dependencies | Blocking task IDs, or `none`; prerequisites must be complete before the task is `ready`. |

| Status | Entry / exit condition |
|---|---|
| `backlog` | Captured outcome; scope, evidence, or acceptance still needs refinement. |
| `ready` | Bounded scope, acceptance criteria, verification commands, authority, and dependencies are resolved. |
| `in_progress` | One owner has claimed the task and recorded its working location. |
| `blocked` | Record the concrete blocker, who or what can resolve it, and the next action; resume only when resolved. |
| `review` | Implementation and evidence are available for review; required failed checks remain visible. |
| `done` | Acceptance and required checks pass, review is complete, and the result location / integration state is recorded. |
| `cancelled` | Record the reason; retain the ID and history. |

## Working agreement

- Select an authorized, unassigned `ready` task with the highest priority; resolve
  ties with the integration owner. Do not take over another owner's work silently.
- Keep one coherent outcome per task. Link a specification using
  [TASK_SPEC.md](TASK_SPEC.md), either below the index or in an existing issue.
  Large tasks use [ExecPlans](../exec-plans/README.md) and the worktree rules in
  [AGENTS.md](../../AGENTS.md). Do not create an ExecPlan for every small task.
- The lead owns this shared index during parallel work. Subagents report through
  [HANDOFF.md](HANDOFF.md); they do not compete to edit the same row.
- Record the branch, worktree, base SHA, changed-file ownership, exact next action,
  and dated command results in the task detail. Update before handing off or ending
  a session. Never replace a failed check with an unsupported success claim.
- Preserve acceptance criteria during implementation. Record scope changes and
  their authorization; do not weaken criteria to close a task.
- Keep technical compromises in the [debt register](../exec-plans/tech-debt.md).
  A `debt` task links to that record rather than duplicating its risk and closure condition.
- If an external issue exists, link it as the canonical specification. This index
  owns the local status and ownership; do not maintain two competing specifications.

## Task index

| ID | Outcome / specification | Type | Area | Priority | Risk | Status | Owner | Dependencies |
|---|---|---|---|---|---|---|---|---|
| TASK-001 | [Create a discoverable agent task tracker](#task-001) | docs | docs | P2 | R1 | done | Codex (lead) | none |

No additional product backlog has been inferred from architecture aspirations.
Add concrete tasks when their intended outcome is established.

## TASK-001

- **Outcome:** An agent can find one tracker from the root instructions, classify
  work, identify ownership and dependencies, and resume from recorded evidence.
- **Context / hypothesis:** The repository has a task template, an empty debt
  register, and ExecPlan directories, but no general task index. A Markdown index
  linked from the root documents closes this gap without changing runtime behavior.
- **Scope / ownership:** Lead edits this file, `AGENTS.md`, and `README.md` only.
  A read-only subagent independently confirmed the missing tracker and reviewed
  classification. No runtime, API, dependency, or data contracts change.
- **Acceptance:** English classification and lifecycle; valid local links; explicit
  ownership, dependencies, and evidence requirements; discoverability from both
  root documents; existing permission and verification rules preserved.
- **Working location:** Primary checkout, branch `main`, base
  `a19d955029765d219ed81156993ac28f539ec079`. This three-file documentation task
  requires neither a dedicated worktree nor an ExecPlan; only the lead writes.
- **Verification:** Check local links and classification, run `git diff --check`,
  review the diff, then run `make check` under the repository's supported runtimes.
- **Verification result (2026-09-23):** Local link validation and
  `git diff --check` passed. Independent read-only review found no blocking
  conflicts. `make check` passed (exit 0) with Node 24.19.0 after synchronizing
  existing locked frontend dependencies using npm 11.19.0. Backend: 61 tests;
  ML: 3 tests; frontend tests, build, OpenAPI drift, and Compose checks passed.
  Earlier Node 18 / stale dependency failures were environment issues; manifests
  and lock files remain unchanged.
- **Result / integration:** Documentation is present in the primary checkout;
  a local checkpoint records this completed setup before the expanded backlog task.
- **Next action:** Populate a separately tracked pre-hackathon backlog from the
  concept and verified code gaps, as requested by the user.

## Research basis

Sources reviewed on 2026-09-23:

- [GitHub: Best practices for Copilot tasks](https://docs.github.com/en/copilot/tutorials/cloud-agent/get-the-best-results)
  recommends bounded tasks with context and complete acceptance criteria. Here,
  the existing task template holds that detail and the index provides discovery.
- [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
  describes incremental work, persisted progress, and verification before declaring
  completion. Those principles fit handoffs between repository sessions. Its
  experimental harness uses JSON feature lists; this small hackathon repository
  uses reviewable Markdown alongside its existing plans instead. Markdown offers
  no automatic locking or schema enforcement: one index owner and diff review
  mitigate collisions and stale status. This is a process choice, not a measured
  improvement to forecast accuracy or runtime SLA.
