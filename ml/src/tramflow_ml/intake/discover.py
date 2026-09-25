"""Locate each stream's file, read its column names, and refuse an unmappable schema.

Only an exact canonical name auto-maps, which is identity rather than inference. Every
other correspondence has to be written into a profile, and the refusal below is what
tells the operator exactly which ones are still missing.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from tramflow_ml.ingestion.normalize import STREAM_FIELDS
from tramflow_ml.ingestion.readers import read_csv_header
from tramflow_ml.ingestion.records import IngestionError, SourceFormat, StreamName
from tramflow_ml.intake.profile import (
    STREAMS,
    IntakeProfile,
    builtin_profile,
    profile_skeleton,
)
from tramflow_ml.intake.records import (
    FIELD_CONTRACTS,
    JSON_COLUMN_SAMPLE_ROWS,
    SchemaError,
)

_NOTHING = "-"


@dataclass(frozen=True)
class StreamSchema:
    """One stream's file, its columns, and how they map onto canonical fields."""

    stream: StreamName
    file: str
    columns: tuple[str, ...]
    mapping: Mapping[str, str]
    constants: tuple[str, ...]
    unmapped: tuple[str, ...]
    unused: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "columns": dict(sorted(self.mapping.items())),
            "constants": list(self.constants),
            "file": self.file,
            "unused_columns": list(self.unused),
        }


def resolve_profile(source: Path, profile: IntakeProfile | None) -> IntakeProfile:
    """Without a profile, pick the built-in shape whose extension the sample uses."""
    if profile is not None:
        return profile
    candidates = [
        fmt
        for fmt in ("jsonl", "csv")
        if all((source / f"{stream}.{fmt}").is_file() for stream in STREAMS)
    ]
    if len(candidates) != 1:
        raise SchemaError(_missing_files_message(source, candidates))
    return builtin_profile("csv" if candidates[0] == "csv" else "jsonl")


def discover(source: Path, profile: IntakeProfile) -> tuple[StreamSchema, ...]:
    schemas = tuple(_stream_schema(source, profile, stream) for stream in STREAMS)
    if any(schema.unmapped for schema in schemas):
        raise SchemaError(_unmapped_message(profile, schemas))
    return schemas


def _stream_schema(source: Path, profile: IntakeProfile, stream: StreamName) -> StreamSchema:
    name = profile.file_for(stream)
    path = source / name
    if not path.is_file():
        raise SchemaError(_absent_file_message(source, stream, name))
    columns = _columns(path, profile.source_format)
    adapter = profile.adapter
    mapping = {
        field: adapter.source_column(field)
        for field in STREAM_FIELDS[stream]
        if adapter.source_column(field) in columns
    }
    unmapped_fields = tuple(field for field in STREAM_FIELDS[stream] if field not in mapping)
    constants = tuple(field for field in unmapped_fields if field in adapter.constants)
    unmapped = tuple(field for field in unmapped_fields if field not in constants)
    return StreamSchema(
        stream=stream,
        file=name,
        columns=columns,
        mapping=mapping,
        constants=constants,
        unmapped=unmapped,
        unused=tuple(sorted(set(columns) - set(mapping.values()))),
    )


def _columns(path: Path, source_format: SourceFormat) -> tuple[str, ...]:
    if source_format == "csv":
        try:
            header, _ = read_csv_header(path)
        except IngestionError as error:
            raise SchemaError(f"{path.name}: {error}") from error
        return tuple(sorted(header))
    return tuple(sorted(_json_keys(path)))


def _json_keys(path: Path) -> set[str]:
    """Union of the keys of the first readable rows; a later row may add a field."""
    keys: set[str] = set()
    seen = 0
    with path.open("rb") as stream:
        for line in stream:
            if seen >= JSON_COLUMN_SAMPLE_ROWS:
                break
            seen += 1
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict):
                keys.update(str(key) for key in row)
    if not keys:
        raise SchemaError(
            f"{path.name}: the first {JSON_COLUMN_SAMPLE_ROWS} lines hold no readable "
            "JSON object, so intake can see no columns at all. Check the encoding and "
            "whether the file really is JSON Lines (one object per line)."
        )
    return keys


