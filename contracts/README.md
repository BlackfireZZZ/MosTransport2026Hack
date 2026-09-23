# Forecast contract v1

`forecast_v1.py` is the strict reference validator for the offline dataset
manifest and published forecast artifact. It is deliberately separate from the
current demo HTTP models: the demo models predate forecast origins, data cutoffs,
target units and publication runs, so changing them would silently break the
existing API.

The contract treats timestamps as instants and requires timezone-aware values.
Storage is UTC-compatible while the product calendar is `Europe/Moscow`; future
calendar bucketing must use explicit calendar versions. Every artifact identifies
its source, feature, model and optional graph versions, and every point is keyed by
route, direction, stop and half-open bucket. The v1 cadence is hourly for the day
horizon, daily for month, and monthly for year; calendar-aware boundary handling is
tested separately from UTC instants. Missing uncertainty is represented by
both bounds being absent; a partial interval is invalid.

`synthetic_boardings` is the only synthetic target. A validation count is not
silently promoted to a boarding count or onboard occupancy. Canonical IDs are
opaque and display names are intentionally absent from this transport contract.

This is a repository contract artifact, not a production import path yet. The
publication task must choose how backend and ML packages consume it without making
the online worker import training code. Until then, validate with the same JSON
fixtures from both environments.

Run the focused checks from the repository root:

```bash
uv run --no-project pytest contracts/tests
uv run --no-project python -c 'from contracts.forecast_v1 import ForecastArtifact; print(ForecastArtifact.model_json_schema()["$defs"].keys())'
```
