"""Unit tests for the provenance downloaders (manifest, fetch, OPC bootstrap).

These are pure unit tests — no docker, no network. The `.cimx` fixture is built
in-process with `zipfile` so the package structure is visible in the test, and
network fetches are exercised via monkeypatched `requests.get`.
"""

from __future__ import annotations

import hashlib
import io
import textwrap
import zipfile

import pytest

from cimloader.downloaders import (
    fetch_part,
    find,
    load_manifest,
    read_package,
    parse_business_metadata,
)
from cimloader.downloaders.models import Part


# --- .cimx fixture ---------------------------------------------------------

CONTENT_TYPES = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml" />
  <Default Extension="xml" ContentType="application/xml" />
  <Override PartName="/BusinessMetadata.xml" ContentType="application/rdf+xml" />
  <Override PartName="/payload_a.xml" ContentType="application/rdf+xml" />
  <Override PartName="/payload_b.json" ContentType="application/ld+json" />
</Types>
"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="file1" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="file2" Type="http://cim-type.ucaiug.io/package/BusinessProcessMetadata" Target="BusinessMetadata.xml"/>
  <Relationship Id="file3" Type="http://cim-type.ucaiug.io/package/GridData" Target="payload_a.xml"/>
  <Relationship Id="file4" Type="http://cim-type.ucaiug.io/package/GridData" Target="payload_b.json"/>
  <Relationship Id="file5" Type="http://cim-type.ucaiug.io/package/GridData" Target="http://myserver/CombinedTP.xml" TargetMode="External"/>
</Relationships>
"""

CORE_XML = """<?xml version="1.0" encoding="utf-8"?>
<coreProperties xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns="http://schemas.openxmlformats.org/package/2006/metadata/core-properties">
  <dc:creator>Test Author</dc:creator>
  <dcterms:conformsTo>http://cim-profile.ucaiug.io/grid/StandardBusinessProcess/1.0</dcterms:conformsTo>
</coreProperties>
"""


@pytest.fixture
def cimx(tmp_path):
    """Write a minimal valid .cimx package and return its path."""
    path = tmp_path / "sample.cimx"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", RELS)
        zf.writestr("docProps/core.xml", CORE_XML)
        zf.writestr("BusinessMetadata.xml", "<rdf:RDF/>")
        zf.writestr("payload_a.xml", "<rdf:RDF/>")
        zf.writestr("payload_b.json", "{}")
    return path


# --- read_package (OPC bootstrap) -----------------------------------------

def test_read_package_surfaces_conforms_to(cimx):
    pkg = read_package(cimx)
    assert pkg.conforms_to == "http://cim-profile.ucaiug.io/grid/StandardBusinessProcess/1.0"
    assert pkg.core_props["creator"] == "Test Author"


def test_read_package_finds_business_metadata_by_rel_type(cimx):
    pkg = read_package(cimx)
    assert pkg.business_metadata is not None
    assert pkg.business_metadata.id == "file2"


def test_read_package_resolves_roles_not_filenames(cimx):
    pkg = read_package(cimx)
    # Three GridData parts; role comes from the .rels Type, never the name.
    roles = {p.id: p.role for p in pkg.grid_parts}
    assert roles == {
        "file3": "http://cim-type.ucaiug.io/package/GridData",
        "file4": "http://cim-type.ucaiug.io/package/GridData",
        "file5": "http://cim-type.ucaiug.io/package/GridData",
    }


def test_read_package_content_type_per_part(cimx):
    pkg = read_package(cimx)
    by_id = {p.id: p for p in pkg.grid_parts}
    # Mixed serialization in one package: rdf+xml and ld+json side by side.
    assert by_id["file3"].content_type == "application/rdf+xml"
    assert by_id["file4"].content_type == "application/ld+json"


def test_read_package_flags_external_part(cimx):
    pkg = read_package(cimx)
    external = [p for p in pkg.grid_parts if p.external_url]
    assert len(external) == 1
    assert external[0].id == "file5"
    assert external[0].external_url == "http://myserver/CombinedTP.xml"
    assert external[0].data is None


def test_read_package_missing_content_types_fails_fast(tmp_path):
    path = tmp_path / "bad.cimx"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("_rels/.rels", RELS)
    with pytest.raises(ValueError, match="Content_Types"):
        read_package(path)


def test_parse_business_metadata_is_stubbed(cimx):
    pkg = read_package(cimx)
    with pytest.raises(NotImplementedError, match="61970-552"):
        parse_business_metadata(pkg.business_metadata)


# --- manifest --------------------------------------------------------------

MANIFEST = textwrap.dedent("""
    - id: ieee13
      family: ieee-test-feeders
      version: "2024.1"
      golden_format: cim_rdf
      golden_direction: native_is_golden
      feeder_mrid: "_49AD8E07"
      doi: "10.5281/zenodo.000000"
      parts:
        - id: _abc123
          profile: combined
          content_type: application/rdf+xml
          filename: ieee13.cimx
          checksum: "sha256:deadbeef"
          sources:
            - https://zenodo.org/records/1/files/ieee13.cimx?download=1
