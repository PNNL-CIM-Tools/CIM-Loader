"""GraphDB uploader - not yet implemented.

GraphDB support is planned but not currently available.
Use BlazegraphUploader or Neo4jUploader as alternatives.
"""

import logging

_log = logging.getLogger(__name__)


class GraphDBUploader:
    """GraphDB uploader stub.

    This class is not yet implemented. GraphDB is a supported database
    in the roadmap, but the uploader implementation is pending.

    For RDF/SPARQL database uploads, use:
    - BlazegraphUploader for Blazegraph triplestore
    - Neo4jUploader for Neo4j graph database with n10s plugin
    """

    def __init__(self):
        raise NotImplementedError(
            "GraphDBUploader is not yet implemented. "
            "Please use BlazegraphUploader or Neo4jUploader instead."
        )
