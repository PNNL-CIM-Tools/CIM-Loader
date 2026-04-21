"""Oxigraph uploader for CIM data.

Uploads RDF data to an Oxigraph triplestore via its /store REST endpoint,
either directly over HTTP or by copying the file into a Docker container
first and running curl inside.
"""

from __future__ import annotations

import logging
import subprocess

import requests

from cimloader._formats import content_type_from_filename, content_type_from_url
from cimloader.databases import OxigraphConnection

_log = logging.getLogger(__name__)


class OxigraphUploader(OxigraphConnection):
    def __init__(self, container: str | None = None) -> None:
        super().__init__()
        self.container = container

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

        Format is auto-detected from the file extension.
        """
        content_type = content_type_from_filename(filename)
        self._upload(filepath, filename, content_type)

    def upload_from_url(self, url: str) -> None:
        """Fetch an RDF file from a URL and upload it to Oxigraph.

        Format is auto-detected from the URL path extension.
        """
        content_type = content_type_from_url(url)
        _log.info("Fetching %s for upload to Oxigraph", url)
        resp = requests.get(url)
        resp.raise_for_status()
        post = requests.post(
            self.upload_endpoint,
            data=resp.content,
            headers={"Content-Type": content_type},
        )
        post.raise_for_status()
        _log.info("Successfully uploaded %s to Oxigraph", url)

    def upload_from_graphmodel(self, graph_dict: dict, feeder_mrid: str | None = None) -> None:
        """Upload a CIMantic Graphs GraphModel to Oxigraph."""
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

        _log.info("Uploading graph with %d object types to Oxigraph", len(graph_dict))
        FeederModel(container=container, connection=self, graph=graph_dict)

    def _upload(self, filepath: str, filename: str, content_type: str) -> None:
        full_path = f"{filepath}/{filename}"

        if self.container:
            container_path = f"/tmp/{filename}"
            _log.info("Copying %s to container %s:%s", full_path, self.container, container_path)
            subprocess.check_call([
                "docker", "cp", full_path, f"{self.container}:{container_path}",
            ])
            _log.info("Uploading %s to Oxigraph in container", filename)
            subprocess.check_call([
                "docker", "exec", self.container,
                "curl", "-X", "POST",
                "-H", f"Content-Type: {content_type}",
                "--data-binary", f"@{container_path}",
                self.upload_endpoint,
            ])
            subprocess.call([
                "docker", "exec", self.container, "rm", container_path,
            ])
        else:
            _log.info("Uploading %s to Oxigraph at %s", filename, self.upload_endpoint)
            subprocess.check_call([
                "curl", "-X", "POST",
                "-H", f"Content-Type: {content_type}",
                "--data-binary", f"@{full_path}",
                self.upload_endpoint,
            ])

        _log.info("Successfully uploaded %s to Oxigraph", filename)
