# Authoritative hackathon task

Source: the full organizer task text supplied by the user on 2026-09-23, with the
user's latest correction applied. No external source URL or dataset was supplied.
The Russian text below is preserved verbatim. This is the requirements source of
truth; [CONCEPT.md](CONCEPT.md) describes the team's approach and optional extensions.
The earlier, mistakenly supplied delay-prediction brief is superseded and must not
be used to plan or implement this project.

## Original task text

ИИ-прогноз загрузки трамвайных маршрутов
В настоящее время в Едином диспетчерском центре (ЕДЦ) ГУП «Московский метрополитен» ведётся работа по созданию набора моделей краткосрочного и долгосрочного прогнозирования пассажиропотока на наземном транспорте. В настоящее время прогнозы строятся на основе простейших регрессионных моделей, имеющих ограниченную точность.

Разработайте математическую модель для прогнозирования пассажиропотока на трамвайных маршрутах на базе технологий ИИ, включая ML. Вам предстоит проанализировать массивы больших данных телематики и валидаций (оплаты проезда) за несколько лет, чтобы создать интерактивный веб-сервис. Сервис должен уметь строить краткосрочные, среднесрочные и долгосрочные прогнозы загруженности транспорта с привязкой к геопозиции и времени, позволяя диспетчерам эффективно распределять подвижной состав.

Ключевые функции будущего решения:
Анализ больших данных: обработка миллионов строк исторических данных по валидациям за несколько лет.
Гибкое прогнозирование: построение предиктивных моделей на три горизонта планирования — 1 день, 1 месяц, 1 год.
Детализированная агрегация: фильтрация и агрегация прогноза по конкретным маршрутам, отдельным остановкам и выбранным временным интервалам.
Интерактивный дашборд: полноценный веб-сервис с визуализацией динамики загрузки на карте Москвы в реальном времени

Участвуй в этом треке, особенно если ты:
ML Engineer / Data Scientist (прогнозирование временных рядов, анализ данных).
Backend-разработчик (Java 17+, Spring Boot, реактивный стек Netty).
Frontend-разработчик (React, визуализация данных на картах).
Data Engineer (настройка пайплайнов для обработки массивов телематики).
Продуктовый или системный аналитик.

## Requirement identifiers

These identifiers support traceability; they do not add organizer requirements.

| ID | Required outcome |
|---|---|
| RQ-01 | Process millions of historical validation and telemetry records spanning years. |
| RQ-02 | Produce AI/ML passenger-flow forecasts for one day, one month, and one year. |
| RQ-03 | Filter and aggregate by tram route, individual stop, and selected time interval. |
| RQ-04 | Provide an interactive web dashboard showing load dynamics on a Moscow map with real-time updates. |
| RQ-05 | Support dispatcher decisions about allocation of rolling stock using geographically and temporally grounded forecasts. |

## Interpretation boundaries and open questions

- The task says passenger flow/load but does not define the measurement target:
  boardings, onboard occupancy, or another quantity. Confirm labels and units when
  data arrives; payment validations alone must not be called observed occupancy.
- Hourly/daily/monthly buckets are the team's proposed implementation for the
  day/month/year horizons, not a separately stated organizer mandate.
- Real-time dashboard updates are required; telemetry transport, update cadence,
  push versus polling, latency SLA, and whether live feeds will be available are
  unspecified. A timestamped refresh/replay contract can be built now.
- Java/Spring/Netty appear in the participant-skills section. This text does not
  explicitly mandate a stack; retain the current Python backend pending any
  additional organizer constraints.
- Exact file schemas, identifiers, licence/access conditions, scoring metric,
  submission format, delay between event and availability, and coverage are unknown.
  Confirm competition rules on pre-event code reuse before submission.
- OD inference, multimodal expansion, graph neural networks, what-if scenarios,
  and automatic fleet optimization are team hypotheses/extensions. They must not
  displace RQ-01 through RQ-05 or be presented as validated capabilities.

Implementation priorities and verification criteria live in the
[agent task tracker](../agentic/TASK_TRACKER.md); the evidence review and dependency
plan live in [PRE_HACKATHON_ANALYSIS.md](PRE_HACKATHON_ANALYSIS.md).
