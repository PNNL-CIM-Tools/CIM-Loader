"""Base-IRI normalization for RDF uploads.

CIM/CGMES files routinely use `rdf:ID="_UUID"` and `rdf:resource="#_UUID"`
without declaring a document base. Strict parsers (Oxigraph, Jena RIOT)
reject these as relative IRIs; permissive ones (Blazegraph) fall back to
the request URL, which mints endpoint-dependent IRIs that don't survive
migration between databases.

This module rewrites RDF/XML bytes to carry an explicit `xml:base` on the
root element before they reach the database, so every uploader produces
identical triples from the same input file.
"""

from __future__ import annotations

import re

DEFAULT_BASE_IRI = "http://gridappsd.org/cim/"

# Matches the opening `<rdf:RDF ...>` tag. We use a regex rather than a full
# XML parser because CIM files can be hundreds of MB and we only need to
# touch the root element — parsing + serializing would balloon both memory
# and wall time for large feeders.
_RDF_ROOT = re.compile(rb"<\s*rdf:RDF\b([^>]*)>", re.IGNORECASE)
_XML_BASE_ATTR = re.compile(rb'\bxml:base\s*=\s*["\'][^"\']*["\']', re.IGNORECASE)


def ensure_rdfxml_base(data: bytes, base_iri: str = DEFAULT_BASE_IRI) -> bytes:
    """Return `data` with `xml:base="<base_iri>"` set on the root `<rdf:RDF>`.

    If the file already declares `xml:base`, it is left untouched — the
    file's author made an explicit choice and we respect it. If not, the
    default is injected so fragment IRIs resolve deterministically.
    """
    match = _RDF_ROOT.search(data)
    if not match:
        # Not an RDF/XML document we recognize — pass through unchanged.
        return data

    attrs = match.group(1)
    if _XML_BASE_ATTR.search(attrs):
        return data

    new_attrs = attrs + b' xml:base="' + base_iri.encode("utf-8") + b'"'
    start, end = match.span()
    return data[:start] + b"<rdf:RDF" + new_attrs + b">" + data[end:]


def prepare_rdf_bytes(
    data: bytes, content_type: str, base_iri: str = DEFAULT_BASE_IRI
) -> bytes:
    """Normalize RDF bytes so fragment IRIs resolve against `base_iri`.

    Currently only RDF/XML is rewritten — it's the only format where CIM
    files routinely ship without a base. Turtle/N-Triples/N-Quads/JSON-LD
    pass through unchanged.
    """
    if content_type == "application/rdf+xml":
        return ensure_rdfxml_base(data, base_iri)
    return data
