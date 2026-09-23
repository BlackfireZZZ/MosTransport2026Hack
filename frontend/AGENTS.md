# Frontend: local rules

Authoritative product requirements: [../docs/product/TASK.md](../docs/product/TASK.md). Prioritize tram passenger-flow forecasts for day/month/year, route/stop/time aggregation, and an updating Moscow map. OD, multimodal modeling, and what-if are optional team extensions.

The root `AGENTS.md` and `DESIGN.md` are mandatory. This file only adds rules specific to `frontend/`.

## Boundaries

- All HTTP access goes through `src/api`; feature components must not call `fetch` or know the base URL.
- Server state lives in query hooks, rendering lives in components, and transport types stay at the API boundary.
- `src/components/ui` contains local shadcn primitives without product copy or business logic.
- A user-flow change covers loading, empty, error, stale/success, and keyboard-accessible paths.
- Do not introduce a new visual pattern until it is aligned with `DESIGN.md`.

## Dependencies

Everything in `dependencies` ships to the browser. Establish the package's licence,
open advisories and gzipped cost before installing, and surface them as a flagged item
in the report — see "Dependencies and lock files" in the root `AGENTS.md`. No approval
is required; silence is what is forbidden. Never hand-edit `package-lock.json`.

## Verification

Run the closest Vitest test first, then:

```bash
cd frontend
npm run lint
npm run test -- --run
npm run build
```

For a UI change, provide observed viewport and accessibility checks. If automation is unavailable, explicitly document the manual scenario and residual risk.
