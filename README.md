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
make setup          # uv workspace backend + ML, npm frontend
make up             # production-like стек: DB, migration, API, Caddy
make dev-frontend   # только Vite; backend ожидается на :8000
make dev-backend    # только PostgreSQL + FastAPI с reload
make dev-ml         # только изолированный ML workspace
make dev            # DB + backend + frontend вместе
make check
make smoke
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

CI и `make check` проверяют Ruff, mypy и pytest для backend; ESLint, Vitest и production build для frontend; корректность Docker Compose; smoke-тест API и SPA после запуска контейнеров.
