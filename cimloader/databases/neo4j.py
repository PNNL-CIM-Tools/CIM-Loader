from __future__ import annotations
import logging


from neo4j import GraphDatabase
from neo4j.exceptions import DriverError, Neo4jError

from cimloader.databases import ConnectionInterface, QueryResponse
from cimgraph.databases import get_cim_profile, get_database, get_iec61970_301, get_namespace, get_password, get_url, get_username



_log = logging.getLogger(__name__)

class Neo4jConnection(ConnectionInterface):
    def __init__(self):

        # clear cached env variables
        get_url.cache_clear()
        get_namespace.cache_clear()
        get_cim_profile.cache_clear()
        get_iec61970_301.cache_clear()
        get_username.cache_clear()
        get_password.cache_clear()

        # retrieve env variables
        self.cim_profile, self.cim = get_cim_profile()
        self.namespace = get_namespace()
        self.url = get_url()
        self.username = get_username()
        self.password = get_password()
        self.database = get_database()
        self.iec61970_301 = get_iec61970_301()
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
        # Capture any errors along with the query and data for traceability
        except (DriverError, Neo4jError) as exception:
            _log.error("%s raised an error: \n%s", query_message, exception)

    def configure(self):
        if self.cim_profile is not None and self.namespace is not None:
            # self.execute("CALL n10s.nsprefixes.add(\""+self.cim_profile+"\",\""+self.namespace+"\");")
            self.execute("CREATE CONSTRAINT n10s_unique_uri FOR (r:Resource) REQUIRE r.uri IS UNIQUE;")

        else:
            _log.exception("CIM profile and namespace must be defined in ConnectionParameters")

        graph_config = """call n10s.graphconfig.init({
            handleMultival: "OVERWRITE", 
            handleVocabUris: "IGNORE",
            keepCustomDataTypes: true,
            handleRDFTypes: "LABELS"})"""
        self.execute(graph_config)

    

    def drop_all(self):
        self.execute("MATCH (n) DETACH DELETE n")
        self.execute("DROP CONSTRAINT n10s_unique_uri")
