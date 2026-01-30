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



    def upload_from_xml(self, filename:str) -> None:
        """Upload CIM XML file to Blazegraph using curl."""
        subprocess.call(["curl", "-s", "-D-", "-H", "Content-Type: application/xml", "--upload-file", f"{filename}", "-X", "Post", self.url])

    def upload_from_url(self):
        """Upload from URL - not yet implemented."""
        raise NotImplementedError("upload_from_url not yet implemented for Blazegraph")

    def upload_from_graphmodel(self, graph):
        """Upload from GraphModel - not yet implemented."""
        raise NotImplementedError("upload_from_graphmodel not yet implemented for Blazegraph")
