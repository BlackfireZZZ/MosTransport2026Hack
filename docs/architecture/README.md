# Архитектура TramFlow

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

`stops` — мультимодальные узлы, `network_edges` — рёбра перемещения/пересадки, `route_stops` — прохождение маршрута по графу. `forecast_points` хранит опубликованный assignment-результат, оптимизированный для чтения. Ключ: `(route_id, stop_id, horizon, bucket_start)`. Каждая точка содержит прогноз и нижнюю/верхнюю границу.

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
- После хакатона: metrics/traces, forecast freshness и model quality dashboards.
- До production нужны SSO/RBAC, audit log, secret manager, rate limits, TLS и классификация исходных полей.
