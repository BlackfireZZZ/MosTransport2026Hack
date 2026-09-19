# TramFlow ML

Изолированное `uv`-окружение для offline-подготовки признаков, обучения и backtesting. Оно намеренно не импортируется backend-процессом.

```bash
make sync-ml
make dev-ml
make ml-check
```

Перед добавлением модели зафиксируйте dataset version, временные split-границы, baseline, метрики и model card. Публикация результата в serving tables должна быть отдельным атомарным шагом.

Golden evaluation проверяет, что кандидат превосходит наивный baseline на каждом
горизонте и сохраняет согласованное покрытие интервалов:

```bash
uv run --package tramflow-ml tramflow-ml evaluate
```
