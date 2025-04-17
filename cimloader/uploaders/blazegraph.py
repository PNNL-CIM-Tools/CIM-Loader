import logging
import subprocess

from cimgraph.databases import get_cim_profile, get_iec61970_301, get_namespace, get_url
from cimloader.databases import BlazegraphConnection
from SPARQLWrapper import JSON, POST, SPARQLWrapper

_log = logging.getLogger(__name__)

class BlazegraphUploader(BlazegraphConnection):
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



    def upload_from_xml(self, filename:str) -> None:
        subprocess.call(["curl", "-s", "-D-", "-H", "Content-Type: application/xml", "--upload-file", f"{filename}", "-X", "Post", self.url])
        
    def upload_from_url(self):
        raise NotImplemented()

    def upload_from_graphmodel(self, graph):
        raise NotImplemented()
