# Backend: локальные правила

Корневой `AGENTS.md` обязателен. Здесь находятся только уточнения для `backend/`.

## Границы

- Направление зависимостей: `api → application → domain`; `infrastructure` реализует порты application/domain и подключается в composition root.
- Pydantic-схемы описывают HTTP-контракт, SQLAlchemy-модели — хранение; не использовать их как domain-типы.
- Endpoint валидирует запрос, вызывает use case и отображает результат/ошибку. SQL и бизнес-решения в handler запрещены.
- Схема БД меняется только новой Alembic-миграцией. Не переписывать уже применённую миграцию.
- Новые production dependencies, breaking API и разрушительные миграции относятся к крупным задачам.

## Проверка

Сначала запустить тест изменённого use case/endpoint, затем:

```bash
uv run --package tramflow-backend ruff check backend
uv run --package tramflow-backend mypy backend/app
uv run --package tramflow-backend pytest backend/tests
```

Для миграции дополнительно нужны upgrade на чистой временной БД, `alembic check` и документированный rollback/forward-fix. Матрица: `docs/agentic/VERIFICATION_MATRIX.md`.
