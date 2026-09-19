# Golden forecast evaluation

Набор содержит небольшие проверяемые срезы для трёх горизонтов и нетипичных
событий. Это не benchmark качества будущей production-модели, а исполняемый
контракт evaluation pipeline.

Gate проходит, если кандидат не хуже наивного baseline по WAPE на каждом
горизонте и покрытие интервалов не ниже 80%. Новая модель должна добавлять сюда
реальные временные holdout-срезы с versioned metadata, не заменяя их synthetic
примерами.

```bash
uv run --package tramflow-ml tramflow-ml evaluate
```
