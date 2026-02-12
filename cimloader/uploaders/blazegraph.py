import logging
import subprocess

from cimgraph.databases import get_cim_profile, get_iec61970_301, get_namespace, get_url
from cimloader.databases import BlazegraphConnection
from cimloader.databases._config_utils import clear_cim_config_cache
from SPARQLWrapper import JSON, POST, SPARQLWrapper

_log = logging.getLogger(__name__)

class BlazegraphUploader(BlazegraphConnection):
    def __init__(self) -> None:
        # Clear cached env variables to pick up any configuration changes
        clear_cim_config_cache()

        # Retrieve configuration from environment
        self.sparql_obj = None
        self.url = get_url()
        self.namespace = get_namespace()
        self.iec61970_301 = get_iec61970_301()
        self.cim_profile, self.cim = get_cim_profile()



    def upload_from_file(self, filepath: str, filename: str) -> None:
        """Upload RDF file from filesystem to Blazegraph.

        Automatically detects format based on file extension.

        Args:
            filepath: Directory containing the file
            filename: Name of the file to upload

        Raises:
            ValueError: If file extension is not recognized
        """
        content_type = self._get_content_type(filename)
        self._upload(filepath, filename, content_type)

    def upload_from_xml(self, filepath: str, filename: str) -> None:
        """Upload RDF/XML file to Blazegraph.

        Args:
            filepath: Directory containing the file
            filename: Name of the XML file to upload
        """
        self._upload(filepath, filename, 'application/rdf+xml')

    def upload_from_ttl(self, filepath: str, filename: str) -> None:
        """Upload Turtle (TTL) file to Blazegraph.

        Args:
            filepath: Directory containing the file
            filename: Name of the TTL file to upload
        """
        self._upload(filepath, filename, 'text/turtle')

    def upload_from_ntriples(self, filepath: str, filename: str) -> None:
        """Upload N-Triples file to Blazegraph.

        Args:
            filepath: Directory containing the file
            filename: Name of the N-Triples file to upload
        """
        self._upload(filepath, filename, 'application/n-triples')

    def upload_from_jsonld(self, filepath: str, filename: str) -> None:
        """Upload JSON-LD file to Blazegraph.

        Args:
            filepath: Directory containing the file
            filename: Name of the JSON-LD file to upload
        """
        self._upload(filepath, filename, 'application/ld+json')

    def upload_from_url(self):
        """Upload from URL - not yet implemented."""
        raise NotImplementedError("upload_from_url not yet implemented for Blazegraph")

    def upload_from_graphmodel(self, graph):
        """Upload from GraphModel - not yet implemented."""
        raise NotImplementedError("upload_from_graphmodel not yet implemented for Blazegraph")

    def _upload(self, filepath: str, filename: str, content_type: str) -> None:
        """Internal method to upload file with specific content type.

        Args:
            filepath: Directory containing the file
            filename: Name of the file to upload
            content_type: MIME type for the RDF format
        """
        full_path = f"{filepath}/{filename}"
        subprocess.call([
            "curl", "-s", "-D-",
            "-H", f"Content-Type: {content_type}",
            "--upload-file", full_path,
            "-X", "POST",
            self.url
        ])

    def _get_content_type(self, filename: str) -> str:
        """Determine RDF content type from file extension.

        Args:
            filename: Name of the file

        Returns:
            MIME type string for the RDF format

        Raises:
            ValueError: If file extension is not recognized
        """
        filename_lower = filename.lower()

        if filename_lower.endswith('.xml') or filename_lower.endswith('.rdf'):
            return 'application/rdf+xml'
        elif filename_lower.endswith('.ttl') or filename_lower.endswith('.turtle'):
            return 'text/turtle'
        elif filename_lower.endswith('.nt') or filename_lower.endswith('.ntriples'):
            return 'application/n-triples'
        elif filename_lower.endswith('.nq') or filename_lower.endswith('.nquads'):
            return 'application/n-quads'
        elif filename_lower.endswith('.jsonld') or filename_lower.endswith('.json-ld'):
            return 'application/ld+json'
        elif filename_lower.endswith('.trig'):
            return 'application/trig'
        else:
            raise ValueError(
                f"Unsupported file format: {filename}. "
                "Supported formats: .xml, .rdf, .ttl, .turtle, .nt, .ntriples, .nq, .nquads, .jsonld, .trig"
            )
