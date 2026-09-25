import csv
import json
from datetime import datetime

import pytest

from tramflow_ml.intake import IntakeRequest, SchemaError, load_profile, profile_sample
from tramflow_ml.synthetic import MOSCOW, SyntheticConfig, generate_dataset

COLUMNS = {
    "available_at": "published",
    "direction_id": "bound",
    "entity_version": "catalog_ver",
    "event_at": "happened",
    "event_id": "row_key",
    "latitude": "lat",
    "longitude": "lon",
    "route_id": "line_code",
    "schema_version": "contract",
    "source_version": "extract_ver",
    "stop_id": "platform_code",
    "stop_sequence": "visit_no",
    "synthetic": "is_generated",
    "target": "measure_name",
    "unit": "measure_unit",
    "vehicle_id": "car_code",
}
FILES = {"telemetry": "positions.csv", "validations": "boardings.csv"}
TIMESTAMP_FORMAT = "%d.%m.%Y %H:%M:%S"
TIMESTAMP_FIELDS = ("event_at", "available_at")
RECONCILING_SECTIONS = ("streams", "supportability")


def _cell(name, value):
    if name in TIMESTAMP_FIELDS:
        return datetime.fromisoformat(value).astimezone(MOSCOW).strftime(TIMESTAMP_FORMAT)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _rewrite(source, target, columns):
    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
    names = sorted(columns)
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow([columns[name] for name in names])
        for row in rows:
            writer.writerow([_cell(name, row[name]) for name in names])


def write_alternate_schema(fixture_dir, destination):
    """The same events rendered as CSV: renamed columns, naive Moscow timestamps."""
    destination.mkdir(parents=True)
    (destination / "entities.json").write_bytes((fixture_dir / "entities.json").read_bytes())
    without = {
        "validations": ("latitude", "longitude"),
        "telemetry": ("target", "unit"),
    }
    for stream, absent in without.items():
        columns = {name: column for name, column in COLUMNS.items() if name not in absent}
        _rewrite(fixture_dir / f"{stream}.jsonl", destination / FILES[stream], columns)
    return destination


def write_profile(path):
    path.write_text(
        json.dumps(
            {
                "schema_version": "intake-profile.v1",
                "name": "alternate-fixture",
                "source_format": "csv",
                "files": FILES,
                "columns": COLUMNS,
                "constants": {},
                "timestamp_format": TIMESTAMP_FORMAT,
                "assume_timezone": "Europe/Moscow",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def canonical(tmp_path):
    generate_dataset(SyntheticConfig(), tmp_path / "canonical")
    return tmp_path / "canonical"


@pytest.fixture
def alternate(canonical, tmp_path):
    return write_alternate_schema(canonical, tmp_path / "alternate")


@pytest.fixture
def reports(canonical, alternate, tmp_path):
    profile = load_profile(write_profile(tmp_path / "alternate.json"))
    return (
        profile_sample(IntakeRequest(source=canonical)),
        profile_sample(IntakeRequest(source=alternate, profile=profile)),
    )


def test_every_reconciling_section_is_identical_across_the_two_schemas(reports):
    first, second = reports

    for section in RECONCILING_SECTIONS:
        assert first[section] == second[section], section


def test_row_duplicate_and_span_counts_reconcile(reports):
    first, second = (report["streams"]["validations"] for report in reports)

    assert (first["rows"], second["rows"]) == (67, 67)
    assert first["duplicates"] == second["duplicates"]
    assert first["date_span"] == second["date_span"]
    assert first["join_coverage"] == second["join_coverage"]


def test_measures_reconcile_although_one_encoding_carries_them_as_text(reports):
    first, second = (report["streams"]["validations"]["fields"] for report in reports)

    assert first["stop_sequence"]["sum"] == second["stop_sequence"]["sum"] == 99
    assert first["synthetic"]["values"] == second["synthetic"]["values"]
    assert first["event_at"]["first"] == second["event_at"]["first"]


def test_only_the_encoding_section_differs(reports):
    first, second = reports

    assert first["source"] != second["source"]
    assert (first["source"]["format"], second["source"]["format"]) == ("jsonl", "csv")
    assert second["source"]["profile"] == "alternate-fixture"
    assert second["source"]["timestamp_format"] == TIMESTAMP_FORMAT
    assert second["source"]["streams"]["validations"]["columns"]["event_id"] == "row_key"


def test_alternate_schema_needs_its_profile(alternate):
    with pytest.raises(SchemaError) as failure:
        profile_sample(IntakeRequest(source=alternate))

    assert "cannot locate the streams" in str(failure.value)
