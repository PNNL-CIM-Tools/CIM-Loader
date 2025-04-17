from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List



@dataclass
class Parameter:
    key: Any
    value: Any



@dataclass
class QueryResponse:
    response: Any


@dataclass
class ConnectionInterface:

    def connect(self):
        raise RuntimeError("Must have implemented connect in inherited class")

    def disconnect(self):
        raise RuntimeError("Must have implemented disconnect in inherited class")

    def execute(self, query: str) -> QueryResponse:
        raise RuntimeError("Must have implemented query in the inherited class")

from cimloader.databases.blazegraph import BlazegraphConnection
from cimloader.databases.neo4j import Neo4jConnection
from cimloader.databases.mysql import MySQLConnection