"""MySQL uploader - not yet implemented.

MySQL upload functionality exists in the MySQLConnection class.
This separate uploader class is not currently needed.
"""

import logging

_log = logging.getLogger(__name__)


class MySQLUploader:
    """MySQL uploader stub.

    MySQL upload functionality is available through MySQLConnection.upload_from_cimgraph().
    This separate uploader class may be implemented in the future for consistency
    with the Blazegraph/Neo4j pattern, but is not currently necessary.

    To upload to MySQL:
    1. Use MySQLConnection from cimloader.databases
    2. Call connection.configure() to create schema
    3. Call connection.upload_from_cimgraph(network) to upload data
    """

    def __init__(self):
        raise NotImplementedError(
            "MySQLUploader is not yet implemented. "
            "Use MySQLConnection.upload_from_cimgraph() instead."
        )
