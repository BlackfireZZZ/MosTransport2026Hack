import json

import pytest

from tramflow_ml.intake import IntakeRequest, classify, profile_sample, render
from tramflow_ml.synthetic import SyntheticConfig, generate_dataset

CARD = "4276-3801-5512-9043"
VEHICLE = "PASSENGER-CARD-9912345678"
EXTRACT = "TICKET-7781234512349999"
IDENTIFIER_VALUES = (CARD, VEHICLE, EXTRACT)
IDENTIFIER_SUMMARY_KEYS = {
    "classification",
    "distinct_values",
    "format_signatures",
    "max_length",
    "min_length",
    "missing",
    "missing_rate",
    "present",
}


def _write(path, rows):
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )


def _read(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@pytest.fixture
def carded_sample(tmp_path):
    """The canonical fixture with card-shaped values in three identifier columns."""
    generate_dataset(SyntheticConfig(), tmp_path / "source")
    sample = tmp_path / "carded"
    sample.mkdir()
    (sample / "entities.json").write_bytes((tmp_path / "source/entities.json").read_bytes())
    for stream in ("validations", "telemetry"):
        rows = _read(tmp_path / f"source/{stream}.jsonl")
        _write(
            sample / f"{stream}.jsonl",
            [
                {
                    **row,
                    "event_id": f"{CARD}-{index}",
                    "vehicle_id": VEHICLE,
                    "source_version": EXTRACT,
                }
                for index, row in enumerate(rows)
            ],
        )
    return sample


@pytest.fixture
def report(carded_sample):
    return profile_sample(IntakeRequest(source=carded_sample))


def test_no_identifier_value_appears_anywhere_in_the_report(report):
    serialized = render(report)

    for value in IDENTIFIER_VALUES:
        assert value not in serialized


def test_the_report_still_describes_those_fields_by_shape(report):
    fields = report["streams"]["validations"]["fields"]

    assert fields["event_id"]["distinct_values"] == 67
    assert fields["vehicle_id"]["distinct_values"] == 1
    assert fields["vehicle_id"]["min_length"] == len(VEHICLE)
    assert fields["source_version"]["format_signatures"] == {"alnum_punct": 67}


def test_an_identifier_summary_carries_only_the_permitted_keys(report):
    for stream in report["streams"].values():
        for name, summary in stream["fields"].items():
            if classify(name) == "identifier":
                assert set(summary) == IDENTIFIER_SUMMARY_KEYS, name


def test_no_summary_offers_a_sample_or_a_most_frequent_value(report):
    forbidden = {"examples", "mode", "most_frequent", "sample", "top", "values_seen"}

    for stream in report["streams"].values():
        for name, summary in stream["fields"].items():
            assert forbidden.isdisjoint(summary), name


def test_enumerated_fields_report_only_code_defined_members(report):
    fields = report["streams"]["validations"]["fields"]

    assert set(fields["target"]["values"]) == {"other", "synthetic_boardings", "validation_count"}
    assert set(fields["unit"]["values"]) == {"event_count", "other"}
    assert set(fields["synthetic"]["values"]) == {"false", "other", "true"}


def test_a_value_outside_the_allowlist_is_counted_but_never_quoted(carded_sample):
    rows = _read(carded_sample / "validations.jsonl")
    rows[0]["unit"] = "passengers-per-card-4276"
    _write(carded_sample / "validations.jsonl", rows)

    report = profile_sample(IntakeRequest(source=carded_sample))

    assert report["streams"]["validations"]["fields"]["unit"]["values"]["other"] == 1
    assert "passengers-per-card-4276" not in render(report)
