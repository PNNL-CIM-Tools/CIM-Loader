from __future__ import annotations
import logging

from neo4j import GraphDatabase
from neo4j.exceptions import DriverError, Neo4jError

from cimloader.databases import ConnectionInterface, QueryResponse
from cimloader.databases._config_utils import clear_cim_config_cache
from cimgraph.databases import get_cim_profile, get_database, get_iec61970_552, get_namespace, get_password, get_url, get_username

_log = logging.getLogger(__name__)

class Neo4jConnection(ConnectionInterface):
    def __init__(self):
        # Clear cached env variables to pick up any configuration changes
        clear_cim_config_cache()

        # Retrieve configuration from environment
        self.cim_profile, self.cim = get_cim_profile()
        self.namespace = get_namespace()
        self.url = get_url()
        self.username = get_username()
        self.password = get_password()
        self.database = get_database()
        self.iec61970_552 = get_iec61970_552()
        self.driver = None


    def connect(self):
        if not self.driver:
            self.driver = GraphDatabase.driver(self.url, auth=(self.username, self.password))
            self.driver.verify_connectivity()

    def disconnect(self):
        self.driver.close()
        self.driver = None

    def execute(self, query_message: str) -> QueryResponse:
        self.connect()

        try:
            records, summary, keys = self.driver.execute_query(query_message, database_=self.database )
            return records, summary, keys
        # Log the failing query for traceability, then re-raise: returning None
        # here would surface as a confusing TypeError when the caller unpacks
        # the three return values, hiding the real Neo4j error.
        except (DriverError, Neo4jError):
            _log.error("Query failed: %s", query_message)
            raise

    def configure(self):
        if self.cim_profile is not None and self.namespace is not None:
            # self.execute("CALL n10s.nsprefixes.add(\""+self.cim_profile+"\",\""+self.namespace+"\");")
            # IF NOT EXISTS keeps configure() idempotent now that execute()
            # re-raises instead of swallowing the "already exists" error.
            self.execute(
                "CREATE CONSTRAINT n10s_unique_uri IF NOT EXISTS "
                "FOR (r:Resource) REQUIRE r.uri IS UNIQUE;"
            )

        else:
            raise RuntimeError(
                "CIM profile and namespace must be defined in environment variables "
                "(CIMG_CIM_PROFILE, CIMG_NAMESPACE)"
            )

        graph_config = """call n10s.graphconfig.init({
            handleMultival: "OVERWRITE", 
            handleVocabUris: "IGNORE",
            keepCustomDataTypes: true,
            handleRDFTypes: "LABELS"})"""
        self.execute(graph_config)

    

    def drop_all(self):
        self.execute("MATCH (n) DETACH DELETE n")
        # IF EXISTS: the constraint is absent on a database that was never
        # configure()d, and its absence is not an error.
        self.execute("DROP CONSTRAINT n10s_unique_uri IF EXISTS")
