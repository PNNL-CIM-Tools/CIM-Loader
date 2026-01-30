import logging
import subprocess

from cimgraph.databases import get_cim_profile, get_database, get_iec61970_301, get_namespace, get_password, get_url, get_username
from cimloader.databases import ConnectionInterface, QueryResponse
from cimloader.databases._config_utils import clear_cim_config_cache
from cimloader.databases.neo4j import Neo4jConnection

_log = logging.getLogger(__name__)

class Neo4jUploader(Neo4jConnection):
    def __init__(self, container:str = None) -> None:
        # Clear cached env variables to pick up any configuration changes
        clear_cim_config_cache()

        # Retrieve configuration from environment
        self.cim_profile, self.cim = get_cim_profile()
        self.namespace = get_namespace()
        self.url = get_url()
        self.username = get_username()
        self.password = get_password()
        self.database = get_database()
        self.iec61970_301 = get_iec61970_301()
        self.container = container
        self.driver = None
        self.connect()


    def upload_from_file(self, filename, filepath):
        if '.xml' in filename or '.XML' in filename:
            format = 'RDF/XML'
        elif '.ttl' in filename:
            #TODO
            pass

        if self.container:
            subprocess.call(["docker", "cp", f"{filepath}/{filename}", f"{self.container}:/var/lib/neo4j/import/{filename}"])
            records=self.execute(f"""call n10s.rdf.import.fetch( "file:///var/lib/neo4j/import//{filename}", "{format}"); """) 
        else:
            records=self.execute(f"""call n10s.rdf.import.fetch( "file://{filepath}/{filename}", "{format}"); """) 
        return records

    def upload_from_url(self, url):
        if '.xml' in url or '.XML' in url:
            format = 'RDF/XML'
        elif '.ttl' in url:
            pass
        records=self.execute(f'''call n10s.rdf.import.fetch("{url}", "{format}"); ''') 
        return records

    def upload_from_rdflib(self, rdflib_graph):

        pass

    def upload_from_cimgraph(self):
        pass

    def upload_from_rdflib(self, rdflib_graph):

        pass
