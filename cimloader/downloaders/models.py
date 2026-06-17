"""Provenance data model for CIM model distribution.

Lightweight dataclasses mirroring the LinkML manifest schema (authored in
Powergrid-Models as `model_manifest.linkml.yaml`). These are kept as plain
dataclasses on purpose: `cimloader` parses the manifest with `pyyaml` and does
NOT take a `linkml`/`linkml-runtime` runtime dependency. The LinkML schema is
the contract and documentation; validation is an optional step in the catalog
repo, not at load time here.

Field semantics map to the IEC 61970-552 metadata profile:
- `ModelEntry.version`  ~ md:Dataset.version
- `ModelEntry.doi`      ~ citation identifier (no direct 552 slot)
- `Part.id`             ~ persistent OPC relationship Id (IEC 61970-557 §4.4)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Part:
    """One physical artifact within a model's distribution.

    A part maps to an OPC package part (IEC 61970-557). `id` is the persistent,
    portable relationship Id — identity is `id` + `checksum`, never `filename`
    (557 §4.5: filenames carry no meaning).
    """

    id: str                       # persistent NCName Id (557 §4.4)
    checksum: str                 # "sha256:..." — the fetch-resolve key
    sources: list[str]            # ordered fetch URLs; firewall-free first
    profile: str = "combined"     # combined | EQ | SSH | SV | TP | ...
    content_type: str = "application/rdf+xml"   # IANA/IETF type (557 §4.6)
    filename: str | None = None   # convenience only; NOT identity
    external: bool = False        # True => part lives off-package (TargetMode=External)


@dataclass
class ModelEntry:
    """One feeder model in the manifest catalog."""

    id: str                       # stable slug used by tests + loader
    family: str                   # = Zenodo record / DOI grouping
    parts: list[Part]
    version: str | None = None
    golden_format: str | None = None      # dss | raw | glm | cim_rdf
    golden_direction: str | None = None   # native_is_golden | cim_is_golden
    feeder_mrid: str | None = None
    doi: str | None = None        # family version DOI; None when none (e.g. OEDI)


@dataclass
class BootstrappedPart:
    """A package part after OPC bootstrap, ready to hand to an uploader.

    Carries either in-package `data` bytes or an `external_url` (never both).
    `role` is the resolved relationship type from the .rels file — the part's
    meaning comes from here, not from any filename.
    """

    id: str
    content_type: str
    role: str                     # resolved .rels Relationship/@Type
    data: bytes | None = None
    external_url: str | None = None


@dataclass
class Package:
    """Result of reading an OPC `.cimx` package (IEC 61970-557 §4 bootstrap)."""

    conforms_to: str | None       # dcterms:conformsTo (business-process profile IRI)
    core_props: dict = field(default_factory=dict)
    business_metadata: BootstrappedPart | None = None
    grid_parts: list[BootstrappedPart] = field(default_factory=list)
