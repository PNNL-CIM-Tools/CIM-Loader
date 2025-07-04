import logging
import subprocess

from cimgraph.databases import get_cim_profile, get_database, get_iec61970_301, get_namespace, get_password, get_url, get_username

from cimloader.databases import ConnectionInterface, QueryResponse
from cimloader.databases.neo4j import Neo4jConnection


_log = logging.getLogger(__name__)

class Neo4jUploader(Neo4jConnection):
    def __init__(self, containerized:bool = True) -> None:

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
        self.containerized = containerized
        self.driver = None
        self.connect()


    def upload_from_file(self, filename, filepath):
        if '.xml' in filename or '.XML' in filename:
            format = 'RDF/XML'
        elif '.ttl' in filename:
            #TODO
            pass

        if self.containerized:
            subprocess.call(["docker", "cp", f"{filepath}/{filename}", f"{self.containerized}:/var/lib/neo4j/import/{filename}"])
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
