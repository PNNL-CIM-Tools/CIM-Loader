"""Blazegraph downloader - not yet implemented.

Download functionality for Blazegraph is planned but not currently available.
Use BlazegraphConnection.execute() to run SPARQL queries directly.
"""

import logging

_log = logging.getLogger(__name__)


class BlazegraphDownloader:
    """Blazegraph downloader stub.

    This class is not yet implemented. For querying Blazegraph:
    1. Use BlazegraphConnection from cimloader.databases
    2. Call connection.execute(sparql_query) to run SPARQL queries
    3. Process the returned query results as needed

    A dedicated downloader may be implemented in the future for
    batch export and conversion workflows.
    """

    def __init__(self):
        raise NotImplementedError(
            "BlazegraphDownloader is not yet implemented. "
            "Use BlazegraphConnection.execute() for SPARQL queries."
        )
