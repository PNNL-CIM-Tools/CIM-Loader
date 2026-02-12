from cimloader.web_apis.naerm_api import NAERM
from cimloader.databases.neo4j import Neo4jConnection
from cimloader.converters.dss_to_cim import DSStoCIM
from cimloader.databases import ConnectionInterface, Parameter, QueryResponse

import os
import logging
import subprocess


_log = logging.getLogger(__name__)

class NAERMtoNeo4j():
    def __init__(self, naerm_url: str, tmp_dir: str, docker_container: str):
        self.NaermDownloader = NAERM(naerm_url)
        # self.Neo4jConnection= Neo4jConnection()
        self.dss_converter = DSStoCIM()
        self.tmp_dir = tmp_dir
        self.docker_container = docker_container

    def upload_all_dss(self, limit):
        # self.Neo4jConnection.connect()
        case_uuid_list, case_uuid_names = self.NaermDownloader.download_all_dss(destination=self.tmp_dir, limit=limit)
        for case_uuid in case_uuid_list:
            self.dss_converter.convert_file(file_path=f"{self.tmp_dir}/{case_uuid}", feeder_mrid=case_uuid, 
                                            sub_name=case_uuid_names[case_uuid], sub_geo="SFO", geo="CA", uuids_file=f"{self.tmp_dir}/sfo_uuid.dat")
            if self.docker_container is not None:
                subprocess.call(["docker", "cp", f"{self.tmp_dir}/{case_uuid}/Master.xml", f"{self.docker_container}:import/{case_uuid}/Master.xml"])
                self.Neo4jConnection.upload(filepath=f"/import/{case_uuid}", filename="Master.xml", format="RDF/XML")
                _log.info(f"Successfully uploaded feeder id {case_uuid}")
        # self.Neo4jConnection.disconnect()

    def upload_case(self, case_uuid):
        # self.Neo4jConnection.connect()
        self.NaermDownloader.download_case(case_uuid=case_uuid, destination=self.tmp_dir)

        self.dss_converter.convert_file(file_path=f"{self.tmp_dir}/{case_uuid}", feeder_mrid=case_uuid, sub_geo="SFO", geo="CA", uuids_file=f"{self.tmp_dir}/sfo_uuid.dat")
        if self.docker_container is not None:
            subprocess.call(["docker", "cp", f"{self.tmp_dir}/{case_uuid}/Master.xml", f"{self.docker_container}:import/{case_uuid}/Master.xml"])
            self.Neo4jConnection.upload(filepath=f"/import/{case_uuid}", filename="Master.xml", format="RDF/XML")
            _log.info(f"Successfully uploaded feeder id {case_uuid}")
        # self.Neo4jConnection.disconnect()





def _main():
    import os

    # Configure Neo4j via environment variables
    os.environ['CIMG_URL'] = 'neo4j://localhost:7687'
    os.environ['CIMG_DATABASE'] = 'neo4j'
    os.environ['CIMG_USERNAME'] = 'neo4j'
    os.environ['CIMG_PASSWORD'] = 'neo4j'
    os.environ['CIMG_CIM_PROFILE'] = 'cimhub_2023'
    os.environ['CIMG_NAMESPACE'] = 'http://iec.ch/TC57/CIM100#'

    naerm_url = "https://api.develop.naerm.team/data/bes/case_files"

    tmp_dir = "/home/ande188/naerm"

    sfo_uuid = """
    Station=Station=1 {ad4e7f6e-b4eb-44cb-a75e-ac7f3e2e41c5}
    GeoRgn=GeoRgn=1 {731690f4-13e0-4555-8084-3cc05d1000f8}
    SubGeoRgn=SubGeoRgn=1 {277ebb75-f974-4de6-8a85-8526d0aa3351}"""

    with open(f"{tmp_dir}/sfo_uuid.dat", "w") as fp:
        fp.write(sfo_uuid)

    docker_container = "gridappsd-docker-neo4j-apoc_1"

    nn4j = NAERMtoNeo4j(naerm_url=naerm_url, tmp_dir=tmp_dir, docker_container=docker_container)

    nn4j.upload_all_dss(limit=10)

    # case_uuid = "accdf54c-c90c-4c41-9d7a-5e5d3d17a4e5"
    case_uuid = "1b5adb54-dcc3-472b-a5fd-aaab635857e1"
    nn4j.upload_case(case_uuid=case_uuid)




if __name__ == "__main__":
     _main()