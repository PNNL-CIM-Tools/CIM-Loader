import re
import mysql.connector
import logging
import importlib
import json
import enum
import time

from cimloader.databases import ConnectionInterface, QueryResponse
from cimgraph.databases import (get_cim_profile, get_database,
                                get_host, get_iec61970_301, get_namespace, get_password, get_port,
                                get_username)
from cimgraph.data_profile.known_problem_classes import ClassesWithoutMRID
from cimgraph.models import GraphModel

_log = logging.getLogger(__name__)

class MySQLConnection(ConnectionInterface):
    def __init__(self):
        self.cim_profile, self.cim = get_cim_profile()
        self.namespace = get_namespace()
        self.host = get_host()
        self.port = get_port()
        self.username = get_username()
        self.password = get_password()
        self.database = get_database()
        self.connection = None
        self.cursor = None

    def connect(self):
        if not self.cursor:
            if not self.database: # Set database name to CIM Profile name if not specified
                self.database = self.cim_profile
            try:
                self.connection = mysql.connector.connect(host = self.host, user = self.username, password = self.password, database = self.database)
                self.cursor = self.connection.cursor(buffered = True)
            except mysql.connector.Error as e:
                _log.error(f'Could not connect to MySQL database at {self.host}:{self.port} - {e}')
                raise  # Re-raise so caller knows connection failed

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
            cursor.execute(f"DROP DATABASE {database}")

        cursor.execute(f"CREATE DATABASE {database}")

    def configure(self, overwrite:bool = True):
        """Create MySQL database schema from CIM dataclass definitions.

        Generates and executes CREATE TABLE statements for each CIM class,
        mapping Python dataclass field types to appropriate MySQL column types.
        """
        class_list = self.cim.__all__
        classes_without_mrid = ClassesWithoutMRID()
        
        for class_name in class_list:
            cim_class = eval(f"self.cim.{class_name}")
            # print(cim_class.__name__)

            try:
                self.connect()
                self.cursor.execute(f"DROP TABLE {cim_class.__name__}")
            except mysql.connector.Error:
                # Table doesn't exist yet, which is fine - we're about to create it
                pass
            # Build table schema by inspecting CIMantic Graphs dataclass fields
            try:
                # Handle enumerations as simple lookup tables
                if type(cim_class) == enum.EnumMeta:
                        values = cim_class._member_names_
                        sql_query = f"CREATE TABLE {cim_class.__name__} (enumeration VARCHAR(255))"
                        self.cursor.execute(sql_query) # create table
                        for value in values:
                            sql_insert = f"""INSERT INTO {cim_class.__name__} (enumeration) VALUES ("{value}")"""
                            self.cursor.execute(sql_insert)
                else:
                    # Regular CIM classes - create tables from dataclass fields
                    fields = cim_class.__dataclass_fields__
                    sql_query = f"CREATE TABLE {cim_class.__name__} ("

                    # Add audit columns to track who uploaded data and when
                    sql_query = sql_query + "username VARCHAR(255), "
                    sql_query = sql_query + "timestamp INT, "

                    # Handle edge case: classes that don't inherit from IdentifiedObject need explicit mRID
                    if cim_class in classes_without_mrid.classes:
                        sql_query = sql_query + "_mRID VARCHAR(255), "

                    # Map each dataclass field to appropriate MySQL column type
                    for attr in list(fields.keys()):
                        attribute_name = fields[attr].type

                        # Map Python type annotations to MySQL column types
                        if "List" in attribute_name:
                            # Lists store JSON arrays of references
                            sql_query = sql_query + f"_{attr} JSON, "
                        elif "float" in attribute_name:
                            sql_query = sql_query + f"_{attr} FLOAT, "
                        elif 'Optional' in attribute_name:
                            # Optional fields may contain references to other CIM objects
                            # Extract the inner type from Optional[Type] using regex
                            if '\'' in attribute_name:
                                # Handle Optional['Type'] with quotes (inconsistent in cimgraph)
                                at_cls = re.match(r'Optional\[\'(.*)\']', attribute_name)
                                attribute_name = at_cls.group(1)
                            else:
                                # Handle Optional[Type] without quotes
                                at_cls = re.match(r'Optional\[(.*)]', attribute_name)
                                attribute_name = at_cls.group(1)

                            # Check if this references another CIM class
                            if attribute_name in self.cim.__all__:
                                attribute_class = eval(f"self.cim.{attribute_name}")
                                if type(attribute_class) == enum.EnumMeta:
                                    # Enum references stored as floats (enum values)
                                    sql_query = sql_query + f"_{attr} FLOAT, "
                                else:
                                    # Class references stored as JSON-LD objects
                                    sql_query = sql_query + f"_{attr} JSON, "
                            else:
                                # Primitive type like Optional[str] or Optional[int]
                                sql_query = sql_query + f"_{attr} VARCHAR(255), "
                        else:
                            # Default to string for unrecognized types
                            sql_query = sql_query + f"_{attr} VARCHAR(255), "
                    sql_query = sql_query[:-2] # remove extra punctuation
                    sql_query = sql_query + ")"
                    # print(sql_query)
                    self.cursor.execute(sql_query) # create table
                    _log.info(f"Created table for class {class_name}")
            except Exception as e:
                _log.warning(f"Unable to create table for class {class_name}: {e}")
                # Continue to next class - one failure shouldn't stop schema creation







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
