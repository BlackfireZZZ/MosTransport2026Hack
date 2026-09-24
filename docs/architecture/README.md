# Архитектура TramFlow

Authoritative product requirements: [../product/TASK.md](../product/TASK.md). Prioritize tram passenger-flow forecasts for day/month/year, route/stop/time aggregation, and an updating Moscow map. OD, multimodal modeling, and what-if are optional team extensions.

## Контекст

TramFlow превращает многолетнюю историю валидаций и телематики в краткосрочные, среднесрочные и долгосрочные прогнозы для диспетчеров ЕДЦ. Архитектура разделяет online-выдачу результата и тяжёлую подготовку/обучение, чтобы рост данных не замедлял веб-сервис.

```text
validation + telemetry + calendar + weather + city events
                    │
           immutable raw storage
                    │
       quality checks / feature pipeline
                    │
 temporal multimodal graph + demand model
                    │
 route assignment / capacity / what-if solver
                    │
       versioned forecast publication
                    │
PostgreSQL/serving tables ── FastAPI ── React dispatcher UI
```

В шаблоне реализована правая часть: graph-shaped serving tables → API → UI. `app/ml` задаёт seam для batch inference. Demand forecast и assignment — разные контракты: изменение расписания не должно требовать переобучения модели спроса.

## Backend

Зависимости направлены внутрь:

```text
api → application → domain
           ↑
infrastructure (repository implementations, DB, ML adapters)
```

- **Domain**: горизонты, интервалы и правила предметной области.
- **Application**: use cases, не зависящие от HTTP или SQLAlchemy.
- **Infrastructure**: async SQLAlchemy, PostgreSQL repositories и adapters.
- **API**: Pydantic contracts, dependency injection, status codes.

Composition root — `app/api/dependencies.py`. Это единственное место, где use case связывается с SQL-реализацией.

## Frontend

```text
features/forecast/{components,hooks,types}
               ↓
             api/client
               ↓
      components/ui + lib
```

Серверное состояние принадлежит TanStack Query; продуктовые components не знают базовый URL и не вызывают `fetch` напрямую. Это позволяет позже подключить typed client из OpenAPI без переписывания экранов.

## Контракт данных

`stops` — мультимодальные узлы, `network_edges` — рёбра перемещения/пересадки, `route_stops` — прохождение маршрута по графу. `forecast_points` хранит опубликованный assignment-результат, оптимизированный для чтения. Ключ: `(route_id, stop_id, horizon, bucket_start)` — описывает текущую засеянную таблицу. [ADR-0006](../decisions/0006-stop-identity-and-direction.md) добавляет к ключу направление: `stop_id` указывает в физический namespace остановок, поэтому маршрут проходит остановку в обе стороны и без направления ключ их схлопывает. Колонку вносит TASK-027 вместе со своей миграцией, и эта строка правится там же. Каждая точка содержит прогноз и нижнюю/верхнюю границу.

Время хранится как `timestamptz` в UTC, показывается в `Europe/Moscow`. Интервалы API полуоткрытые: `[from, to)`.

## Путь к большим данным

1. Сырые события вынести в объектное хранилище/колоночный формат, не в OLTP API.
2. Партиционировать агрегаты по дате; индексы — по маршруту/остановке/времени.
3. Training pipeline запускать отдельно, публиковать только прошедший quality gate forecast run.
4. Длинные вычисления API оформлять async job, а не держать HTTP-соединение.
5. Для real-time слоя применять инкрементальные агрегаты и явную отметку freshness.

## Наблюдаемость и безопасность

- `/health/live` проверяет процесс, `/health/ready` — DB.
- Каждый ответ получает `X-Request-ID`; HTTP access logs с длительностью запроса
  сериализуются в JSON.
- `tramflow.http` accepts only `request_failed` / `request_completed` message names
  (other messages become `application_event`). Diagnostic fields are `request_id`,
  `method`, `path` (matched route template, or `<unmatched>`), `status_code` and
  `duration_ms`. Never pass payload values through these fields.
- The optional `exception` object contains a built-in `category` (custom types use
  `Exception`) and the last 20 `frames`, each with deployed code `module`, `function`
  and `line`. Exception text, nested values, SQL parameters, notes, source lines,
  absolute filenames and locals are excluded. Consumers must not expect the former
  traceback string. Code metadata is trusted; client request IDs must be opaque,
  non-sensitive correlation tokens. Third-party loggers and validation responses
  are outside this formatter's scope.
- После хакатона: metrics/traces, forecast freshness и model quality dashboards.
- До production нужны SSO/RBAC, audit log, secret manager, rate limits, TLS и классификация исходных полей.
