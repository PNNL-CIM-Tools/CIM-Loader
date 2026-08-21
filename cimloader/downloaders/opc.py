"""Read an OPC `.cimx` package per IEC 61970-557 §4 (normative bootstrap).

A `.cimx` file is an OpenXML/OPC package — a ZIP whose well-known parts describe
the rest. The bootstrap order is fixed by the standard:

1. ``[Content_Types].xml`` — serialization per part (Default-by-extension plus
   per-part Override).
2. ``_rels/.rels`` — every part's persistent Id, Target, TargetMode and Type.
   OPC's own relationship types are interpretable immediately; business types
   are NOT, until step 3 (557 §4.3).
3. ``docProps/core.xml`` (+ custom props) — Dublin Core header and
   ``dcterms:conformsTo`` (the business-process profile IRI).
4. With ``conformsTo`` known, resolve business relationship types: find the one
   ``BusinessProcessMetadata`` part and the grid parts.

A part's meaning comes from its relationship Type, never its filename
(557 §4.5). The business-metadata graph itself (IEC 61970-552 Dataset/Activity
RDF) is parsed separately — see ``parse_business_metadata`` (still stubbed
pending a concrete instance).
"""

from __future__ import annotations

import logging
import posixpath
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from cimloader._formats import content_type_from_filename
from cimloader.downloaders.models import BootstrappedPart, Package

_log = logging.getLogger(__name__)

# OPC + relationship namespaces (ISO/IEC 29500).
_NS_CONTENT_TYPES = "http://schemas.openxmlformats.org/package/2006/content-types"
_NS_RELATIONSHIPS = "http://schemas.openxmlformats.org/package/2006/relationships"
_NS_CORE_PROPS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
_NS_DCTERMS = "http://purl.org/dc/terms/"

# Relationship types (557 §4.2; OPC standard types §4.3).
_REL_CORE_PROPS = "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties"
_REL_BUSINESS_METADATA = "http://cim-type.ucaiug.io/package/BusinessProcessMetadata"


def read_package(cimx_path: str | Path) -> Package:
    """Bootstrap an OPC `.cimx` package into a Package (557 §4)."""
    path = Path(cimx_path)
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        content_types = _parse_content_types(_read(zf, "[Content_Types].xml"))
        rels = _parse_rels(_read(zf, "_rels/.rels"))

        core_props, conforms_to = _read_core_props(zf, rels, names)

        business_metadata = None
        grid_parts: list[BootstrappedPart] = []
        for rel in rels:
            if rel["type"] == _REL_CORE_PROPS:
                continue  # handled above
            part = _bootstrap_part(zf, rel, content_types, names)
            if rel["type"] == _REL_BUSINESS_METADATA:
                business_metadata = part
            else:
                # Everything else is a business-defined part; per 557 §4.3 its
                # precise role is interpreted by the business process named in
                # conforms_to. We surface them as grid parts with their raw type.
                grid_parts.append(part)

    return Package(
        conforms_to=conforms_to,
        core_props=core_props,
        business_metadata=business_metadata,
        grid_parts=grid_parts,
    )


def parse_business_metadata(part: BootstrappedPart) -> dict:
    """Parse the IEC 61970-552 metadata graph from a BusinessMetadata package part.

    Returns a dict with:
      full_model_uuid  — rdf:about of md:FullModel (the root dataset identity)
      distributions    — list of dicts per dcat:Distribution:
                           uuid, access_url, byte_size, media_type, checksum,
                           conforms_to (list of profile IRIs), dataset_uuid
      datasets         — list of dicts per cim:BoundaryModel / cim:GridDataset:
                           uuid, title, profile_type, issued, defines_uuid,
                           contains (list of child dataset UUIDs)

    Namespace URIs follow the concrete instance (IEC 61970-552 ModelDescription/3):
      md:  http://iec.ch/TC57/61970-552/ModelDescription/3#
      cim: http://cim.ucaiug.io/ns#
      dcat: http://www.w3.org/ns/dcat#
      dcterms: http://purl.org/dc/terms/
      spdx: http://spdx.org/rdf/terms#
    """
    data = part.data
    if data is None:
        raise ValueError("parse_business_metadata: part has no data (external parts not supported)")

    _NS = {
        "rdf":     "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "md":      "http://iec.ch/TC57/61970-552/ModelDescription/3#",
        "cim":     "http://cim.ucaiug.io/ns#",
        "dcat":    "http://www.w3.org/ns/dcat#",
        "dcterms": "http://purl.org/dc/terms/",
        "spdx":    "http://spdx.org/rdf/terms#",
    }

    def _ns(prefix: str, local: str) -> str:
        return f"{{{_NS[prefix]}}}{local}"

    def _about(el) -> str:
        return el.attrib.get(_ns("rdf", "about"), "")

    def _resource(el) -> str:
        return el.attrib.get(_ns("rdf", "resource"), "")

    root = ET.fromstring(data)

    full_model_uuid = None
    distributions = []
    datasets = []

    for el in root:
        tag = el.tag

        if tag == _ns("md", "FullModel"):
            full_model_uuid = _about(el)

        elif tag == _ns("dcat", "Distribution"):
            dist: dict = {"uuid": _about(el), "conforms_to": []}
            for child in el:
                ctag = child.tag
                if ctag == _ns("dcat", "Distribution.accessURL"):
                    dist["access_url"] = (child.text or "").strip()
                elif ctag == _ns("dcat", "Distribution.byteSize"):
                    dist["byte_size"] = (child.text or "").strip()
                elif ctag == _ns("dcat", "Distribution.mediaType"):
                    dist["media_type"] = (child.text or "").strip()
                elif ctag == _ns("spdx", "Distribution.checksum"):
                    dist["checksum"] = (child.text or "").strip()
                elif ctag == _ns("dcterms", "Distribution.conformsTo"):
                    dist["conforms_to"].append(_resource(child))
                elif ctag == _ns("dcat", "Distribution.DataSet"):
                    dist["dataset_uuid"] = _resource(child)
            distributions.append(dist)

        elif tag in (_ns("cim", "BoundaryModel"), _ns("cim", "GridDataset")):
            ds: dict = {"uuid": _about(el), "contains": []}
            for child in el:
                ctag = child.tag
                if ctag == _ns("dcterms", "MetaThing.title"):
                    ds["title"] = (child.text or "").strip()
                elif ctag == _ns("dcterms", "Distribution.issued"):
                    ds["issued"] = (child.text or "").strip()
                elif ctag == _ns("cim", "GridDataset.profileType"):
                    ds["profile_type"] = (child.text or "").strip()
                elif ctag == _ns("cim", "BoundaryModel.Defines"):
                    ds["defines_uuid"] = _resource(child)
                elif ctag == _ns("cim", "GridDataset.Contains"):
                    ds["contains"].append(_resource(child))
            datasets.append(ds)

    return {
        "full_model_uuid": full_model_uuid,
        "distributions": distributions,
        "datasets": datasets,
    }