def _missing_files_message(source: Path, candidates: Sequence[str]) -> str:
    present = sorted(entry.name for entry in source.iterdir())
    expected = [f"{stream}.jsonl" for stream in STREAMS] + [f"{stream}.csv" for stream in STREAMS]
    ambiguity = (
        "Both the .jsonl and the .csv spelling are complete, so which one is the sample "
        "is not intake's decision."
        if len(candidates) > 1
        else "No complete set of stream files is present under the built-in names."
    )
    skeleton = profile_skeleton("jsonl", {stream: "REPLACE-ME" for stream in STREAMS}, {})
    return (
        f"intake cannot locate the streams in {source.name!r}.\n\n"
        f"  files present ({len(present)}): {', '.join(present) or _NOTHING}\n"
        f"  built-in names, one full set of which is needed: {', '.join(expected)}\n\n"
        f"{ambiguity}\n"
        "Name the files yourself in a profile and rerun with --profile <file>:\n\n"
        f"{_render(skeleton)}"
    )


def _absent_file_message(source: Path, stream: StreamName, name: str) -> str:
    present = sorted(entry.name for entry in source.iterdir())
    return (
        f"intake cannot read the {stream!r} stream: the profile names {name!r} and "
        f"{source.name!r} does not hold it.\n\n"
        f"  files present ({len(present)}): {', '.join(present) or _NOTHING}\n\n"
        "Correct profile.files and rerun."
    )


def _unmapped_message(profile: IntakeProfile, schemas: Sequence[StreamSchema]) -> str:
    blocked = [schema for schema in schemas if schema.unmapped]
    files: dict[str, str] = {schema.stream: schema.file for schema in schemas}
    mapped = {
        field: column for schema in schemas for field, column in sorted(schema.mapping.items())
    }
    skeleton = profile_skeleton(profile.source_format, files, mapped)
    return "\n".join(
        [
            f"intake cannot read this sample with the {profile.name!r} mapping: "
            f"{len(blocked)} of {len(schemas)} streams have unmapped required fields.",
            "",
            *[line for schema in blocked for line in _stream_block(schema)],
            "No column is mapped by name similarity, position or a synonym list: only an "
            "exact canonical name maps on its own. Supply the rest yourself and rerun with "
            "--profile <file>:",
            "",
            _render(skeleton),
            "",
            "Replace every null with the source column that carries that field, or move the "
            'field into "constants" when the source omits it and one value is right for every '
            "row. Certifying the organizer's real mapping is TASK-049/TASK-050, not this "
            "tool's job.",
        ]
    )


def _stream_block(schema: StreamSchema) -> list[str]:
    width = max(len(field) for field in schema.unmapped)
    mapped = ", ".join(f"{field} <- {column}" for field, column in sorted(schema.mapping.items()))
    return [
        f"stream {schema.stream!r} (file {schema.file})",
        f"  columns found ({len(schema.columns)}): {', '.join(schema.columns) or _NOTHING}",
        f"  mapped ({len(schema.mapping)}): {mapped or _NOTHING}",
        f"  supplied as constants ({len(schema.constants)}): "
        f"{', '.join(schema.constants) or _NOTHING}",
        f"  unmapped, required ({len(schema.unmapped)}):",
        *[
            f"    {field.ljust(width)}  {FIELD_CONTRACTS[field]}"
            for field in sorted(schema.unmapped)
        ],
        f"  columns not used ({len(schema.unused)}): {', '.join(schema.unused) or _NOTHING}",
        "",
    ]


def _render(skeleton: Mapping[str, object]) -> str:
    return json.dumps(skeleton, indent=2, ensure_ascii=False, sort_keys=True)
