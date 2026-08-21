"""Oxigraph uploader for CIM data.

Uploads RDF data to an Oxigraph triplestore via its /store REST endpoint.
"""

from __future__ import annotations

import logging

import requests

from cimloader._base_iri import DEFAULT_BASE_IRI, prepare_rdf_bytes
from cimloader.uploaders._graphmodel import upload_graph_via_sparql
from cimloader._formats import content_type_from_filename, content_type_from_url
from cimloader.databases import OxigraphConnection

_log = logging.getLogger(__name__)


class OxigraphUploader(OxigraphConnection):
    def __init__(self, base_iri: str = DEFAULT_BASE_IRI) -> None:
        super().__init__()
        self.base_iri = base_iri

        # Oxigraph's SPARQL URL typically ends in /query; strip it to get
        # the base URL for the /store upload endpoint.
        if self.url.endswith('/query'):
            base_url = self.url.rsplit('/query', 1)[0]
        else:
            base_url = self.url
        # Post to ?default so triples land in the default graph — without
        # the parameter, Oxigraph creates a fresh named graph per request
        # and SELECT WHERE {?s ?p ?o} sees nothing.
        self.upload_endpoint = f"{base_url}/store?default"

    def upload_from_file(self, filepath: str, filename: str) -> None:
        """Upload an RDF file to Oxigraph.

        Format is auto-detected from the file extension. RDF/XML files get
        `xml:base=<self.base_iri>` injected when they don't already declare
        one, so fragment IRIs (`#_UUID`) resolve deterministically.
        """
        content_type = content_type_from_filename(filename)
        with open(f"{filepath}/{filename}", "rb") as f:
            data = prepare_rdf_bytes(f.read(), content_type, self.base_iri)
        _log.info("Uploading %s to Oxigraph at %s", filename, self.upload_endpoint)
        resp = requests.post(
            self.upload_endpoint,
            data=data,
            headers={"Content-Type": content_type},
        )
        resp.raise_for_status()
        _log.info("Successfully uploaded %s to Oxigraph", filename)

    def upload_from_url(self, url: str) -> None:
        """Fetch an RDF file from a URL and upload it to Oxigraph.

        Format is auto-detected from the URL path extension.
        """
        content_type = content_type_from_url(url)
        _log.info("Fetching %s for upload to Oxigraph", url)
        resp = requests.get(url)
        resp.raise_for_status()
        data = prepare_rdf_bytes(resp.content, content_type, self.base_iri)
        post = requests.post(
            self.upload_endpoint,
            data=data,
            headers={"Content-Type": content_type},
        )
        post.raise_for_status()
        _log.info("Successfully uploaded %s to Oxigraph", url)

    def upload_part(self, part) -> None:
        """Upload a BootstrappedPart from an OPC `.cimx` package.

        Dispatches on the part's content_type. External parts
        (`TargetMode="External"`) are fetched + posted via `upload_from_url`;
        in-package parts post their bytes directly. `part` is a
        `cimloader.downloaders.models.BootstrappedPart`.
        """
        if part.external_url is not None:
            self.upload_from_url(part.external_url)
            return

        if part.data is None:
            raise ValueError(f"Part {part.id!r} has neither data nor external_url")

        data = prepare_rdf_bytes(part.data, part.content_type, self.base_iri)
        _log.info("Uploading part %s (%s) to Oxigraph", part.id, part.content_type)
        resp = requests.post(
            self.upload_endpoint,
            data=data,
            headers={"Content-Type": part.content_type},
        )
        resp.raise_for_status()
        _log.info("Successfully uploaded part %s to Oxigraph", part.id)

    def upload_from_graphmodel(self, graph_dict: dict) -> None:
        """Upload a CIMantic Graphs graph dict to Oxigraph.

        Accepts the ``graph`` of any GraphModel subclass (FeederModel,
        BusBranchModel, NodeBreakerModel) -- only the objects matter.
        """
        upload_graph_via_sparql(self, graph_dict, "Oxigraph")
