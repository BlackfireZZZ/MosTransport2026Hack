# Frontend: локальные правила

Корневой `AGENTS.md` и `DESIGN.md` обязательны. Здесь находятся только уточнения для `frontend/`.

## Границы

- HTTP проходит через `src/api`; feature components не вызывают `fetch` и не знают base URL.
- Серверное состояние живёт в query hooks, отображение — в components, транспортные типы — у API-границы.
- `src/components/ui` содержит локальные shadcn primitives без продуктовых текстов и бизнес-логики.
- Изменение пользовательского сценария включает loading, empty, error, stale/success и keyboard path.
- Не вводить новый визуальный паттерн, пока он не согласован с `DESIGN.md`.

## Проверка

Сначала запустить ближайший Vitest-тест, затем:

```bash
cd frontend
npm run lint
npm run test -- --run
npm run build
```

Для UI-изменения приложить фактическую проверку целевых viewport и доступности; если автоматизации нет, явно описать ручной сценарий и остаточный риск.
