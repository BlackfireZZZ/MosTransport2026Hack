"""Deterministic synthetic fixtures; never a claim about observed Moscow demand."""

import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, BinaryIO
from zoneinfo import ZoneInfo

GENERATOR_VERSION = "synthetic.v1"
SOURCE_VERSION = "synthetic-source.v1"
ENTITY_VERSION = "synthetic-entities.v1"
MOSCOW = ZoneInfo("Europe/Moscow")
HOURS = (8, 8, 8, 18, 18, 18, 12, 3)
STOP_IDS = ("synthetic:stop:1", "synthetic:stop:2", "synthetic:stop:3")


@dataclass(frozen=True)
class SyntheticConfig:
    start: date = date(2024, 1, 1)
    end: date = date(2026, 1, 1)
    events: int = 64
    seed: int = 42
    duplicate_every: int = 17
    late_every: int = 11
    telemetry_every: int = 5
    gap_every_days: int = 13

    def __post_init__(self) -> None:
        if type(self.start) is not date or type(self.end) is not date:
            raise ValueError("start and end must be dates")
        if self.end <= self.start:
            raise ValueError("end must be after start")
        for name in (
            "events",
            "seed",
            "duplicate_every",
            "late_every",
            "telemetry_every",
            "gap_every_days",
        ):
            value = getattr(self, name)
            minimum = 1 if name in ("events", "telemetry_every") else 0
            if type(value) is not int or value < minimum:
                raise ValueError(f"{name} must be an integer >= {minimum}")
        if self.gap_every_days == 1:
            raise ValueError("gap_every_days=1 leaves no source coverage")


def _encode(value: Any) -> bytes:
    return (
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
        + "\n"
    ).encode("utf-8")


class _Writer:
    def __init__(self, stream: BinaryIO) -> None:
        self.stream = stream
        self.digest = hashlib.sha256()
        self.size = 0

    def write(self, content: bytes) -> None:
        self.stream.write(content)
        self.digest.update(content)
        self.size += len(content)

    def inventory(self) -> dict[str, Any]:
        return {"sha256": self.digest.hexdigest(), "bytes": self.size}


def _write_json(output: Path, name: str, value: Any) -> dict[str, Any]:
    with (output / name).open("xb") as stream:
        writer = _Writer(stream)
        writer.write(_encode(value))
        return writer.inventory()


def _catalog() -> dict[str, Any]:
    return {
        "schema_version": "data.v1",
        "entity_version": ENTITY_VERSION,
        "routes": ["synthetic:route:1", "synthetic:route:2"],
        "stops": [
            {"id": STOP_IDS[0], "name": "Тестовая площадь"},
            {"id": STOP_IDS[1], "name": "Тестовая площадь"},
            {"id": STOP_IDS[2], "name": "Тестовый парк"},
        ],
        "patterns": [
            {
                "route_id": f"synthetic:route:{route}",
                "direction_id": f"synthetic:direction:{direction}",
                "stop_ids": list(STOP_IDS if direction == 0 else reversed(STOP_IDS))
                + [STOP_IDS[0] if direction == 0 else STOP_IDS[-1]],
            }
            for route in (1, 2)
            for direction in (0, 1)
        ],
    }


