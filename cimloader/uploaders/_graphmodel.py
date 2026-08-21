"""Shared helper for uploading a cimgraph graph dict to a SPARQL endpoint."""

from __future__ import annotations

import logging

_log = logging.getLogger(__name__)


def upload_graph_via_sparql(connection, graph_dict: dict, target: str) -> None:
    """INSERT DATA each object of a cimgraph graph dict into a SPARQL store.

    Works with any GraphModel subclass (FeederModel, BusBranchModel,
    NodeBreakerModel) since only the ``graph`` dict is needed -- the model
    type and its container are irrelevant to the triples produced.

    Args:
        connection: a cimloader connection exposing ``update()``.
        graph_dict: ``{cim_class: {identifier: object}}``, e.g. GraphModel.graph.
        target: database name, used only for logging.
    """
    # Imported here so a missing/renamed cimgraph query module fails at upload
    # time with a clear traceback rather than at package import.
    from cimgraph.queries.sparql import upload_triples_sparql

    _log.info('Uploading graph with %d object types to %s', len(graph_dict), target)

    count = 0
    for objects in graph_dict.values():
        for obj in objects.values():
            connection.update(upload_triples_sparql(obj))
            count += 1

    _log.info('Uploaded %d objects to %s', count, target)
