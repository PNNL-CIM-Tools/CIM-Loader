from __future__ import annotations

import logging
import subprocess

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
    def __init__(self, container: str | None = None) -> None:
        super().__init__()
        self.container = container
        self.connect()

    def upload_from_file(self, filepath: str, filename: str):
        """Upload an RDF file to Neo4j via the n10s plugin.

        Format is auto-detected from the file extension. If a `container`
        was given at construction time the file is `docker cp`'d into the
        Neo4j container first; otherwise the path must already be reachable
        from the Neo4j process.
        """
        content_type = content_type_from_filename(filename)
        n10s_format = _CONTENT_TYPE_TO_N10S[content_type]
        return self._upload(filepath, filename, n10s_format)

    def upload_from_url(self, url: str):
        """Fetch an RDF file from a URL and import it via the n10s plugin.

        Neo4j's n10s.rdf.import.fetch takes a URL natively, so no local
        download is needed. Format is auto-detected from the URL path
        extension.
        """
        content_type = content_type_from_url(url)
        n10s_format = _CONTENT_TYPE_TO_N10S[content_type]
        _log.info("Fetching %s for import into Neo4j", url)
        query = f'call n10s.rdf.import.fetch("{url}", "{n10s_format}");'
        return self.execute(query)

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

    def _upload(self, filepath: str, filename: str, n10s_format: str):
        if self.container:
            subprocess.call([
                "docker", "cp",
                f"{filepath}/{filename}",
                f"{self.container}:/var/lib/neo4j/import/{filename}",
            ])
            query = (
                f'call n10s.rdf.import.fetch("file:///var/lib/neo4j/import/{filename}", '
                f'"{n10s_format}");'
            )
        else:
            query = (
                f'call n10s.rdf.import.fetch("file://{filepath}/{filename}", '
                f'"{n10s_format}");'
            )
        return self.execute(query)
