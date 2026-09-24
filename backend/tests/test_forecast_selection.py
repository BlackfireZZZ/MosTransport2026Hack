from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.domain.forecast import ForecastHorizon, ForecastQueryError, ForecastSelection


def test_window_limit_uses_elapsed_time_for_zoneinfo_calls() -> None:
    zone = ZoneInfo("Europe/Berlin")
    selection = ForecastSelection(
        start=datetime(2026, 10, 25, tzinfo=zone), end=datetime(2026, 10, 26, tzinfo=zone)
    )
    with pytest.raises(ForecastQueryError, match="horizon limit"):
        selection.validate(ForecastHorizon.DAY)