def generate_dataset(config: SyntheticConfig, output: Path) -> dict[str, Any]:
    """Create a new directory; manifest.json exists only after all data files close.

    ``events`` counts unique validations. Duplicate and late injection periods are
    one-based. Summary counts exclude duplicates. Gap dates mean missing source
    coverage, while covered dates with no generated events have observed zero.
    Inventory hashes cover exact UTF-8 bytes, including terminating newlines.
    """
    config.__post_init__()
    days = (config.end - config.start).days
    covered_dates = []
    gap_dates = []
    for index in range(days):
        day = config.start + timedelta(days=index)
        if config.gap_every_days and (index + 1) % config.gap_every_days == 0:
            gap_dates.append(day.isoformat())
        else:
            covered_dates.append(day)
    catalog = _catalog()
    salt = int.from_bytes(hashlib.sha256(str(config.seed).encode("ascii")).digest()[:8])
    cells: Counter[tuple[str, str, str, str, int]] = Counter()
    hour_totals: Counter[str] = Counter()
    counts = {
        "unique_validations": config.events,
        "duplicate_validations": 0,
        "late_validations": 0,
        "telemetry": 0,
    }
    output.mkdir(parents=True, exist_ok=False)
    inventory = {"entities.json": _write_json(output, "entities.json", catalog)}
    with (
        (output / "validations.jsonl").open("xb") as validation_stream,
        (output / "telemetry.jsonl").open("xb") as telemetry_stream,
    ):
        validations = _Writer(validation_stream)
        telemetry = _Writer(telemetry_stream)
        for index in range(config.events):
            day_index = index * (len(covered_dates) - 1) // max(config.events - 1, 1)
            day = covered_dates[day_index]
            hour = HOURS[(index + salt) % len(HOURS)]
            event_at = datetime.combine(day, time(hour, (index + salt) % 60), MOSCOW)
            late = bool(config.late_every and (index + 1) % config.late_every == 0)
            available_at = event_at + (timedelta(days=1) if late else timedelta(minutes=1))
            pattern = catalog["patterns"][(index + salt) % len(catalog["patterns"])]
            sequence = (index // 4 + salt) % len(pattern["stop_ids"])
            stop_id = pattern["stop_ids"][sequence]
            common = {
                "schema_version": "data.v1",
                "entity_version": ENTITY_VERSION,
                "source_version": SOURCE_VERSION,
                "route_id": pattern["route_id"],
                "direction_id": pattern["direction_id"],
                "stop_id": stop_id,
                "stop_sequence": sequence,
                "synthetic": True,
                "vehicle_id": f"synthetic:vehicle:{(index + salt) % 8 + 1}",
                "event_at": event_at.isoformat(),
                "available_at": available_at.isoformat(),
            }
            event = {
                **common,
                "event_id": f"synthetic:validation:{index + 1}",
                "target": "synthetic_boardings",
                "unit": "event_count",
            }
            encoded = _encode(event)
            validations.write(encoded)
            if config.duplicate_every and (index + 1) % config.duplicate_every == 0:
                validations.write(encoded)
                counts["duplicate_validations"] += 1
            counts["late_validations"] += int(late)
            if (index + 1) % config.telemetry_every == 0:
                stop_index = STOP_IDS.index(stop_id)
                telemetry.write(
                    _encode(
                        {
                            **common,
                            "event_id": f"synthetic:telemetry:{index + 1}",
                            "latitude": 55.75 + stop_index * 0.01,
                            "longitude": 37.60 + stop_index * 0.01,
                        }
                    )
                )
                counts["telemetry"] += 1
            hour_totals[f"{hour:02d}"] += 1
            cells[
                (pattern["route_id"], pattern["direction_id"], stop_id, day.isoformat(), hour)
            ] += 1
        inventory["validations.jsonl"] = validations.inventory()
        inventory["telemetry.jsonl"] = telemetry.inventory()
    generation = {
        "generator_version": GENERATOR_VERSION,
        "config": {
            **asdict(config),
            "start": config.start.isoformat(),
            "end": config.end.isoformat(),
        },
        "counts": counts,
        "synthetic": True,
        "gap_dates": gap_dates,
        "hour_totals": dict(sorted(hour_totals.items())),
        "cell_totals": [
            {
                "route_id": route,
                "direction_id": direction,
                "stop_id": stop,
                "date": day_string,
                "hour": hour,
                "count": count,
            }
            for (route, direction, stop, day_string, hour), count in sorted(cells.items())
        ],
    }
    inventory["generation.json"] = _write_json(output, "generation.json", generation)
    source_hash = hashlib.sha256(_encode(inventory)).hexdigest()
    manifest = {
        "schema_version": "forecast.v1",
        "dataset_id": f"synthetic:{source_hash}",
        "source_version": SOURCE_VERSION,
        "source_hash": source_hash,
        "date_from": datetime.combine(config.start, time(), MOSCOW).isoformat(),
        "date_to": datetime.combine(config.end, time(), MOSCOW).isoformat(),
        "timezone": "Europe/Moscow",
        "feature_version": "raw.v1",
        "target": "synthetic_boardings",
        "unit": "event_count",
        "entity_version": ENTITY_VERSION,
        "calendar_version": "moscow-midnight.v1",
        "availability_policy": "event-and-availability.v1",
        "synthetic": True,
    }
    _write_json(output, ".manifest.json.tmp", manifest)
    (output / ".manifest.json.tmp").replace(output / "manifest.json")
    return {"manifest": manifest, "generation": generation, "files": inventory}
