# Матрица проверки изменений

Выберите все подходящие строки. Узкие проверки запускаются до полного gate; фактический exit code/результат попадает в отчёт.

| Изменение | Минимальное опровержение | Обязательный gate |
|---|---|---|
| Документация | ссылки и команды существуют | `git diff --check` + просмотр diff |
| Backend domain/application | unit-тест правила/use case | Ruff, mypy, backend pytest |
| HTTP API | тест success + validation/error + совместимость schema | backend gate + smoke затронутого endpoint |
| SQL/repository | integration-тест с PostgreSQL, диапазон/агрегация | backend gate; для тяжёлого запроса `EXPLAIN (ANALYZE, BUFFERS)` |
| Alembic | upgrade на чистой временной БД; стратегия rollback/forward-fix | `alembic check`, backend gate, Compose smoke |
| Frontend logic | ближайший Vitest/component test | `npm run lint`, `npm run test -- --run`, `npm run build` |
| UI-сценарий | критический happy/error/what-if, keyboard | frontend gate + `make e2e` |
| ML feature/data | schema, boundary time/timezone и leakage test | Ruff, mypy, ML pytest |
| ML model | одинаковые temporal splits, baseline и несколько slices | ML gate + `make ml-eval` |
| Compose/runtime | `docker compose config --quiet` | чистый `up --build --wait`, `make smoke`, logs при ошибке |
| Несколько контуров | contract/integration test на границе | все затронутые gates, затем `make verify-fast` |

Команды контуров описаны в ближайших `AGENTS.md`. Нельзя заменять требуемую проверку более широкой, если её результат не локализует нарушение. Если проверка недоступна, изменение не объявляется готовым.
