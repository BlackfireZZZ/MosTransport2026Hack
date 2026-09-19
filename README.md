# TramFlow — прогноз пассажиропотока московского трамвая

Рабочий шаблон сервиса для ЕДЦ ГУП «Московский метрополитен»: FastAPI + PostgreSQL + Alembic на backend и Vite + React + TypeScript + shadcn/ui на frontend.

Первый вертикальный срез уже включён: API выдаёт прогноз по маршруту и горизонту, PostgreSQL заполняется демонстрационными данными через Alembic, а диспетчерский дашборд показывает KPI, график и схему остановок.

## Быстрый старт

```bash
cp .env.example .env
docker compose up --build
```

После запуска Caddy является единой точкой входа:

- веб-интерфейс: http://localhost:8080
- API через Caddy: http://localhost:8080/api/v1/health/ready
- OpenAPI backend: http://localhost:8000/docs

Остановить стек: `docker compose down`. Удалить локальные данные: `docker compose down -v`.

## Команды разработки

```bash
make bootstrap      # locked backend + ML + frontend dependencies
make doctor         # версии runtimes, Docker и конфигурация
make up             # production-like стек: DB, migration, API, Caddy
make dev-frontend   # только Vite; backend ожидается на :8000
make dev-backend    # только PostgreSQL + FastAPI с reload
make dev-ml         # только изолированный ML workspace
make dev            # DB + backend + frontend вместе
make verify-fast    # основной цикл: lint, types, unit, contracts
make verify         # fast + Alembic на чистой БД
make verify-full    # verify + Docker smoke + browser E2E
make smoke
make ml-eval
make contract-generate
make migration NAME="add feature"
```

Backend локально:

```bash
uv sync --package tramflow-backend --extra dev
make dev-backend
```

Frontend локально:

```bash
cd frontend && npm ci
make dev-frontend
```

В dev Vite проксирует `/api` на `http://localhost:8000`; в Compose тот же путь проксирует Caddy. Поэтому frontend-код не меняет base URL между окружениями. Компоненты shadcn хранятся в `frontend/src/components/ui` и принадлежат проекту.

Проект закрепляет Python 3.13 и Node 24. Если локальные версии отличаются,
используйте `.devcontainer` или Docker; `make doctor` покажет конкретное
расхождение.

## Параллельная работа агентов

Крупная задача автоматически получает отдельную ветку, worktree и изолированный
Compose project:

```bash
make agent-create ID=graph-forecast
make agent-up ID=graph-forecast
make agent-smoke ID=graph-forecast
make agent-down ID=graph-forecast
make agent-remove ID=graph-forecast
```

Порты и PostgreSQL volume вычисляются из `ID`, поэтому несколько задач не
перезаписывают runtime друг друга. Точные критерии крупной задачи и безопасный
lifecycle находятся в [AGENTS.md](AGENTS.md).

## Структура

```text
backend/
  app/api/              # HTTP-контракты и маршруты
  app/application/      # сценарии использования
  app/domain/           # бизнес-типы без инфраструктуры
  app/infrastructure/   # PostgreSQL и репозитории
  app/ml/               # контракт и будущие реализации моделей
  alembic/              # версионируемая схема и seed демо-данных
frontend/src/
  api/                  # единственная граница HTTP-клиента
  components/ui/        # локальные shadcn/ui primitives
  features/             # вертикальные продуктовые модули
docs/
  agentic/              # task, verification, permissions и handoff
  exec-plans/           # только крупные/high-risk задачи
  architecture/         # границы, данные, масштабирование
  decisions/            # ADR — журнал решений
```

## Продуктовый контекст

Система рассчитана на анализ миллионов валидаций и телематических событий за несколько лет и на три горизонта:

- 1 день — почасовое оперативное планирование;
- 1 месяц — посуточное тактическое планирование;
- 1 год — помесячное стратегическое планирование.

Ключевая гипотеза — прогнозировать поток на мультимодальном графе, а затем распределять его по маршрутам и подвижному составу. Поверх него работает сценарный слой «что будет, если». Полная [концепция](docs/product/CONCEPT.md) зафиксирована отдельно.

Текущий репозиторий — foundation: seed-прогноз и сценарный расчёт детерминированы, но интерфейс `ForecastModel` позволяет заменить их ML/solver-пайплайном без изменения API и UI. План развития описан в [архитектуре](docs/architecture/README.md), визуальная система — в [DESIGN.md](DESIGN.md), правила работы агентов — в [AGENTS.md](AGENTS.md).

## Контроль качества

`make verify-fast` проверяет архитектурные границы, Ruff, mypy, backend/ML
pytest, ML golden-eval, ESLint, Vitest, production build, OpenAPI drift и Docker
Compose. `make verify` дополнительно прогоняет Alembic на чистой БД, а
`make verify-full` собирает контейнеры, запускает smoke и три критических
Playwright-сценария. CI использует те же команды.

Это hackathon-профиль на три дня: ExecPlan применяется только для изменений
API/БД/ML-контрактов, параллельной записи или работы дольше 90 минут. Тяжёлые
процессы вроде cloud preview environments и отдельной agent-evaluation platform
намеренно не включены.
