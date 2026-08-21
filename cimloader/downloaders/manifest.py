"""Load the model-provenance manifest and look up entries.

The manifest (`models.yaml`) is owned by the catalog repo (Powergrid-Models),
NOT shipped in this wheel — `cimloader` is pure mechanism. Every entry point
takes an explicit path and fails fast if it is missing or malformed.

Parsing is plain `pyyaml` into the dataclasses in `models.py`; there is no
LinkML validation here (that is an optional CI step in the catalog repo).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from cimloader.downloaders.models import ModelEntry, Part


def load_manifest(path: str | Path) -> list[ModelEntry]:
    """Parse a manifest YAML file into a list of ModelEntry.

    Args:
        path: Explicit path to the manifest YAML. Required — there is no
            default location or env-var fallback.

    Raises:
        FileNotFoundError: if `path` does not exist.
        ValueError: if the YAML is not a list of model entries, or an entry
            is missing required fields.
    """
    p = Path(path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"Manifest not found: {p}")

    raw = yaml.safe_load(p.read_text())
    if not isinstance(raw, list):
        raise ValueError(
            f"Manifest {p} must be a YAML list of model entries, got {type(raw).__name__}"
        )

    return [_entry_from_dict(item, p) for item in raw]


def find(entries: list[ModelEntry], model_id: str) -> ModelEntry:
    """Return the entry with the given id.

    Raises:
        KeyError: if no entry matches `model_id`.
    """
    for entry in entries:
        if entry.id == model_id:
            return entry
    raise KeyError(f"Model id {model_id!r} not in manifest")


def _entry_from_dict(item: dict, source: Path) -> ModelEntry:
    """Build a ModelEntry from one parsed YAML mapping, failing fast on shape."""
    if not isinstance(item, dict):
        raise ValueError(f"Manifest {source}: each entry must be a mapping, got {item!r}")

    raw_parts = item.get("parts")
    if not isinstance(raw_parts, list) or not raw_parts:
        raise ValueError(f"Manifest {source}: entry {item.get('id')!r} needs a non-empty 'parts' list")

    try:
        parts = [_part_from_dict(p, source) for p in raw_parts]
        return ModelEntry(
            id=item["id"],
            family=item["family"],
            parts=parts,
            version=item.get("version"),
            golden_format=item.get("golden_format"),
            golden_direction=item.get("golden_direction"),
            feeder_mrid=item.get("feeder_mrid"),
            doi=item.get("doi"),
        )
    except KeyError as missing:
        raise ValueError(f"Manifest {source}: entry missing required field {missing}") from None


def _part_from_dict(p: dict, source: Path) -> Part:
    if not isinstance(p, dict):
        raise ValueError(f"Manifest {source}: each part must be a mapping, got {p!r}")
    try:
        return Part(
            id=p["id"],
            checksum=p["checksum"],
            sources=p["sources"],
            profile=p.get("profile", "combined"),
            content_type=p.get("content_type", "application/rdf+xml"),
            filename=p.get("filename"),
            external=p.get("external", False),
        )
    except KeyError as missing:
        raise ValueError(f"Manifest {source}: part missing required field {missing}") from None
