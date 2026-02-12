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


    def upload_from_file(self, filepath: str, filename: str):
        """Upload RDF file from filesystem to Neo4j.

        Automatically detects format based on file extension.

        Args:
            filepath: Directory containing the file
            filename: Name of the file to upload

        Returns:
            Neo4j query result records

        Raises:
            ValueError: If file extension is not recognized
        """
        format = self._get_n10s_format(filename)
        return self._upload(filepath, filename, format)

    def upload_from_xml(self, filepath: str, filename: str):
        """Upload RDF/XML file to Neo4j.

        Args:
            filepath: Directory containing the file
            filename: Name of the XML file to upload

        Returns:
            Neo4j query result records
        """
        return self._upload(filepath, filename, 'RDF/XML')

    def upload_from_ttl(self, filepath: str, filename: str):
        """Upload Turtle (TTL) file to Neo4j.

        Args:
            filepath: Directory containing the file
            filename: Name of the TTL file to upload

        Returns:
            Neo4j query result records
        """
        return self._upload(filepath, filename, 'Turtle')

    def upload_from_ntriples(self, filepath: str, filename: str):
        """Upload N-Triples file to Neo4j.

        Args:
            filepath: Directory containing the file
            filename: Name of the N-Triples file to upload

        Returns:
            Neo4j query result records
        """
        return self._upload(filepath, filename, 'N-Triples')

    def upload_from_jsonld(self, filepath: str, filename: str):
        """Upload JSON-LD file to Neo4j.

        Args:
            filepath: Directory containing the file
            filename: Name of the JSON-LD file to upload

        Returns:
            Neo4j query result records
        """
        return self._upload(filepath, filename, 'JSON-LD')

    def upload_from_url(self, url):
        if '.xml' in url or '.XML' in url:
            format = 'RDF/XML'
        elif '.ttl' in url:
            pass
        records=self.execute(f'''call n10s.rdf.import.fetch("{url}", "{format}"); ''') 
        return records

    def upload_from_rdflib(self, rdflib_graph):
        """Upload from RDFLib graph - not yet implemented."""
        raise NotImplementedError("upload_from_rdflib not yet implemented for Neo4j")

    def upload_from_cimgraph(self):
        """Upload from CIMantic Graphs GraphModel - not yet implemented."""
        raise NotImplementedError("upload_from_cimgraph not yet implemented for Neo4j")

    def _upload(self, filepath: str, filename: str, format: str):
        """Internal method to upload file with specific n10s format.

        Args:
            filepath: Directory containing the file
            filename: Name of the file to upload
            format: n10s format string (e.g., 'RDF/XML', 'Turtle', 'N-Triples', 'JSON-LD')

        Returns:
            Neo4j query result records
        """
        if self.container:
            subprocess.call(["docker", "cp", f"{filepath}/{filename}", f"{self.container}:/var/lib/neo4j/import/{filename}"])
            records = self.execute(f"""call n10s.rdf.import.fetch("file:///var/lib/neo4j/import/{filename}", "{format}");""")
        else:
            records = self.execute(f"""call n10s.rdf.import.fetch("file://{filepath}/{filename}", "{format}");""")
        return records

    def _get_n10s_format(self, filename: str) -> str:
        """Determine n10s format string from file extension.

        Args:
            filename: Name of the file

        Returns:
            n10s format string

        Raises:
            ValueError: If file extension is not recognized
        """
        filename_lower = filename.lower()

        if filename_lower.endswith('.xml') or filename_lower.endswith('.rdf'):
            return 'RDF/XML'
        elif filename_lower.endswith('.ttl') or filename_lower.endswith('.turtle'):
            return 'Turtle'
        elif filename_lower.endswith('.nt') or filename_lower.endswith('.ntriples'):
            return 'N-Triples'
        elif filename_lower.endswith('.jsonld') or filename_lower.endswith('.json-ld'):
            return 'JSON-LD'
        elif filename_lower.endswith('.nq') or filename_lower.endswith('.nquads'):
            return 'N-Quads'
        elif filename_lower.endswith('.trig'):
            return 'TriG'
        else:
            raise ValueError(
                f"Unsupported file format: {filename}. "
                "Supported formats: .xml, .rdf, .ttl, .turtle, .nt, .ntriples, .jsonld, .nq, .nquads, .trig"
            )
