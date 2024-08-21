from __future__ import annotations
import logging
import subprocess

from typing import Dict, List, Optional


from neo4j import GraphDatabase
from neo4j.exceptions import DriverError, Neo4jError

from cimloader.databases import ConnectionInterface, ConnectionParameters, Parameter, QueryResponse

import rdflib
# from rdflib import Graph, Namespace
from rdflib.namespace import RDF

_log = logging.getLogger(__name__)

class Neo4jConnection(ConnectionInterface):
    def __init__(self, connection_parameters):
        self.connection_parameters = connection_parameters
        self.cim_profile = connection_parameters.cim_profile
        self.namespace = connection_parameters.namespace
        self.url = connection_parameters.url
        self.username = connection_parameters.username
        self.password = connection_parameters.password
        self.database = connection_parameters.database
        self.container = connection_parameters.container
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
