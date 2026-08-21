"""Integration tests for upload_from_graphmodel across backends.

Regression coverage for the bug where every uploader's
upload_from_graphmodel() raised AttributeError: no attribute
'create_new_graph'. Each uploader built a FeederModel and threw it away --
constructing a GraphModel is a database *read*, so nothing was ever written.

These tests build a graph in memory (no source database) and assert the
objects actually land in the target, so a stub or no-op cannot pass.
"""

import uuid

import pytest


def _make_graph(tag: str):
    """Build a tiny in-memory graph: one BaseVoltage + 2 lines referencing it."""
    import cimgraph.data_profile.rc4_2021 as cim

    base_voltage = cim.BaseVoltage(
        identifier=str(uuid.uuid4()),
        name=f'BV_{tag}',
        nominalVoltage=12470.0,
    )
    lines = {}
    for index in range(2):
        line = cim.ACLineSegment(
            identifier=str(uuid.uuid4()),
            name=f'LINE_{tag}_{index}',
            BaseVoltage=base_voltage,
            length=100.0 + index,
        )
        lines[line.identifier] = line

    return {
        cim.BaseVoltage: {base_voltage.identifier: base_voltage},
        cim.ACLineSegment: lines,
    }


def _count_named(connection, name: str) -> int:
    """Count SPARQL triples whose object is the given IdentifiedObject.name."""
    query = (
        'SELECT (COUNT(*) AS ?count) WHERE { ?s '
        '<http://iec.ch/TC57/CIM100#IdentifiedObject.name> '
        f'"{name}" }}'
    )
    result = connection.execute(query)
    return int(result['results']['bindings'][0]['count']['value'])


# =============================================================================
# SPARQL backends
# =============================================================================

@pytest.mark.integration
@pytest.mark.blazegraph
class TestBlazegraphGraphModelUpload:

    def test_upload_from_graphmodel_writes_objects(self, blazegraph_uploader):
        tag = uuid.uuid4().hex[:8]
        blazegraph_uploader.upload_from_graphmodel(_make_graph(tag))

        assert _count_named(blazegraph_uploader, f'BV_{tag}') > 0
        assert _count_named(blazegraph_uploader, f'LINE_{tag}_0') > 0
        assert _count_named(blazegraph_uploader, f'LINE_{tag}_1') > 0

    def test_upload_from_graphmodel_does_not_raise_attributeerror(
        self, blazegraph_uploader
    ):
        """The original bug surfaced as AttributeError on create_new_graph."""
        blazegraph_uploader.upload_from_graphmodel(_make_graph(uuid.uuid4().hex[:8]))

    def test_upload_from_graphmodel_empty_graph(self, blazegraph_uploader):
        blazegraph_uploader.upload_from_graphmodel({})


@pytest.mark.integration
@pytest.mark.oxigraph
class TestOxigraphGraphModelUpload:

    def test_upload_from_graphmodel_writes_objects(self, oxigraph_uploader):
        tag = uuid.uuid4().hex[:8]
        oxigraph_uploader.upload_from_graphmodel(_make_graph(tag))

        assert _count_named(oxigraph_uploader, f'BV_{tag}') > 0
        assert _count_named(oxigraph_uploader, f'LINE_{tag}_0') > 0

    def test_upload_from_graphmodel_does_not_raise_attributeerror(
        self, oxigraph_uploader
    ):
        oxigraph_uploader.upload_from_graphmodel(_make_graph(uuid.uuid4().hex[:8]))


# =============================================================================
# Neo4j (delegates to cimgraph's n10s-based upload)
# =============================================================================

@pytest.mark.integration
@pytest.mark.neo4j
class TestNeo4jGraphModelUpload:

    def test_upload_from_graphmodel_writes_nodes(self, neo4j_uploader):
        tag = uuid.uuid4().hex[:8]
        neo4j_uploader.upload_from_graphmodel(_make_graph(tag))

        records, _, _ = neo4j_uploader.execute(
            'MATCH (n:Resource) WHERE n.`IdentifiedObject.name` STARTS WITH '
            f'"LINE_{tag}" RETURN count(n) AS count'
        )
        assert records[0]['count'] == 2

    def test_upload_from_graphmodel_preserves_associations(self, neo4j_uploader):
        """Associations must become relationships, not just literals."""
        tag = uuid.uuid4().hex[:8]
        neo4j_uploader.upload_from_graphmodel(_make_graph(tag))

        records, _, _ = neo4j_uploader.execute(
            'MATCH (:Resource)-[r:`ConductingEquipment.BaseVoltage`]->(:Resource) '
            'RETURN count(r) AS count'
        )
        assert records[0]['count'] == 2

    def test_upload_from_graphmodel_applies_cim_labels(self, neo4j_uploader):
        tag = uuid.uuid4().hex[:8]
        neo4j_uploader.upload_from_graphmodel(_make_graph(tag))

        records, _, _ = neo4j_uploader.execute(
            'MATCH (n:ACLineSegment) WHERE n.`IdentifiedObject.name` STARTS WITH '
            f'"LINE_{tag}" RETURN count(n) AS count'
        )
        assert records[0]['count'] == 2

    def test_upload_from_graphmodel_does_not_raise_attributeerror(
        self, neo4j_uploader
    ):
        neo4j_uploader.upload_from_graphmodel(_make_graph(uuid.uuid4().hex[:8]))


# =============================================================================
# GraphModel subclasses: transmission models must work, not just FeederModel
# =============================================================================

@pytest.mark.integration
@pytest.mark.neo4j
class TestGraphModelSubclasses:
    """upload_from_graphmodel takes only the graph dict, so every GraphModel
    subclass must work. Transmission uses BusBranchModel / NodeBreakerModel."""

    @pytest.mark.parametrize('model_name', ['BusBranchModel', 'NodeBreakerModel'])
    def test_upload_from_transmission_model(self, neo4j_uploader, model_name):
        import cimgraph.data_profile.rc4_2021 as cim
        from cimgraph.databases import Neo4jConnection
        import cimgraph.models as models

        model_class = getattr(models, model_name)
        tag = uuid.uuid4().hex[:8]

        substation = cim.Substation(identifier=str(uuid.uuid4()), name=f'SUB_{tag}')
        base_voltage = cim.BaseVoltage(
            identifier=str(uuid.uuid4()),
            name=f'BV_{tag}',
            nominalVoltage=230000.0,
        )
        graph = {
            cim.Substation: {substation.identifier: substation},
            cim.BaseVoltage: {base_voltage.identifier: base_voltage},
        }

        network = model_class(
            container=substation,
            connection=Neo4jConnection(),
            graph=graph,
        )
        # Constructing the model must not discard the caller's graph.
        assert cim.Substation in network.graph

        neo4j_uploader.upload_from_graphmodel(network.graph)

        records, _, _ = neo4j_uploader.execute(
            'MATCH (n:Resource) WHERE n.`IdentifiedObject.name` IN '
            f'["SUB_{tag}", "BV_{tag}"] RETURN count(n) AS count'
        )
        assert records[0]['count'] == 2
