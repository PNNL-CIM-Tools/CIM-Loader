import logging
import subprocess

from cimloader.databases import ConnectionInterface, QueryResponse
from cimloader.databases.neo4j import Neo4jConnection
from SPARQLWrapper import JSON, POST, SPARQLWrapper

_log = logging.getLogger(__name__)

class Neo4jUploader(ConnectionInterface):
    def __init__(self, connection_params: ConnectionInterface) -> None:
        self.url = connection_params.url
        self.connection_params = connection_params
        self.container = connection_params.container
        self.connection = Neo4jConnection(connection_params)
        self.connection.connect()


    def upload_from_file(self, filename, filepath):
        if '.xml' in filename or '.XML' in filename:
            format = 'RDF/XML'
        elif '.ttl' in filename:
            #TODO
            pass

        if self.container:
            subprocess.call(["docker", "cp", f"{filepath}/{filename}", f"{self.container}:/var/lib/neo4j/import/{filename}"])
            records=self.connection.execute(f"""call n10s.rdf.import.fetch( "file:///var/lib/neo4j/import//{filename}", "{format}"); """) 
        else:
            records=self.connection.execute(f"""call n10s.rdf.import.fetch( "file://{filepath}/{filename}", "{format}"); """) 
        return records

    def upload_from_url(self, url):
        if '.xml' in url or '.XML' in url:
            format = 'RDF/XML'
        elif '.ttl' in url:
            pass
        records=self.connection.execute(f'''call n10s.rdf.import.fetch("{url}", "{format}"); ''') 
        return records

    def upload_from_rdflib(self, rdflib_graph):

        pass

    def upload_from_cimgraph(self):
        pass

    def upload_from_rdflib(self, rdflib_graph):

        pass
