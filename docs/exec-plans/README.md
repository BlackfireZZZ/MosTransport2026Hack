# Execution plans

An ExecPlan is a versioned living document used only for a large task under the
criteria in the root `AGENTS.md`: an API, database, or ML contract change,
parallel writes, or work expected to exceed 90 minutes. A normal hackathon task
only needs `docs/agentic/TASK_SPEC.md`. Active plans live in `active/` and
completed plans in `completed/`. Each plan has exactly one integration owner.

## Required plan structure

1. **Purpose / observable result** — the user outcome and how to observe it.
2. **Context** — current state, contracts, full paths, and term definitions.
3. **Scope / non-goals** — the change boundaries.
4. **Acceptance** — specific inputs, outputs, and behavior that must remain unchanged.
5. **Progress / decisions** — milestones, decisions, and discovered risks.
6. **Research evidence** — sources only for a genuinely new solution.
7. **Validation / recovery** — commands, observed results, and rollback or forward-fix strategy.

The plan is self-contained: work can continue from the current checkout and the
single plan file. A prototype is explicitly marked and includes a criterion for
adoption or removal. After completion, move open compromises to `tech-debt.md`
instead of leaving them in chat history.
