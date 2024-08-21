import logging
import subprocess

from cimloader.databases import ConnectionInterface, QueryResponse
from cimloader.databases.blazegraph import BlazegraphConnection
from SPARQLWrapper import JSON, POST, SPARQLWrapper

_log = logging.getLogger(__name__)

class BlazegraphUploader(ConnectionInterface):
    def __init__(self, connection_params: ConnectionInterface) -> None:
        self.url = connection_params.url
        self.connection_params = connection_params
        self.connection = BlazegraphConnection(connection_params)
        self.connection.connect()

    def upload_from_file(self, filepath:str, filename:str) -> None:
        subprocess.call(["curl", "-s", "-D-", "-H", "Content-Type: application/xml", "--upload-file", f"{filepath}/{filename}", "-X", "Post", self.url])
        
    def upload_from_url(self):
        pass

    def upload_from_rdflib(self, rdflib_graph):

        pass
