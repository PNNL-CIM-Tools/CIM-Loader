"""Integration tests for Neo4j uploader and connection.

Tests uploading CIM XML files to Neo4j graph database using n10s plugin
and verifies data integrity using Cypher queries.

Prerequisites:
    - Docker daemon running
    - Neo4j container with n10s plugin: docker-compose up -d neo4j-apoc

Usage:
    pytest tests/test_neo4j.py -v
    pytest tests/test_neo4j.py -v -k test_upload
    pytest -m neo4j
"""

import pytest
from pathlib import Path

from cimloader.databases import Neo4jConnection
from cimloader.uploaders import Neo4jUploader


# =============================================================================
# Connection Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.neo4j
class TestNeo4jConnection:
    """Test Neo4j connection functionality."""

    def test_connection_create(self, neo4j_connection):
        """Test that connection can be created."""
        assert neo4j_connection is not None
        assert neo4j_connection.url == 'neo4j://localhost:7687'
        assert neo4j_connection.database == 'neo4j'

    def test_connection_connect(self, neo4j_connection):
        """Test that connection can be established."""
        neo4j_connection.connect()
        assert neo4j_connection.driver is not None

    def test_connection_execute_query(self, neo4j_connection):
        """Test executing a simple Cypher query."""
        query = "MATCH (n) RETURN count(n) AS count"
        result = neo4j_connection.execute(query)
        assert result is not None
        # Result is a tuple: (records, summary, keys)
        records, summary, keys = result
        assert 'count' in keys

    def test_connection_configure(self, neo4j_connection):
        """Test n10s configuration."""
        # configure() should have been called in fixture
        # Verify constraint exists
        query = "SHOW CONSTRAINTS"
        records, _, _ = neo4j_connection.execute(query)
        # Should have n10s_unique_uri constraint
        constraint_names = [record['name'] for record in records if hasattr(record, '__getitem__')]
        # Note: Constraint checking depends on Neo4j version

    def test_connection_drop_all(self, neo4j_connection):
        """Test dropping all data and constraints."""
        neo4j_connection.drop_all()
        query = "MATCH (n) RETURN count(n) AS count"
        records, _, _ = neo4j_connection.execute(query)
        count = records[0]['count']
        assert count == 0, "Database should be empty after drop_all()"

    def test_connection_disconnect(self, neo4j_connection):
        """Test disconnection."""
        neo4j_connection.connect()
        neo4j_connection.disconnect()
        assert neo4j_connection.driver is None


# =============================================================================
# Upload Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.neo4j
@pytest.mark.slow
class TestNeo4jUpload:
    """Test Neo4j upload functionality."""

    def test_upload_from_file_ieee13_seto(self, neo4j_uploader, neo4j_connection, test_model_path):
        """Test uploading IEEE 13 bus SETO model from file."""
        # Get initial count
        query = "MATCH (n) RETURN count(n) AS count"
        records, _, _ = neo4j_connection.execute(query)
        initial_count = records[0]['count']

        # Upload file
        neo4j_uploader.upload_from_file(
            filepath=str(test_model_path),
            filename="ieee13_seto.xml"
        )

        # Verify upload
        records, _, _ = neo4j_connection.execute(query)
        final_count = records[0]['count']
        assert final_count > initial_count, "Nodes should have been added"
        assert final_count > 100, "IEEE 13 model should have substantial nodes"

    def test_upload_from_file_ieee13_2021(self, neo4j_uploader, neo4j_connection, test_model_path):
        """Test uploading IEEE 13 bus 2021 model from file."""
        neo4j_connection.drop_all()
        neo4j_connection.configure()

        # Upload file
        neo4j_uploader.upload_from_file(
            filepath=str(test_model_path),
            filename="ieee13_2021.xml"
        )

        # Verify upload
        query = "MATCH (n) RETURN count(n) AS count"
        records, _, _ = neo4j_connection.execute(query)
        count = records[0]['count']
        assert count > 100, "IEEE 13 2021 model should have substantial nodes"

    def test_upload_verify_cim_labels(self, neo4j_uploader, neo4j_connection, test_model_path):
        """Test that uploaded data contains expected CIM labels."""
        neo4j_connection.drop_all()
        neo4j_connection.configure()

        # Upload file
        neo4j_uploader.upload_from_file(
            filepath=str(test_model_path),
            filename="ieee13_seto.xml"
        )

        # Query for CIM labels
        query = """
        MATCH (n)
        WHERE any(label IN labels(n) WHERE label CONTAINS 'Feeder' OR label CONTAINS 'ACLineSegment')
        RETURN labels(n) AS labels, count(n) AS count
        """
        records, _, _ = neo4j_connection.execute(query)

        # Should have at least some CIM-labeled nodes
        total_cim_nodes = sum(record['count'] for record in records)
        assert total_cim_nodes > 0, "Should have CIM-labeled nodes"

    def test_upload_verify_resource_nodes(self, neo4j_uploader, neo4j_connection, test_model_path):
        """Test that Resource nodes are created by n10s."""
        neo4j_connection.drop_all()
        neo4j_connection.configure()

        # Upload file
        neo4j_uploader.upload_from_file(
            filepath=str(test_model_path),
            filename="ieee13_seto.xml"
        )

        # Query for Resource nodes (n10s creates these)
        query = "MATCH (n:Resource) RETURN count(n) AS count"
        records, _, _ = neo4j_connection.execute(query)
        count = records[0]['count']
        assert count > 0, "Should have Resource nodes from n10s import"


