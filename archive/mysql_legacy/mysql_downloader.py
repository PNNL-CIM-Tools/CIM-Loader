"""MySQL downloader - not yet implemented.

MySQL query functionality exists in the MySQLConnection class.
This separate downloader class is not currently needed.
"""

import logging

_log = logging.getLogger(__name__)


class MySQLDownloader:
    """MySQL downloader stub.

    MySQL query functionality is available through MySQLConnection.execute().
    This separate downloader class may be implemented in the future for
    batch export workflows, but is not currently necessary.

    To query MySQL:
    1. Use MySQLConnection from cimloader.databases
    2. Call connection.execute(sql_query) to run SQL queries
    3. Process the returned result set
    """

    def __init__(self):
        raise NotImplementedError(
            "MySQLDownloader is not yet implemented. "
            "Use MySQLConnection.execute() for SQL queries."
        )