""")


@pytest.fixture
def manifest_file(tmp_path):
    path = tmp_path / "models.yaml"
    path.write_text(MANIFEST)
    return path


def test_load_manifest_and_find(manifest_file):
    entries = load_manifest(manifest_file)
    m = find(entries, "ieee13")
    assert m.family == "ieee-test-feeders"
    assert m.golden_direction == "native_is_golden"
    assert [p.id for p in m.parts] == ["_abc123"]
    assert m.parts[0].content_type == "application/rdf+xml"


def test_load_manifest_missing_path_fails_fast(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_manifest(tmp_path / "nope.yaml")


def test_find_unknown_id_raises(manifest_file):
    entries = load_manifest(manifest_file)
    with pytest.raises(KeyError):
        find(entries, "does-not-exist")


def test_load_manifest_rejects_non_list(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("id: ieee13\n")  # mapping, not a list
    with pytest.raises(ValueError, match="list of model entries"):
        load_manifest(path)


# --- fetch (checksum + cache, monkeypatched network) -----------------------

def _part_for(payload: bytes, *sources) -> Part:
    digest = hashlib.sha256(payload).hexdigest()
    return Part(id="_p", checksum=f"sha256:{digest}", sources=list(sources))


def test_fetch_part_verifies_and_caches(tmp_path, monkeypatch):
    payload = b"<rdf:RDF>ok</rdf:RDF>"
    calls = {"n": 0}

    def fake_get(url, timeout=60):
        calls["n"] += 1
        return _FakeResp(payload)

    monkeypatch.setattr("cimloader.downloaders.fetch.requests.get", fake_get)
    part = _part_for(payload, "https://example/ieee13.cimx")

    p1 = fetch_part(part, cache_dir=tmp_path)
    assert p1.read_bytes() == payload
    # Second call is a cache hit — no extra network.
    p2 = fetch_part(part, cache_dir=tmp_path)
    assert p2 == p1
    assert calls["n"] == 1


def test_fetch_part_checksum_mismatch_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "cimloader.downloaders.fetch.requests.get",
        lambda url, timeout=60: _FakeResp(b"corrupted"),
    )
    part = _part_for(b"original", "https://example/ieee13.cimx")
    with pytest.raises(ValueError, match="checksum"):
        fetch_part(part, cache_dir=tmp_path)


def test_fetch_part_tries_sources_in_order(tmp_path, monkeypatch):
    payload = b"good"

    def fake_get(url, timeout=60):
        if "mirror" in url:
            return _FakeResp(payload)
        raise __import__("requests").RequestException("down")

    monkeypatch.setattr("cimloader.downloaders.fetch.requests.get", fake_get)
    part = _part_for(payload, "https://primary/down", "https://mirror/good")
    assert fetch_part(part, cache_dir=tmp_path).read_bytes() == payload


class _FakeResp:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        pass
