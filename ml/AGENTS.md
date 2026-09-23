# ML: local rules

Authoritative product requirements: [../docs/product/TASK.md](../docs/product/TASK.md). Prioritize tram passenger-flow forecasts for day/month/year, route/stop/time aggregation, and an updating Moscow map. OD, multimodal modeling, and what-if are optional team extensions.

The root `AGENTS.md` is mandatory. This file only adds rules specific to `ml/`.

## Experiment contract

- Before training, record the objective, baseline, metrics, temporal slices, and acceptance threshold.
- A dataset manifest records the source and version, date range, timezone, feature version, target definition, and leakage-prevention rules.
- Results must be reproducible from configuration and seed. Do not commit a model artifact without an explicit registry or storage decision.
- Compare models on identical temporal splits and route, stop, and horizon segments; an average metric must not hide the worst slices.
- Training and batch code must not be imported by the online backend worker. Integrate through a versioned forecast-publication contract.

## Verification

Run the closest test for the changed transformation or metric first, then:

```bash
uv run --package tramflow-ml ruff check ml
uv run --package tramflow-ml mypy ml/src
uv run --package tramflow-ml pytest ml/tests
```

A feature change requires schema and boundary tests plus a leakage report; a model change requires comparison with the baseline across multiple temporal slices.
