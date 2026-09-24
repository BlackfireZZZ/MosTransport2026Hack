"""Calendar-period arithmetic in Europe/Moscow: hours, civil days, calendar months.

No step is ever approximated by a fixed number of days. Hour steps move whole UTC
hours because every historical Moscow offset is a whole hour, which keeps an hour
bucket one elapsed hour across a DST transition; day and month steps move the civil
date and recombine at Moscow midnight.
"""

from calendar import monthrange
from datetime import UTC, date, datetime, time, timedelta

from tramflow_ml.features.records import (
    GRANULARITY_FOR_HORIZON,
    MOSCOW,
    Bucket,
    FeatureError,
    Granularity,
    Horizon,
    require_aware,
)

MONTHS_PER_YEAR = 12
HOURS_PER_DAY = 24


def granularity_for(horizon: Horizon) -> Granularity:
    """The horizon → granularity mapping the forecast contract requires."""
    try:
        return GRANULARITY_FOR_HORIZON[horizon]
    except KeyError as error:
        raise FeatureError(f"unsupported horizon {horizon!r}") from error


def moscow(instant: datetime, name: str = "instant") -> datetime:
    return require_aware(instant, name).astimezone(MOSCOW)


def service_date(instant: datetime) -> date:
    """The Moscow civil date, the same service-day rule the identity layer applies."""
    return moscow(instant, "event").date()


def midnight(day: date) -> datetime:
    """Moscow midnight of a civil date, refused when that wall time names no single instant.

    Moscow advanced the clock at 00:00 on 1 April 1981-1984, so those dates have no
    midnight. Resolving one would mean guessing an instant, which the identity clock
    already refuses; a service day that cannot be located is an error, not a default.
    """
    naive = datetime.combine(day, time(0))
    local = naive.replace(tzinfo=MOSCOW, fold=0)
    if local.astimezone(UTC).astimezone(MOSCOW).replace(tzinfo=None) != naive:
        raise FeatureError(f"{day.isoformat()} has no Moscow midnight")
    if local.utcoffset() != naive.replace(tzinfo=MOSCOW, fold=1).utcoffset():
        raise FeatureError(f"{day.isoformat()} has an ambiguous Moscow midnight")
    return local


def bucket_start_of(instant: datetime, granularity: Granularity) -> datetime:
    """The start of the bucket containing ``instant``."""
    local = moscow(instant)
    if granularity == "hourly":
        truncated = local.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
        return truncated.astimezone(MOSCOW)
    if granularity == "daily":
        return midnight(local.date())
    if granularity == "monthly":
        return midnight(date(local.year, local.month, 1))
    raise FeatureError(f"unsupported granularity {granularity!r}")


def step(start: datetime, granularity: Granularity, steps: int) -> datetime:
    """Move a bucket start by whole buckets; ``steps`` may be negative."""
    local = moscow(start, "bucket start")
    try:
        if granularity == "hourly":
            return (local.astimezone(UTC) + timedelta(hours=steps)).astimezone(MOSCOW)
        if granularity == "daily":
            return midnight(local.date() + timedelta(days=steps))
        if granularity == "monthly":
            return _shift_months(local, steps)
    except FeatureError:
        raise
    except (OverflowError, ValueError) as error:
        raise FeatureError("bucket step leaves the supported datetime range") from error
    raise FeatureError(f"unsupported granularity {granularity!r}")


def _shift_months(local: datetime, steps: int) -> datetime:
    total = local.year * MONTHS_PER_YEAR + (local.month - 1) + steps
    year, month = divmod(total, MONTHS_PER_YEAR)
    return midnight(date(year, month + 1, 1))


def bucket_from_start(start: datetime, granularity: Granularity) -> Bucket:
    return Bucket(moscow(start, "bucket start"), step(start, granularity, 1))


def bucket_of(instant: datetime, granularity: Granularity) -> Bucket:
    return bucket_from_start(bucket_start_of(instant, granularity), granularity)


def bucket_dates(bucket: Bucket) -> tuple[date, ...]:
    """The Moscow civil dates a half-open bucket touches; coverage is stated per date."""
    days: list[date] = []
    day = bucket.start.date()
    while midnight(day) < bucket.end:
        days.append(day)
        day += timedelta(days=1)
    return tuple(days)


def validate_origin(origin: datetime, horizon: Horizon) -> datetime:
    """Accept only the origins ``calendar.v1`` accepts for this horizon."""
    local = moscow(origin, "forecast origin")
    if horizon not in GRANULARITY_FOR_HORIZON:
        raise FeatureError(f"unsupported horizon {horizon!r}")
    if local.minute or local.second or local.microsecond:
        raise FeatureError("forecast origin must align to an exact Moscow hour")
    if horizon in {"month", "year"} and (local.day != 1 or local.hour != 0):
        raise FeatureError("month/year origin must be the first day at midnight")
    if horizon == "year" and local.month != 1:
        raise FeatureError("year origin must be January 1")
    return local


def horizon_buckets(origin: datetime, horizon: Horizon) -> tuple[Bucket, ...]:
    """Contiguous buckets covering one calendar horizon, matching ``calendar.v1``."""
    local = validate_origin(origin, horizon)
    granularity = granularity_for(horizon)
    counts: dict[str, int] = {
        "day": HOURS_PER_DAY,
        "month": monthrange(local.year, local.month)[1],
        "year": MONTHS_PER_YEAR,
    }
    starts = [local]
    for _ in range(counts[horizon] - 1):
        starts.append(step(starts[-1], granularity, 1))
    return tuple(bucket_from_start(start, granularity) for start in starts)
