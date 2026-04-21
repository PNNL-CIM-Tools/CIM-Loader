"""AWS Neptune uploader for CIM data.

Uploads RDF data to a Neptune cluster via HTTP POST to its SPARQL
endpoint. AWS SigV4 auth and S3 bulk loading are planned — see
`design/TODO.md`.
"""

from __future__ import annotations

import logging

import requests

from cimloader._base_iri import DEFAULT_BASE_IRI, prepare_rdf_bytes
from cimloader._formats import content_type_from_filename, content_type_from_url
from cimloader.databases import NeptuneConnection

_log = logging.getLogger(__name__)


class NeptuneUploader(NeptuneConnection):
    def __init__(self, base_iri: str = DEFAULT_BASE_IRI) -> None:
        super().__init__()
        self.base_iri = base_iri

    def upload_from_file(self, filepath: str, filename: str) -> None:
        """Upload an RDF file to Neptune via HTTP POST.

        Format is auto-detected from the file extension. RDF/XML files get
        `xml:base=<self.base_iri>` injected when they don't already declare
        one, so fragment IRIs (`#_UUID`) resolve deterministically. For
        large datasets (>100MB), Neptune's S3 bulk loader is recommended
        (not yet implemented).
        """
        content_type = content_type_from_filename(filename)
        with open(f"{filepath}/{filename}", "rb") as f:
            data = prepare_rdf_bytes(f.read(), content_type, self.base_iri)
        self._post(data, filename, content_type)

    def upload_from_url(self, url: str) -> None:
        """Fetch an RDF file from a URL and upload it to Neptune.

        Format is auto-detected from the URL path extension. IAM-protected
        clusters will reject the POST until AWS SigV4 signing is added —
        see `design/TODO.md`.
        """
        content_type = content_type_from_url(url)
        _log.info("Fetching %s for upload to Neptune", url)
        resp = requests.get(url)
        resp.raise_for_status()
        data = prepare_rdf_bytes(resp.content, content_type, self.base_iri)
        self._post(data, url, content_type)

    def upload_from_graphmodel(self, graph_dict: dict, feeder_mrid: str | None = None) -> None:
        """Upload a CIMantic Graphs GraphModel to Neptune."""
        from cimgraph.models import FeederModel

        if self.cim is None:
            raise RuntimeError(
                "CIM profile not configured. Set CIMG_CIM_PROFILE environment variable."
            )

        if feeder_mrid:
            container = self.cim.Feeder(mRID=feeder_mrid)
        else:
            import uuid
            container = self.cim.Feeder(mRID=str(uuid.uuid4()))

        _log.info("Uploading graph with %d object types to Neptune", len(graph_dict))
        FeederModel(container=container, connection=self, graph=graph_dict)

    def _post(self, data: bytes, source: str, content_type: str) -> None:
        if self.use_iam_auth:
            _log.warning(
                "AWS authentication not fully implemented. "
                "Upload may fail if Neptune requires IAM authentication."
            )
        _log.info("Uploading %s to Neptune at %s", source, self.url)
        resp = requests.post(
            self.url, data=data, headers={"Content-Type": content_type}
        )
        resp.raise_for_status()
        _log.info("Successfully uploaded %s to Neptune", source)
