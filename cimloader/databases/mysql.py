import re
import mysql.connector
import logging
import importlib
import json
import enum
import time

from cimloader.databases import ConnectionInterface, ConnectionParameters, Parameter, QueryResponse
from cimgraph.data_profile.known_problem_classes import ClassesWithoutMRID
from cimgraph.models import GraphModel

_log = logging.getLogger(__name__)

class MySQLConnection(ConnectionInterface):
    def __init__(self, connection_parameters: ConnectionParameters):
        self.connection_parameters = connection_parameters
        self.cim_profile = connection_parameters.cim_profile
        self.cim = importlib.import_module('cimgraph.data_profile.' + self.cim_profile)
        self.namespace = connection_parameters.namespace
        self.host = connection_parameters.host
        self.port = connection_parameters.port
        self.username = connection_parameters.username
        self.password = connection_parameters.password
        self.database = connection_parameters.database
        self.connection = None
        self.cursor = None

    def connect(self):
        if not self.cursor:
            if not self.database: # Set database name to CIM Profile name if not specified
                self.database = self.cim_profile 
            try:
                self.connection = mysql.connector.connect(host = self.host, user = self.username, password = self.password, database = self.database)
                self.cursor = self.connection.cursor(buffered = True)
            except:
                _log.error('Could not connect to database')

    def disconnect(self):
        self.cursor = None

    def execute(self, query_message: str) -> QueryResponse:
        self.connect()
        self.cursor.execute(query_message)
        response = self.cursor.fetchall()
        return response
    
    def create_database(self, database:str = None, overwrite:bool = True):
        if database is None:
            if self.database is None:
                database = self.cim_profile
            else:
                database = self.database
        self.database = database
        connection = mysql.connector.connect(host = self.host, user = self.username, password = self.password)
        cursor = connection.cursor(buffered = True)
        if overwrite:
            # try:
            cursor.execute(f"DROP DATABASE {database}")
            # except:
            #     _log.error("Unable to connect to database")
        
        # try:
        cursor.execute(f"CREATE DATABASE {database}")
        # except:
            # _log.error("Unable to create new database")

    def configure(self, overwrite:bool = True):
        class_list = self.cim.__all__
        classes_without_mrid = ClassesWithoutMRID()
        
        for class_name in class_list:
            cim_class = eval(f"self.cim.{class_name}")
            # print(cim_class.__name__)

            try:
                self.connect()
                self.cursor.execute(f"DROP TABLE {cim_class.__name__}")
            except:
                pass
            # Get all attribute types from CIMantic Graphs dataclasses
            try:
                if type(cim_class) == enum.EnumMeta:
                        values = cim_class._member_names_
                        sql_query = f"CREATE TABLE {cim_class.__name__} (enumeration VARCHAR(255))"
                        self.cursor.execute(sql_query) # create table
                        for value in values:
                            sql_insert = f"""INSERT INTO {cim_class.__name__} (enumeration) VALUES ("{value}")"""
                            self.cursor.execute(sql_insert)
                else:
                    # Check if is class and has class fields
                    fields = cim_class.__dataclass_fields__
                    sql_query = f"CREATE TABLE {cim_class.__name__} ("
                    
                    sql_query = sql_query + "username VARCHAR(255), "
                    sql_query = sql_query + "timestamp INT, "

                    # Handling for problem classes that don't inherit from IdentifiedObject
                    if cim_class in classes_without_mrid.classes:
                        sql_query = sql_query + "_mRID VARCHAR(255), "
                    # Iterate through all attributes and add to table
                    for attr in list(fields.keys()):
                        attribute_name = fields[attr].type
                        # Determine type of attribute value and use correct column type in table
                        if "List" in attribute_name:
                            sql_query = sql_query + f"_{attr} JSON, "
                        elif "float" in attribute_name:
                            sql_query = sql_query + f"_{attr} FLOAT, "
                        elif 'Optional' in attribute_name: #check if attribute is association to a class object
                            if '\'' in attribute_name: #handling inconsistent '' marks in data profile
                                at_cls = re.match(r'Optional\[\'(.*)\']',attribute_name)
                                attribute_name = at_cls.group(1)
                            else:        
                                at_cls = re.match(r'Optional\[(.*)]',attribute_name)
                                attribute_name = at_cls.group(1)
                            # If a CIM class, then use JSON-LD
                            if attribute_name in self.cim.__all__:
                                attribute_class = eval(f"self.cim.{attribute_name}")
                                if type(attribute_class) == enum.EnumMeta:
                                    sql_query = sql_query + f"_{attr} FLOAT, "
                                else:
                                    sql_query = sql_query + f"_{attr} JSON, "

                            else:
                                sql_query = sql_query + f"_{attr} VARCHAR(255), "
                        else:
                            sql_query = sql_query + f"_{attr} VARCHAR(255), "
                    sql_query = sql_query[:-2] # remove extra punctuation
                    sql_query = sql_query + ")"
                    # print(sql_query)
                    self.cursor.execute(sql_query) # create table
                    _log.info(f"Created table for class {class_name}")
            except:
                _log.warning(f"Unable to create table for class {class_name}")







    def upload_from_file(self):
        pass

    def upload_from_url(self):
        pass

    def upload_from_rdflib(self, rdflib_graph):

        pass

    def upload_from_cimgraph(self, network:GraphModel):
        
        class_list = list(network.graph.keys())
        for cim_class in class_list:
            # Get JSON-LD representation of model
            table = network.cim_dump(cim_class)
            fields = cim_class.__dataclass_fields__
            # Insert each power system object in CIMantic Graphs model
            for obj in table.values():
                # Create SQL Query
                sql_insert = f"INSERT INTO {cim_class.__name__} ("
                sql_values = " VALUES ("
                sql_params = [self.username, int(time.time())]

                sql_insert = sql_insert + "username, timestamp, "
                sql_values = sql_values + f"%s, %s, "
                # Iterate through each attribute
                for attr in list(obj.keys()):
                    sql_insert = sql_insert + f"_{attr}, "
                    sql_values = sql_values + f"%s, "
                    
                    if "List" in fields[attr].type:
                        sql_params.append(json.dumps(obj[attr])) # JSON-LD List of RDF links
                    elif "float" in fields[attr].type:
                        sql_params.append(obj[attr]) # float
                    else:
                        sql_params.append(str(obj[attr])) # free text

                sql_insert = sql_insert[:-2] # remove extra punctuation
                sql_insert = sql_insert + ")"
                sql_values = sql_values[:-2] # remove extra punctuation
                sql_values = sql_values + ")"
                sql_query = sql_insert + sql_values # append query message
                sql_params = tuple(sql_params)
                self.cursor.execute(sql_query, sql_params) # insert all CIM objects
