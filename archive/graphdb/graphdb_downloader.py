"""GraphDB downloader - not yet implemented.

GraphDB support is planned but not currently available.
"""

import logging

_log = logging.getLogger(__name__)


class GraphDBDownloader:
    """GraphDB downloader stub.

    This class is not yet implemented. GraphDB is a supported database
    in the roadmap, but the downloader implementation is pending.

    For RDF/SPARQL database queries, use:
    - BlazegraphConnection for Blazegraph triplestore queries
    - Neo4jConnection for Neo4j Cypher queries
    """

    def __init__(self):
        raise NotImplementedError(
            "GraphDBDownloader is not yet implemented. "
            "GraphDB support is planned for future release."
        )
