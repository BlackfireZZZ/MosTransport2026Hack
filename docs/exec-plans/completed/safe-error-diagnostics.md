# TASK-013: safe exception diagnostics

## Purpose and acceptance

Synthetic secrets in exception text, SQL parameters, nested causes, notes and
source lines must not reach the configured HTTP JSON log or the generic 500
response. Keep request correlation, status/timing, error category and code location.
Preserve the existing HTTP response and CORS contract.

## Context and ownership

Base: 6a0f1a7f62c52a04c51a9d7f6dde3b54868326a3; primary checkout clean.
Worktree: `/home/blackfire/Hackatons/MosTransport2026Hack-worktrees/safe-error-diagnostics`;
branch `agent/safe-error-diagnostics`. Lead owns formatter, middleware and docs;
test subagent owns only `backend/tests/test_observability.py`.
`rg` found two log events, both in ObservabilityMiddleware; no other consumers of
JsonFormatter or the JSON exception field. Existing HTTP tests fix response shape.

## Scope and decisions

Allow static request event names and explicitly selected diagnostic fields.
Represent exceptions by a built-in category and at most 20 innermost traceback code
locations, without rendering exception objects, chains/groups, locals or source.
Log matched route templates instead of user-controlled paths; unknown paths use
`<unmatched>`. Existing validated request IDs remain correlation tokens: clients
must never put secrets in them. Code module/function names are trusted deployed metadata. This is not a sanitizer
for third-party loggers or validation-error responses.
No dependency, API schema, database or authentication change.

## Research evidence

- https://docs.python.org/3.13/library/logging.html#logging.Formatter.formatException:
  default exception formatting renders traceback text; unsuitable for driver errors.
- https://docs.python.org/3.13/library/traceback.html: rendering includes exception
  values, chains, notes and source. Walk raw traceback frames instead; only select
  code metadata and line numbers. No exception stringification is required.
- https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html:
  exclude tokens, personal data, credentials, connection strings and source text.
  This supports an allowlist, rather than guessing every possible secret syntax.

## Validation and recovery

Start with formatter and HTTP captured-output regressions, then backend checks and
`make check`; contract pytest separately. Independent review before handoff.
Rollback is a code revert; it would restore the original diagnostic exposure.
No live credentials/passenger data or external runtime resources needed.

## Progress

- Regression suite on old code: 11 failed, 2 passed. After implementation,
  `uv run --package tramflow-backend pytest backend/tests/test_observability.py
  backend/tests/test_error_responses.py -q`: 19 passed.
- Ruff clean; mypy checked 40 source files successfully.
- Lead `make check`: exit 0; backend 133 passed / 10 SQL skipped, ML 50 passed,
  frontend 47 passed; architecture, lint, types, production build, OpenAPI drift,
  synthetic evaluation and Compose validation passed.
- `uv run --package tramflow-backend pytest contracts/tests -q`: 12 passed.
- First `make stack-verify` failed while obtaining a GHCR registry token (TLS
  handshake timeout), before application startup. Retry exited 0: built stack
  healthy and smoke passed. Owned containers/networks/volumes were removed.
- Independent read-only review found no blockers; lead reviewed final diff and
  `git diff --check` passed. No dependencies or generated artifacts changed.
- Integration: fast-forward main from the recorded clean base after these gates.
  No remote push. Worktree/branch retained for review; graph worktrees untouched.
- Limits: safe diagnostic policy applies to the configured HTTP JSON logger and
  generic unhandled-error response, not arbitrary third-party log output or 422
  validation payloads. Nested exception values are intentionally unavailable;
  category and code locations replace full text.
