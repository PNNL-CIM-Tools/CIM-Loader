import logging

import requests

from cimloader._base_iri import DEFAULT_BASE_IRI, prepare_rdf_bytes
from cimloader.uploaders._graphmodel import upload_graph_via_sparql
from cimloader._formats import content_type_from_filename, content_type_from_url
from cimloader.databases import BlazegraphConnection

_log = logging.getLogger(__name__)


class BlazegraphUploader(BlazegraphConnection):
    def __init__(self, base_iri: str = DEFAULT_BASE_IRI) -> None:
        super().__init__()
        self.base_iri = base_iri

    def upload_from_file(self, filepath: str, filename: str) -> None:
        """Upload an RDF file to Blazegraph.

        Format is auto-detected from the file extension (.xml, .ttl, .nt,
        .nq, .jsonld, .trig, and their common aliases). RDF/XML files get
        `xml:base=<self.base_iri>` injected when they don't already declare
        one, so fragment IRIs (`#_UUID`) resolve deterministically.
        """
        content_type = content_type_from_filename(filename)
        with open(f"{filepath}/{filename}", "rb") as f:
            data = prepare_rdf_bytes(f.read(), content_type, self.base_iri)
        resp = requests.post(
            self.url, data=data, headers={"Content-Type": content_type}
        )
        resp.raise_for_status()

    def upload_from_url(self, url: str) -> None:
        """Fetch an RDF file from a URL and upload it to Blazegraph.

        Format is auto-detected from the URL path extension.
        """
        content_type = content_type_from_url(url)
        _log.info("Fetching %s for upload to Blazegraph", url)
        resp = requests.get(url)
        resp.raise_for_status()
        data = prepare_rdf_bytes(resp.content, content_type, self.base_iri)
        post = requests.post(
            self.url, data=data, headers={"Content-Type": content_type}
        )
        post.raise_for_status()

    def upload_from_graphmodel(self, graph_dict: dict) -> None:
        """Upload a CIMantic Graphs graph dict to Blazegraph.

        Accepts the ``graph`` of any GraphModel subclass (FeederModel,
        BusBranchModel, NodeBreakerModel) -- only the objects matter.
        """
        upload_graph_via_sparql(self, graph_dict, "Blazegraph")
