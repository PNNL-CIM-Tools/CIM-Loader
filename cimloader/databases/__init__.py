from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List



@dataclass
class Parameter:
    key: Any
    value: Any


@dataclass
class ConnectionParameters:
    url: str = field(default_factory=str)
    host: str = field(default_factory=str)
    port: str = field(default_factory=str)
    filename: str = field(default_factory=str)
    username: str = field(default_factory=str)
    password: str = field(default_factory=str)
    database: str = field(default_factory=str)
    container: str = field(default_factory=str)
    namespace: str = field(default="<http://iec.ch/TC57/CIM100#>")
    cim_profile: str = field(default_factory=str)
    iec61970_301: int = field(default=7)
    

@dataclass
class QueryResponse:
    response: Any


@dataclass
class ConnectionInterface:
    connection_params: ConnectionParameters

    def connect(self):
        raise RuntimeError("Must have implemented connect in inherited class")

    def disconnect(self):
        raise RuntimeError("Must have implemented disconnect in inherited class")

    def execute(self, query: str) -> QueryResponse:
        raise RuntimeError("Must have implemented query in the inherited class")

from cimloader.databases.blazegraph import BlazegraphConnection
from cimloader.databases.neo4j import Neo4jConnection
from cimloader.databases.mysql import MySQLConnection