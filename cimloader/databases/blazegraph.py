import logging

from cimgraph.databases import get_cim_profile, get_iec61970_301, get_namespace, get_url
from cimloader.databases import ConnectionInterface, QueryResponse
from SPARQLWrapper import JSON, POST, SPARQLWrapper

_log = logging.getLogger(__name__)

class BlazegraphConnection(ConnectionInterface):
    def __init__(self) -> None:
        # clear cached env variables
        get_url.cache_clear()
        get_namespace.cache_clear()
        get_cim_profile.cache_clear()
        get_iec61970_301.cache_clear()

        # retrieve env variables
        self.sparql_obj = None
        self.url = get_url()
        self.namespace = get_namespace()
        self.iec61970_301 = get_iec61970_301()
        self.cim_profile, self.cim = get_cim_profile()

    def connect(self):
        if not self.sparql_obj:
            self.sparql_obj = SPARQLWrapper(self.url)
            self.sparql_obj.setReturnFormat(JSON)

    def configure(self):
        pass

    def drop_all(self):
        self.update('drop all')

    def disconnect(self):
        self.sparql_obj = None
        
    def execute(self, query_message: str) -> QueryResponse:
        self.connect()
        self.sparql_obj.setQuery(query_message)
        self.sparql_obj.setMethod(POST)
        query_output = self.sparql_obj.query().convert()
        return query_output
    
    def update(self, query_message:str) -> QueryResponse:
        self.connect()
        self.sparql_obj.setQuery(query_message)
        self.sparql_obj.setMethod(POST)
        query_output = self.sparql_obj.query()
        return query_output
