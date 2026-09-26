# TramFlow — прогноз пассажиропотока московского трамвая

Актуальная [постановка организаторов](docs/product/TASK.md) — источник требований: прогноз пассажиропотока трамваев на день, месяц и год, агрегация по маршруту/остановке/времени и обновляемая карта Москвы. [Заполненный трекер подготовки](docs/agentic/TASK_TRACKER.md) содержит порядок работ и зависимости; [анализ](docs/product/PRE_HACKATHON_ANALYSIS.md) отделяет обязательное от расширений команды.

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

Реестр задач агентов: [docs/agentic/TASK_TRACKER.md](docs/agentic/TASK_TRACKER.md).
Он ведётся на английском: тип, область, приоритет, риск, статус, владелец,
зависимости и ссылки на проверяемый результат.

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
data/                   # выгруженный граф трамвайной сети, закоммичен
scripts/fetch_tram_graph.py   # его перевыгрузка из Overpass
infra/overpass/         # self-hosted Overpass API — отдельный деплой
```

## Продуктовый контекст

Система рассчитана на анализ миллионов валидаций и телематических событий за несколько лет и на три горизонта:

- 1 день — почасовое оперативное планирование;
- 1 месяц — посуточное тактическое планирование;
- 1 год — помесячное стратегическое планирование.

Расширение команды, не отдельное требование организаторов: прогнозировать поток на мультимодальном графе, а затем распределять его по маршрутам и подвижному составу. Поверх него работает сценарный слой «что будет, если». Полная [концепция](docs/product/CONCEPT.md) зафиксирована отдельно.

Текущий репозиторий — foundation: seed-прогноз и сценарный расчёт детерминированы, но интерфейс `ForecastModel` позволяет заменить их ML/solver-пайплайном без изменения API и UI. План развития описан в [архитектуре](docs/architecture/README.md), визуальная система — в [DESIGN.md](DESIGN.md), правила работы агентов — в [AGENTS.md](AGENTS.md).

## Источники данных

Граф трамвайной сети выгружен из OpenStreetMap и закоммичен в `data/`: 856
остановок, 919 направленных рёбер, 377 км путей, 73 route-relation (38
уникальных рефов — PTv2 описывает каждое направление отдельно).

Длина перегона считается **по реальной геометрии рельсов**, а не по прямой:
PTv2 размещает узлы `stop_position` на самих путевых ways, поэтому путь между
двумя остановками проходится по узлам. Все 2102 сегмента разрешились так,
без единого отката на прямую линию.

Неочевидное, что ломает наивный роутинг: неориентированно граф распадается на
**две несвязные компоненты** (694 и 162 остановки). Это реальная география —
северная сеть вокруг Тимирязевской не имеет путевой связи с остальной
системой. Недостижимость пары остановок — валидный ответ, а не ошибка.

Схема датасета и способы его загрузки: [docs/tram-graph.md](docs/tram-graph.md).
Перевыгрузка (только стандартная библиотека, без установки зависимостей):

```bash
python3 scripts/fetch_tram_graph.py --out-dir data
```

Выгрузка ходит в собственный Overpass API — `http://204.168.155.177/api/interpreter`,
Москва и область, суточные диффы Geofabrik. Он поднят отдельно от этого стека:
у него своя БД на 12 ГБ и свой жизненный цикл, поэтому он намеренно не входит
в `compose.yaml`. Развёртывание — [docs/deployment.md](docs/deployment.md).

Перед тем как писать к нему клиент, прочитайте раздел про ошибки в
[docs/overpass-api.md](docs/overpass-api.md). Overpass отвечает **пятью разными
формами**, и только одна из них очевидна: запрос, упёршийся в собственный
`[timeout:]`, возвращает HTTP 200 с валидным JSON и молча неполным набором
объектов — единственный признак это ключ `remark`. Кривой QL приходит как HTTP
400 с HTML-телом, а перегруз диспетчера — как HTTP 504, тоже HTML, поэтому
`raise_for_status()` срабатывает раньше, чем кто-либо прочитает сообщение.
Готовый клиент, покрывающий все пять, лежит в том же документе.

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

## Последние исследования посадок

[Сильные ориентиры, слабые кандидаты и сопоставление с расписанием](docs/analysis/2026-09-26-boarding-matching/README.md):
открываемые графики, полные диапазоны рейсов, проверки синхронности валидаторов,
относительные интервалы и воспроизводимые результаты. Это экспериментальные
гипотезы остановок; они не заменяют подтверждённую телематику и не включены в serving.