# --- internals -------------------------------------------------------------


def _read(zf: zipfile.ZipFile, name: str) -> bytes:
    try:
        return zf.read(name)
    except KeyError:
        raise ValueError(f"Malformed .cimx: required part {name!r} is missing") from None


def _parse_content_types(data: bytes) -> "ContentTypes":
    """Parse [Content_Types].xml into a (defaults-by-ext, overrides-by-part) lookup."""
    root = ET.fromstring(data)
    defaults: dict[str, str] = {}
    overrides: dict[str, str] = {}
    for el in root:
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "Default":
            defaults[el.attrib["Extension"].lower()] = el.attrib["ContentType"]
        elif tag == "Override":
            overrides[el.attrib["PartName"]] = el.attrib["ContentType"]
    return ContentTypes(defaults, overrides)


def _parse_rels(data: bytes) -> list[dict]:
    """Parse _rels/.rels into a list of {id, target, type, external} dicts."""
    root = ET.fromstring(data)
    rels = []
    for el in root:
        if el.tag.rsplit("}", 1)[-1] != "Relationship":
            continue
        rels.append({
            "id": el.attrib["Id"],
            "target": el.attrib["Target"],
            "type": el.attrib["Type"],
            "external": el.attrib.get("TargetMode") == "External",
        })
    return rels


def _read_core_props(
    zf: zipfile.ZipFile, rels: list[dict], names: set[str]
) -> tuple[dict, str | None]:
    """Read docProps/core.xml (located via its rel type) → (props, conformsTo)."""
    core_rel = next((r for r in rels if r["type"] == _REL_CORE_PROPS), None)
    if core_rel is None:
        # 557 §4.2: core properties shall not be omitted.
        raise ValueError("Malformed .cimx: no core-properties relationship in .rels")

    part_name = core_rel["target"].lstrip("/")
    if part_name not in names:
        raise ValueError(f"Malformed .cimx: core props part {part_name!r} not in package")

    root = ET.fromstring(zf.read(part_name))
    props: dict[str, str] = {}
    conforms_to = None
    for el in root:
        tag = el.tag.rsplit("}", 1)[-1]
        text = (el.text or "").strip()
        props[tag] = text
        if el.tag == f"{{{_NS_DCTERMS}}}conformsTo":
            conforms_to = text
    return props, conforms_to


def _bootstrap_part(
    zf: zipfile.ZipFile, rel: dict, content_types: "ContentTypes", names: set[str]
) -> BootstrappedPart:
    """Resolve one relationship into a BootstrappedPart (in-package or external)."""
    if rel["external"]:
        return BootstrappedPart(
            id=rel["id"],
            content_type=content_types.for_part(rel["target"]),
            role=rel["type"],
            external_url=rel["target"],
        )

    part_name = rel["target"].lstrip("/")
    if part_name not in names:
        raise ValueError(f"Malformed .cimx: part {part_name!r} (rel {rel['id']}) not in package")
    return BootstrappedPart(
        id=rel["id"],
        content_type=content_types.for_part(part_name),
        role=rel["type"],
        data=zf.read(part_name),
    )


class ContentTypes:
    """Content-type lookup: per-part Override wins, else Default-by-extension."""

    def __init__(self, defaults: dict[str, str], overrides: dict[str, str]) -> None:
        self._defaults = defaults
        self._overrides = overrides

    def for_part(self, target: str) -> str:
        # Overrides are keyed by absolute PartName ("/Area1EQ.xml").
        part_name = "/" + target.lstrip("/")
        if part_name in self._overrides:
            return self._overrides[part_name]
        ext = posixpath.splitext(target)[1].lstrip(".").lower()
        if ext in self._defaults:
            return self._defaults[ext]
        # Last resort: derive from the extension via the shared RDF map.
        return content_type_from_filename(target)
