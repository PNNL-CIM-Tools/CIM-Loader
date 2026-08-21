"""Fetch model parts by checksum, with a local on-disk cache.

A part's identity is its checksum (`Part.checksum`). `fetch_part` tries each URL
in `Part.sources` in order — firewall-free mirrors (Zenodo) first, upstream
(OEDI etc.) after — and verifies the downloaded bytes against the checksum
before accepting them. Verified bytes are cached under `~/.cache/cimloader`
keyed by checksum, so a second fetch (and offline runs) skip the network.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import requests

from cimloader.downloaders.models import ModelEntry, Part

_log = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path("~/.cache/cimloader").expanduser()


def fetch_part(part: Part, cache_dir: str | Path = DEFAULT_CACHE_DIR) -> Path:
    """Return a local path to `part`, downloading + verifying if not cached.

    Tries `part.sources` in order; the first download whose sha256 matches
    `part.checksum` wins. Caches by checksum.

    Raises:
        ValueError: if `part.checksum` is not "sha256:<hex>", or if no source
            yielded bytes matching the checksum.
    """
    algo, expected = _parse_checksum(part.checksum)
    cache = Path(cache_dir).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    cached = cache / expected

    if cached.is_file() and _digest(cached.read_bytes(), algo) == expected:
        _log.debug("Cache hit for part %s (%s)", part.id, expected[:12])
        return cached

    errors: list[str] = []
    for url in part.sources:
        try:
            data = _get(url)
        except requests.RequestException as exc:
            errors.append(f"{url}: {exc}")
            continue
        actual = _digest(data, algo)
        if actual != expected:
            errors.append(f"{url}: checksum mismatch (got {actual[:12]}, want {expected[:12]})")
            continue
        cached.write_bytes(data)
        _log.info("Fetched part %s from %s (%s)", part.id, url, expected[:12])
        return cached

    raise ValueError(
        f"Could not fetch part {part.id!r} matching {part.checksum}. Tried:\n  "
        + "\n  ".join(errors)
    )


def fetch_model(entry: ModelEntry, cache_dir: str | Path = DEFAULT_CACHE_DIR) -> Path:
    """Fetch the `.cimx` package for a model.

    Today a model is a single package part; this returns its local path. When
    a model is split across multiple physical parts, this will return the
    package that contains them.
    """
    if len(entry.parts) != 1:
        # Multi-part fetch is a deliberate future step (see MODEL_PROVENANCE.md);
        # fail fast rather than silently fetching only the first part.
        raise NotImplementedError(
            f"Model {entry.id!r} has {len(entry.parts)} parts; multi-part fetch is not yet implemented"
        )
    return fetch_part(entry.parts[0], cache_dir)


def _get(url: str) -> bytes:
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.content


def _digest(data: bytes, algo: str) -> str:
    return hashlib.new(algo, data).hexdigest()


def _parse_checksum(checksum: str) -> tuple[str, str]:
    """Split 'sha256:<hex>' into (algo, hex). Fail fast on bad format."""
    if ":" not in checksum:
        raise ValueError(f"Checksum must be '<algo>:<hex>', got {checksum!r}")
    algo, _, hexdigest = checksum.partition(":")
    if algo not in hashlib.algorithms_available:
        raise ValueError(f"Unsupported checksum algorithm: {algo!r}")
    return algo, hexdigest.lower()
