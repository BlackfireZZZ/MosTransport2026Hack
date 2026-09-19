# Work handoff contract

A subagent returns a concise summary, not a raw transcript. The next contributor must be able to continue without verbal context.

## Required fields

```text
Objective and actual status:
Worktree / branch / base SHA:
Owner of changed files:
Changed contracts and files:
Decisions and supporting evidence:
Verification commands and observed results:
What remains unverified and why:
Risks and open questions:
Exact next step:
Cleanup completed, or why the environment was retained:
```

## Rules

- Do not write “done” or “tests pass” without the command and its observed result.
- Separate facts from assumptions and recommendations from already applied changes.
- Identify uncommitted or third-party changes and do not include them in your result.
- A write-task handoff includes a clear ownership boundary; two agents must not edit the same file or contract at the same time.
- The root agent reviews the diff, integrates the results, and personally runs the final gate.
- When stopping, update the active ExecPlan if one exists and always state the exact next step in the handoff.
