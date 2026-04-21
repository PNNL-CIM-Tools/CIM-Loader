"""AWS Neptune uploader for CIM data.

Uploads RDF data to a Neptune cluster via HTTP POST to its SPARQL
endpoint. AWS SigV4 auth and S3 bulk loading are planned — see
`design/TODO.md`.
"""

from __future__ import annotations

import logging
import subprocess

import requests

from cimloader._formats import content_type_from_filename, content_type_from_url
from cimloader.databases import NeptuneConnection

_log = logging.getLogger(__name__)


class NeptuneUploader(NeptuneConnection):
    def __init__(self) -> None:
        super().__init__()

    def upload_from_file(self, filepath: str, filename: str) -> None:
        """Upload an RDF file to Neptune via HTTP POST.

        Format is auto-detected from the file extension. For large
        datasets (>100MB), Neptune's S3 bulk loader is recommended
        (not yet implemented).
        """
        content_type = content_type_from_filename(filename)
        self._upload(filepath, filename, content_type)

    def upload_from_url(self, url: str) -> None:
        """Fetch an RDF file from a URL and upload it to Neptune.

        Format is auto-detected from the URL path extension. IAM-protected
        clusters will reject the POST until AWS SigV4 signing is added —
        see `design/TODO.md`.
        """
        content_type = content_type_from_url(url)

        if self.use_iam_auth:
            _log.warning(
                "AWS authentication not fully implemented. "
                "Upload may fail if Neptune requires IAM authentication."
            )

        _log.info("Fetching %s for upload to Neptune", url)
        resp = requests.get(url)
        resp.raise_for_status()
        post = requests.post(
            self.url,
            data=resp.content,
            headers={"Content-Type": content_type},
        )
        post.raise_for_status()
        _log.info("Successfully uploaded %s to Neptune", url)

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

    def _upload(self, filepath: str, filename: str, content_type: str) -> None:
        full_path = f"{filepath}/{filename}"

        if self.use_iam_auth:
            _log.warning(
                "AWS authentication not fully implemented. "
                "Upload may fail if Neptune requires IAM authentication."
            )

        _log.info("Uploading %s to Neptune at %s", filename, self.url)

        cmd = [
            "curl", "-X", "POST",
            "-H", f"Content-Type: {content_type}",
            "--data-binary", f"@{full_path}",
            self.url,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            _log.info("Successfully uploaded %s to Neptune", filename)
            if result.stdout:
                _log.debug("Response: %s", result.stdout)
        except subprocess.CalledProcessError as e:
            _log.error("Failed to upload %s to Neptune: %s", filename, e.stderr)
            raise
