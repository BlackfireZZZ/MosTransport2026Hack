# Frontend: local rules

The root `AGENTS.md` and `DESIGN.md` are mandatory. This file only adds rules specific to `frontend/`.

## Boundaries

- All HTTP access goes through `src/api`; feature components must not call `fetch` or know the base URL.
- Server state lives in query hooks, rendering lives in components, and transport types stay at the API boundary.
- `src/components/ui` contains local shadcn primitives without product copy or business logic.
- A user-flow change covers loading, empty, error, stale/success, and keyboard-accessible paths.
- Do not introduce a new visual pattern until it is aligned with `DESIGN.md`.

## Verification

Run the closest Vitest test first, then:

```bash
cd frontend
npm run lint
npm run test -- --run
npm run build
```

For a UI change, provide observed viewport and accessibility checks. If automation is unavailable, explicitly document the manual scenario and residual risk.
