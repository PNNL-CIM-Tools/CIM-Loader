"""Base connection interface for CIM-Loader database connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

QueryResponse = Any


class ConnectionInterface(ABC):
    """Contract every database connection class must implement.

    This is deliberately narrower than cimgraph's ConnectionInterface.
    cimloader connections are **bulk-ingest / query** connections: they load
    RDF files and URLs and run raw queries. They intentionally do NOT
    implement cimgraph's object-graph read API (create_new_graph,
    get_all_edges, get_object, ...), which belongs to cimgraph because it
    depends on the CIM data profile.

    They also do not subclass cimgraph's connections, because the two are not
    driver-compatible: cimgraph's Neo4jConnection uses the async neo4j driver
    (returning a list of records) to parallelize edge queries, while these use
    the sync driver (returning (records, summary, keys)). To read a graph into
    memory, use cimgraph.databases.*; to write one back, see
    uploaders.upload_from_graphmodel.
    """

    @abstractmethod
    def connect(self) -> None:
        ...

    @abstractmethod
    def disconnect(self) -> None:
        ...

    @abstractmethod
    def execute(self, query: str) -> QueryResponse:
        ...

    # NOTE: SPARQL-backed connections (Blazegraph, Oxigraph, Neptune, GraphDB)
    # also provide update(query) for writes, which upload_from_graphmodel
    # relies on. It is deliberately NOT abstract here: Neo4j speaks Cypher and
    # has no SPARQL update endpoint, so requiring it would make
    # Neo4jConnection uninstantiable for no benefit.