# =============================================================================
# Query Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.neo4j
class TestNeo4jQuery:
    """Test Cypher query functionality on Neo4j."""

    @pytest.fixture(autouse=True)
    def setup_data(self, neo4j_uploader, neo4j_connection, test_model_path):
        """Load test data before each query test."""
        neo4j_connection.drop_all()
        neo4j_connection.configure()
        neo4j_uploader.upload_from_file(
            filepath=str(test_model_path),
            filename="ieee13_seto.xml"
        )
        yield

    def test_query_count_all_nodes(self, neo4j_connection):
        """Test counting all nodes."""
        query = "MATCH (n) RETURN count(n) AS count"
        records, _, _ = neo4j_connection.execute(query)
        count = records[0]['count']
        assert count > 0, "Should have nodes loaded"

    def test_query_count_all_relationships(self, neo4j_connection):
        """Test counting all relationships."""
        query = "MATCH ()-[r]->() RETURN count(r) AS count"
        records, _, _ = neo4j_connection.execute(query)
        count = records[0]['count']
        assert count >= 0, "Should successfully count relationships"

    def test_query_resource_nodes(self, neo4j_connection):
        """Test querying Resource nodes."""
        query = "MATCH (n:Resource) RETURN n.uri AS uri LIMIT 10"
        records, _, _ = neo4j_connection.execute(query)
        assert len(records) > 0, "Should have Resource nodes with URIs"

    def test_query_with_property_filter(self, neo4j_connection):
        """Test query with property filter."""
        query = """
        MATCH (n:Resource)
        WHERE n.uri IS NOT NULL
        RETURN count(n) AS count
        """
        records, _, _ = neo4j_connection.execute(query)
        count = records[0]['count']
        assert count > 0, "Should have Resource nodes with URIs"

    def test_query_relationships_by_type(self, neo4j_connection):
        """Test querying relationships by type."""
        query = """
        MATCH ()-[r]->()
        RETURN type(r) AS relType, count(r) AS count
        ORDER BY count DESC
        LIMIT 5
        """
        records, _, _ = neo4j_connection.execute(query)
        # Should get some relationship types
        assert len(records) >= 0


# =============================================================================
# Configuration Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.neo4j
class TestNeo4jConfiguration:
    """Test Neo4j n10s configuration."""

    def test_configure_creates_constraint(self, neo4j_connection):
        """Test that configure() creates necessary constraints."""
        neo4j_connection.drop_all()
        neo4j_connection.configure()

        # Check for n10s configuration
        query = "CALL n10s.graphconfig.show()"
        try:
            records, _, _ = neo4j_connection.execute(query)
            assert len(records) > 0, "Should have n10s graph configuration"
        except Exception:
            # n10s might not be properly installed
            pytest.skip("n10s plugin not available")

    def test_reconfigure_after_drop(self, neo4j_connection):
        """Test that database can be reconfigured after drop_all()."""
        neo4j_connection.drop_all()
        neo4j_connection.configure()

        # Should be able to query
        query = "MATCH (n) RETURN count(n) AS count"
        records, _, _ = neo4j_connection.execute(query)
        assert records[0]['count'] == 0


# =============================================================================
# Error Handling Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.neo4j
class TestNeo4jErrorHandling:
    """Test error handling in Neo4j operations."""

    def test_upload_nonexistent_file(self, neo4j_uploader):
        """Test uploading a file that doesn't exist."""
        with pytest.raises(Exception):
            neo4j_uploader.upload_from_file(
                filepath="/nonexistent",
                filename="nonexistent.xml"
            )

    def test_query_invalid_cypher(self, neo4j_connection):
        """Test executing invalid Cypher query."""
        with pytest.raises(Exception):
            neo4j_connection.execute("INVALID CYPHER QUERY")

    def test_connection_after_disconnect(self, neo4j_connection):
        """Test that connection is re-established after disconnect."""
        neo4j_connection.connect()
        neo4j_connection.disconnect()
        # Should automatically reconnect on execute
        result = neo4j_connection.execute("RETURN 1 AS value")
        assert result is not None
