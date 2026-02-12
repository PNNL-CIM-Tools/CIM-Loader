"""Oxigraph database connection.

Oxigraph is a lightweight RDF graph database with SPARQL 1.1 support.
It provides a REST API for data upload and SPARQL query execution.
"""

import logging

from cimgraph.databases import get_cim_profile, get_iec61970_301, get_namespace, get_url
from cimloader.databases import ConnectionInterface, QueryResponse
from cimloader.databases._config_utils import clear_cim_config_cache
from SPARQLWrapper import JSON, POST, SPARQLWrapper

_log = logging.getLogger(__name__)


class OxigraphConnection(ConnectionInterface):
    """Connection to Oxigraph RDF triplestore.

    Oxigraph is a fast, standards-compliant graph database that supports:
    - RDF/XML, Turtle, N-Triples, N-Quads file formats
    - SPARQL 1.1 queries and updates
    - HTTP REST API for data operations

    The connection uses environment variables from cimgraph for configuration.
    """

    def __init__(self) -> None:
        # Clear cached env variables to pick up any configuration changes
        clear_cim_config_cache()

        # Retrieve configuration from environment
        self.sparql_obj = None
        self.url = get_url()  # Expected format: http://localhost:7878/query
        self.namespace = get_namespace()
        self.iec61970_301 = get_iec61970_301()
        self.cim_profile, self.cim = get_cim_profile()

    def connect(self):
        """Establish SPARQL connection to Oxigraph.

        Creates a SPARQLWrapper instance configured for JSON responses.
        Connection is lazy - only created when needed.
        """
        if not self.sparql_obj:
            self.sparql_obj = SPARQLWrapper(self.url)
            self.sparql_obj.setReturnFormat(JSON)

    def configure(self):
        """Configure Oxigraph database.

        Oxigraph is schemaless and doesn't require pre-configuration.
        This method is provided for interface compatibility.
        """
        pass

    def drop_all(self):
        """Delete all triples from the Oxigraph store.

        Uses SPARQL UPDATE to clear all data. Use with caution.
        """
        self.update('CLEAR ALL')

    def disconnect(self):
        """Close connection to Oxigraph.

        Releases the SPARQLWrapper instance.
        """
        self.sparql_obj = None

    def execute(self, query_message: str) -> QueryResponse:
        """Execute a SPARQL query against Oxigraph.

        Args:
            query_message: SPARQL SELECT or CONSTRUCT query

        Returns:
            Query results in JSON format
        """
        self.connect()
        self.sparql_obj.setQuery(query_message)
        self.sparql_obj.setMethod(POST)
        query_output = self.sparql_obj.query().convert()
        return query_output

    def update(self, query_message: str) -> QueryResponse:
        """Execute a SPARQL UPDATE against Oxigraph.

        Args:
            query_message: SPARQL UPDATE query (INSERT, DELETE, etc.)

        Returns:
            Update response
        """
        self.connect()
        self.sparql_obj.setQuery(query_message)
        self.sparql_obj.setMethod(POST)
        query_output = self.sparql_obj.query()
        return query_output
