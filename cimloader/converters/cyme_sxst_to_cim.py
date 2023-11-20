"""
This script provides a wrapper around the Cyme2DSS converter in CIMHub.
It ingests a single sxst file generated from Cyme, produces the json
config file required from Cyme2DSS and calls Cyme2DSS to do the conversion.
It produces a folder in the same directory as the sxst file where the
DSS files are stored.
"""

import xmltodict
import os
import math
import shutil
import json
import sys


from converters import Cyme2DSS
from cimloader.converters import dss_to_cim

class SXSTToCIM:
    def __init__(self, input_file):
        self.input_file = input_file
        self.out_dir = None
        self.file_name = None
        self.cyme_json = {}
        self.sxst_dict = {}
        self.main_method()

    def main_method(self):
        self.sxst_dict = self.convert_sxst_to_dict(self.input_file)
        self.make_cyme_json()
        self.convert_sxst_to_dss()
        self.convert_dss_to_cim()

    def convert_sxst_to_dict(self, sxst_filename):
        with open(sxst_filename, 'r') as sxst_file:
            sxst_data = sxst_file.read()
            sxst_dict = xmltodict.parse(sxst_data)
        return sxst_dict

    def search_sxst_by_key(self, search_keys, search_data, search_outcome):
        for i in range(len(search_keys)):
            if search_keys[i] in list(search_data.keys()):
                search_outcome[i].append(search_data[search_keys[i]])
        for each in list(search_data.values()):
            if isinstance(each, dict):
                self.search_sxst_by_key(search_keys, each, search_outcome)
            if isinstance(each, list):
                for item in each:
                    if isinstance(item, dict):
                        self.search_sxst_by_key(search_keys, item, search_outcome)
        for i in range(len(search_outcome)):
            try:
                search_outcome[i] = list(set(search_outcome[i]))
            except TypeError:
                pass
        return search_outcome

    def make_cyme_json(self):
        # Get root file name for DSS master file
        self.file_name = self.input_file.split("/")[-1]
        self.file_name = self.file_name.split(".")[0]

        # Get default directory
        file_path_list = self.input_file.split("/")
        file_path_list.pop()
        default_dir = ""
        for each in file_path_list:
            default_dir = default_dir + each + "/"

        # Make output directory. If already exists, delete first
        self.out_dir = os.path.join(default_dir, f"{self.file_name}_dss")
        shutil.rmtree(self.out_dir, True)
        os.mkdir(self.out_dir)

        # Other model-specific parameters
        search_keys = ["OwnerID", "PrimaryVoltage", "Points", "LoadModelInformation"]
        [owner_ids, prim_voltages, points, load_model] = self.search_sxst_by_key(search_keys, self.sxst_dict,
                                                                             [[]] * len(search_keys))
        # Convert relevant parameters to floats
        xcoord = []
        ycoord = []
        # Primary voltages
        for i in range(len(prim_voltages)):
            prim_voltages[i] = float(prim_voltages[i])
        # X and Y coordinates
        for pt in points:
            point = pt["Point"]
            for point_dict in point:
                xcoord.append(float(point_dict["X"]))
                ycoord.append(float(point_dict["Y"]))
        # Load model
        lm = float(load_model[0]["ID"])

        # Default base voltage
        if 12.47 in prim_voltages:
            base_voltage = 12.47
        elif 13.2 in prim_voltages:
            base_voltage = 13.2
        elif 4.16 in prim_voltages:
            base_voltage = 4.16
        elif 7.2 in prim_voltages:
            base_voltage = 7.2
        else:
            base_voltage = float(min(prim_voltages))

        self.cyme_json = {
                      "DefaultDir": default_dir,
                      "OutDir": self.out_dir,
                      "xmlfilename": self.file_name,
                      "RootName": self.file_name,
                      "SubName": f"{self.file_name}_sub",
                      "LoadScale": 1.0,
                      "LoadModel": lm,
                      "DefaultBaseVoltage": base_voltage,
                      "BaseVoltages": prim_voltages,
                      "CoordXmin": math.floor(min(xcoord)),
                      "CoordXmax": math.ceil(max(xcoord)),
                      "CoordYmin": math.floor(min(ycoord)),
                      "CoordYmax": math.ceil(max(ycoord)),
                      "CYMESectionUnit": "m",
                      "CYMELineCodeUnit": "km",
                      "DSSSectionUnit": "m",
                      "OwnerIDs": owner_ids
                    }
        with open(f'{default_dir}/{self.file_name}_config.json', 'w') as fp:
            json.dump(self.cyme_json, fp)

    def convert_sxst_to_dss(self):
        Cyme2DSS.ConvertSXST(self.cyme_json)

    def convert_dss_to_cim(self):
        # Rename master dss file to Master.dss
        # os.rename(f'{self.out_dir}/{self.file_name}_master.dss', f'{self.out_dir}/Master.dss')
        dss_converter = dss_to_cim.DSStoCIM()
        dss_converter.convert_file(file_path=f'{self.out_dir}', master_file=f'{self.file_name}_master.dss')


def usage():
    print("usage: python cyme_sxst_to_cim.py <full path to sxst file>")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        usage()
        sys.exit()
    SXSTToCIM(sys.argv[1])

