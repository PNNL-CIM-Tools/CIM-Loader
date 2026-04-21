from __future__ import annotations

import logging
import os
import subprocess
import tempfile

import requests

from cimloader._base_iri import DEFAULT_BASE_IRI, prepare_rdf_bytes
from cimloader._formats import content_type_from_filename, content_type_from_url
from cimloader.databases.neo4j import Neo4jConnection

_log = logging.getLogger(__name__)

# n10s uses its own format name strings, not MIME content types.
_CONTENT_TYPE_TO_N10S = {
    'application/rdf+xml':    'RDF/XML',
    'text/turtle':            'Turtle',
    'application/n-triples':  'N-Triples',
    'application/n-quads':    'N-Quads',
    'application/ld+json':    'JSON-LD',
    'application/trig':       'TriG',
}


class Neo4jUploader(Neo4jConnection):
    def __init__(
        self,
        container: str | None = None,
        base_iri: str = DEFAULT_BASE_IRI,
    ) -> None:
        super().__init__()
        self.container = container
        self.base_iri = base_iri
        self.connect()

    def upload_from_file(self, filepath: str, filename: str):
        """Upload an RDF file to Neo4j via the n10s plugin.

        Format is auto-detected from the file extension. If a `container`
        was given at construction time the (rewritten) file is `docker
        cp`'d into the Neo4j container first; otherwise the path must
        already be reachable from the Neo4j process. RDF/XML files get
        `xml:base=<self.base_iri>` injected when they don't already
        declare one.
        """
        content_type = content_type_from_filename(filename)
        with open(f"{filepath}/{filename}", "rb") as f:
            data = prepare_rdf_bytes(f.read(), content_type, self.base_iri)
        return self._upload_bytes(data, filename, content_type)

    def upload_from_url(self, url: str):
        """Fetch an RDF file from a URL and import it via the n10s plugin.

        We download + rewrite the bytes in-process so Neo4j sees the same
        base-IRI-normalized content every other uploader produces. The
        rewritten bytes are staged into Neo4j's import directory and
        n10s.rdf.import.fetch reads them with a file:// URL.
        """
        content_type = content_type_from_url(url)
        filename = os.path.basename(url.split('?', 1)[0].split('#', 1)[0])
        _log.info("Fetching %s for import into Neo4j", url)
        resp = requests.get(url)
        resp.raise_for_status()
        data = prepare_rdf_bytes(resp.content, content_type, self.base_iri)
        return self._upload_bytes(data, filename, content_type)

    def upload_from_graphmodel(self, graph_dict: dict, feeder_mrid: str | None = None):
        """Upload a CIMantic Graphs GraphModel to Neo4j."""
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

        _log.info("Uploading graph with %d object types to Neo4j", len(graph_dict))
        FeederModel(container=container, connection=self, graph=graph_dict)

    def _upload_bytes(self, data: bytes, filename: str, content_type: str):
        """Stage `data` somewhere n10s can read and call fetch()."""
        n10s_format = _CONTENT_TYPE_TO_N10S[content_type]

        # Write to a temp file on the host, then either docker-cp it into
        # the container's import dir or (if no container was given) hand
        # n10s the host path directly.
        with tempfile.NamedTemporaryFile(
            prefix="cimloader-", suffix=f"-{filename}", delete=False
        ) as tmp:
            tmp.write(data)
            host_path = tmp.name

        try:
            if self.container:
                container_path = f"/var/lib/neo4j/import/{filename}"
                subprocess.check_call([
                    "docker", "cp",
                    host_path,
                    f"{self.container}:{container_path}",
                ])
                # docker cp preserves host uid/mode, which are unreadable to
                # the container's neo4j user. Make it world-readable so n10s
                # can open it.
                subprocess.check_call([
                    "docker", "exec", self.container,
                    "chmod", "644", container_path,
                ])
                fetch_url = f"file://{container_path}"
            else:
                fetch_url = f"file://{host_path}"
            query = (
                f'call n10s.rdf.import.fetch("{fetch_url}", "{n10s_format}");'
            )
            return self.execute(query)
        finally:
            try:
                os.unlink(host_path)
            except OSError:
                pass
