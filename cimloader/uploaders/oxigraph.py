"""Oxigraph uploader for CIM data.

Provides methods to upload CIM XML/RDF files to an Oxigraph triplestore
running in a Docker container or standalone.
"""

import logging
import subprocess

from cimgraph.databases import get_cim_profile, get_iec61970_301, get_namespace, get_url
from cimloader.databases import OxigraphConnection
from cimloader.databases._config_utils import clear_cim_config_cache

_log = logging.getLogger(__name__)


class OxigraphUploader(OxigraphConnection):
    """Upload CIM data to Oxigraph triplestore.

    Oxigraph accepts RDF data via HTTP POST to its /store endpoint.
    Supports multiple RDF formats:
    - RDF/XML (application/rdf+xml)
    - Turtle (text/turtle)
    - N-Triples (application/n-triples)
    - N-Quads (application/n-quads)

    The uploader automatically detects format based on file extension.
    """

    def __init__(self, container: str = None) -> None:
        # Clear cached env variables to pick up any configuration changes
        clear_cim_config_cache()

        # Retrieve configuration from environment
        self.url = get_url()  # Base URL like http://localhost:7878
        self.namespace = get_namespace()
        self.iec61970_301 = get_iec61970_301()
        self.cim_profile, self.cim = get_cim_profile()
        self.container = container

        # Remove /query suffix if present, we need base URL for uploads
        if self.url.endswith('/query'):
            self.base_url = self.url.rsplit('/query', 1)[0]
        else:
            self.base_url = self.url

        # Oxigraph upload endpoint
        self.upload_endpoint = f"{self.base_url}/store"

    def upload_from_file(self, filepath: str, filename: str) -> None:
        """Upload RDF file to Oxigraph from filesystem.

        Automatically detects format based on file extension.

        Args:
            filepath: Directory containing the file
            filename: Name of the file to upload

        Raises:
            RuntimeError: If upload fails or file format is unsupported

        Example:
            uploader = OxigraphUploader()
            uploader.upload_from_file('./models', 'ieee13.xml')
        """
        content_type = self._get_content_type(filename)
        self._upload_with_format(filepath, filename, content_type)

    def upload_from_xml(self, filepath: str, filename: str) -> None:
        """Upload RDF/XML file to Oxigraph.

        Args:
            filepath: Directory containing the file
            filename: Name of the XML file to upload
        """
        self._upload_with_format(filepath, filename, 'application/rdf+xml')

    def upload_from_ttl(self, filepath: str, filename: str) -> None:
        """Upload Turtle (TTL) file to Oxigraph.

        Args:
            filepath: Directory containing the file
            filename: Name of the TTL file to upload
        """
        self._upload_with_format(filepath, filename, 'text/turtle')

    def upload_from_ntriples(self, filepath: str, filename: str) -> None:
        """Upload N-Triples file to Oxigraph.

        Args:
            filepath: Directory containing the file
            filename: Name of the N-Triples file to upload
        """
        self._upload_with_format(filepath, filename, 'application/n-triples')

    def upload_from_nquads(self, filepath: str, filename: str) -> None:
        """Upload N-Quads file to Oxigraph.

        Args:
            filepath: Directory containing the file
            filename: Name of the N-Quads file to upload
        """
        self._upload_with_format(filepath, filename, 'application/n-quads')

    def upload_from_url(self, url: str) -> None:
        """Upload CIM data from a URL to Oxigraph.

        Args:
            url: HTTP(S) URL pointing to RDF data

        Raises:
            NotImplementedError: This method is not yet implemented
        """
        raise NotImplementedError("upload_from_url not yet implemented for Oxigraph")

    def upload_from_graphmodel(self, graph):
        """Upload from CIMantic Graphs GraphModel.

        Args:
            graph: cimgraph.models.GraphModel instance

        Raises:
            NotImplementedError: This method is not yet implemented
        """
        raise NotImplementedError("upload_from_graphmodel not yet implemented for Oxigraph")

    def _upload_with_format(self, filepath: str, filename: str, content_type: str) -> None:
        """Internal method to upload file with specific content type.

        Args:
            filepath: Directory containing the file
            filename: Name of the file to upload
            content_type: MIME type for the RDF format

        Raises:
            RuntimeError: If upload fails
        """
        full_path = f"{filepath}/{filename}"

        if self.container:
            # If using Docker container, copy file into container first
            container_path = f"/tmp/{filename}"
            _log.info(f"Copying {full_path} to container {self.container}:{container_path}")
            subprocess.check_call([
                "docker", "cp",
                full_path,
                f"{self.container}:{container_path}"
            ])

            # Execute curl from within the container
            _log.info(f"Uploading {filename} to Oxigraph in container")
            subprocess.check_call([
                "docker", "exec", self.container,
                "curl", "-X", "POST",
                "-H", f"Content-Type: {content_type}",
                "--data-binary", f"@{container_path}",
                self.upload_endpoint
            ])

            # Clean up temp file in container
            subprocess.call([
                "docker", "exec", self.container,
                "rm", container_path
            ])
        else:
            # Direct upload from host filesystem
            _log.info(f"Uploading {filename} to Oxigraph at {self.upload_endpoint}")
            subprocess.check_call([
                "curl", "-X", "POST",
                "-H", f"Content-Type: {content_type}",
                "--data-binary", f"@{full_path}",
                self.upload_endpoint
            ])

        _log.info(f"Successfully uploaded {filename} to Oxigraph")

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
        else:
            raise ValueError(
                f"Unsupported file format: {filename}. "
                "Supported formats: .xml, .rdf, .ttl, .turtle, .nt, .ntriples, .nq, .nquads"
            )
