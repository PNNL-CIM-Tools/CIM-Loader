from cimloader.databases import ConnectionInterface, ConnectionParameters

import io
import zipfile
import os
import requests
import logging

_log = logging.getLogger(__name__)

class NAERM(ConnectionInterface):
    def __init__(self, connection_parameters:ConnectionParameters):
        self.connection_parameters = connection_parameters
        self.url = connection_parameters.url

    def connect(self):
        pass

    def disconnect(self):
        pass

    def download_case(self, case_uuid, destination):
        casefile_url = self.url + "/uuid/" + case_uuid
        case_info = requests.get(casefile_url).json()
        file_url = case_info["file_url"]
        file_path = f"{destination}/{case_uuid}"

        r = requests.get(file_url)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall(file_path)
        


    def download_all_dss(self, destination, limit:int = 10000):
        counter = 0
        case_list = requests.get(self.url).json()
        case_uuid_list = []
        case_uuid_names = {}
        for case in case_list:
            if "simulator_type" in case["case"]:
                if case["case"]["simulator_type"] == "opendss":
                    counter = counter+1
                    case_uuid_list.append(case["bes_case_uuid"])
                    case_uuid_names[case["bes_case_uuid"]] = case["case"]["feeder_name"]

            if counter == limit:
                break

        counter = 0
        for case_uuid in case_uuid_list:
            counter = counter+1
            casefile_url = self.url + "/uuid/" + case_uuid
            case_info = requests.get(casefile_url).json()
            file_url = case_info["file_url"]
            file_path = f"{destination}/{case_uuid}"

            r = requests.get(file_url)
            z = zipfile.ZipFile(io.BytesIO(r.content))
            z.extractall(file_path)

        print(f"Successfully downloaded {counter} case files")

        return case_uuid_list, case_uuid_names
    

    
