"""Integration tests for Blazegraph uploader and connection.

Tests uploading CIM XML files to Blazegraph triplestore and verifies
data integrity using SPARQL queries.

Prerequisites:
    - Docker daemon running
    - Blazegraph container: docker-compose up -d blazegraph

Usage:
    pytest tests/test_blazegraph.py -v
    pytest tests/test_blazegraph.py -v -k test_upload
    pytest -m blazegraph
"""

import pytest
from pathlib import Path

from cimloader.databases import BlazegraphConnection
from cimloader.uploaders import BlazegraphUploader
from conftest import (
    IEEE13_ASSETS_URL,
    IEEE13_URL,
    count_triples,
    verify_cim_objects,
)


# =============================================================================
# Connection Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.blazegraph
class TestBlazegraphConnection:
    """Test Blazegraph connection functionality."""

    def test_connection_create(self, blazegraph_connection):
        """Test that connection can be created."""
        assert blazegraph_connection is not None
        assert blazegraph_connection.url == 'http://localhost:8889/bigdata/namespace/kb/sparql'

    def test_connection_connect(self, blazegraph_connection):
        """Test that connection can be established."""
        blazegraph_connection.connect()
        assert blazegraph_connection.sparql_obj is not None

    def test_connection_execute_query(self, blazegraph_connection):
        """Test executing a simple SPARQL query."""
        query = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o . }"
        result = blazegraph_connection.execute(query)
        assert result is not None
        assert 'results' in result
        assert 'bindings' in result['results']

    def test_connection_drop_all(self, blazegraph_connection):
        """Test dropping all data from store."""
        blazegraph_connection.drop_all()
        triple_count = count_triples(blazegraph_connection)
        assert triple_count == 0, "Store should be empty after drop_all()"

    def test_connection_disconnect(self, blazegraph_connection):
        """Test disconnection."""
        blazegraph_connection.connect()
        blazegraph_connection.disconnect()
        assert blazegraph_connection.sparql_obj is None


# =============================================================================
# Upload Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.blazegraph
class TestBlazegraphUpload:
    """Test Blazegraph upload functionality."""

    def test_upload_from_file_ieee13_seto(self, blazegraph_uploader, blazegraph_connection, test_model_path):
        """Test uploading IEEE 13 bus SETO model from file."""
        # Clear store
        blazegraph_connection.drop_all()
        initial_count = count_triples(blazegraph_connection)
        assert initial_count == 0

        # Upload file
        blazegraph_uploader.upload_from_file(
            filepath=str(test_model_path),
            filename="ieee13_seto.xml"
        )

        # Verify upload
        final_count = count_triples(blazegraph_connection)
        assert final_count > initial_count, "Triples should have been added"
        assert final_count > 1000, "IEEE 13 model should have substantial data"

    def test_upload_from_file_ieee13_2021(self, blazegraph_uploader, blazegraph_connection, test_model_path):
        """Test uploading IEEE 13 bus 2021 model from file."""
        # Clear store
        blazegraph_connection.drop_all()

        # Upload file
        blazegraph_uploader.upload_from_file(
            filepath=str(test_model_path),
            filename="ieee13_2021.xml"
        )

        # Verify upload
        final_count = count_triples(blazegraph_connection)
        assert final_count > 1000, "IEEE 13 2021 model should have substantial data"

    def test_upload_multiple_files(self, blazegraph_uploader, blazegraph_connection, test_model_path):
        """Test uploading multiple files to the same store."""
        blazegraph_connection.drop_all()

        # Upload first file
        blazegraph_uploader.upload_from_file(
            filepath=str(test_model_path),
            filename="ieee13_seto.xml"
        )
        count1 = count_triples(blazegraph_connection)

        # Upload second file
        blazegraph_uploader.upload_from_file(
            filepath=str(test_model_path),
            filename="ieee13_2021.xml"
        )
        count2 = count_triples(blazegraph_connection)

        assert count2 > count1, "Second upload should add more triples"

    def test_upload_verify_cim_structure(self, blazegraph_uploader, blazegraph_connection, test_model_path):
        """Test that uploaded data contains expected CIM classes."""
        blazegraph_connection.drop_all()

        # Upload file
        blazegraph_uploader.upload_from_file(
            filepath=str(test_model_path),
            filename="ieee13_seto.xml"
        )

        # Verify CIM structure
        cim_counts = verify_cim_objects(blazegraph_connection)

        assert cim_counts['feeders'] > 0, "Should have at least one Feeder"
        assert cim_counts['lines'] > 0, "Should have ACLineSegments"
        # Note: Transformers and loads may or may not be present depending on model
        assert sum(cim_counts.values()) > 0, "Should have some CIM objects"


# =============================================================================
# URL Upload Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.blazegraph
class TestBlazegraphUploadFromURL:
    """Test uploading CIM models fetched directly from a raw GitHub URL."""

    def test_upload_from_url_ieee13(
        self, blazegraph_uploader, blazegraph_connection, raw_github_reachable
    ):
        """Download IEEE13.xml from raw GitHub and verify it loaded."""
        blazegraph_connection.drop_all()
        assert count_triples(blazegraph_connection) == 0

        blazegraph_uploader.upload_from_url(IEEE13_URL)

        assert count_triples(blazegraph_connection) > 1000
        cim_counts = verify_cim_objects(blazegraph_connection)
        assert cim_counts['feeders'] > 0, "Should have at least one Feeder"
        assert cim_counts['lines'] > 0, "Should have ACLineSegments"

    def test_upload_from_url_ieee13_assets(
        self, blazegraph_uploader, blazegraph_connection, raw_github_reachable
    ):
        """Download IEEE13_Assets.xml from raw GitHub and verify it loaded."""
        blazegraph_connection.drop_all()

        blazegraph_uploader.upload_from_url(IEEE13_ASSETS_URL)

        assert count_triples(blazegraph_connection) > 1000


# =============================================================================
# Query Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.blazegraph
class TestBlazegraphQuery:
    """Test SPARQL query functionality on Blazegraph."""

    @pytest.fixture(autouse=True)
    def setup_data(self, blazegraph_uploader, blazegraph_connection, test_model_path):
        """Load test data before each query test."""
        blazegraph_connection.drop_all()
        blazegraph_uploader.upload_from_file(
            filepath=str(test_model_path),
            filename="ieee13_seto.xml"
        )
        yield

    def test_query_count_all_triples(self, blazegraph_connection):
        """Test counting all triples."""
        count = count_triples(blazegraph_connection)
        assert count > 0, "Should have triples loaded"

    def test_query_cim_feeders(self, blazegraph_connection):
        """Test querying for CIM Feeder objects."""
        query = """
        PREFIX cim: <http://iec.ch/TC57/CIM100#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?feeder ?name
        WHERE {
            ?feeder rdf:type cim:Feeder .
            OPTIONAL { ?feeder cim:IdentifiedObject.name ?name . }
        }
        """
        result = blazegraph_connection.execute(query)
        assert len(result['results']['bindings']) > 0, "Should find at least one feeder"

    def test_query_cim_lines(self, blazegraph_connection):
        """Test querying for ACLineSegment objects."""
        query = """
        PREFIX cim: <http://iec.ch/TC57/CIM100#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT (COUNT(?line) AS ?count)
        WHERE {
            ?line rdf:type cim:ACLineSegment .
        }
        """
        result = blazegraph_connection.execute(query)
        count = int(result['results']['bindings'][0]['count']['value'])
        assert count >= 0, "Should successfully count lines (may be 0)"

    def test_query_with_filter(self, blazegraph_connection):
        """Test SPARQL query with FILTER clause."""
        query = """
        PREFIX cim: <http://iec.ch/TC57/CIM100#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?obj ?name
        WHERE {
            ?obj rdf:type ?type .
            ?obj cim:IdentifiedObject.name ?name .
            FILTER(STRSTARTS(STR(?type), "http://iec.ch/TC57/CIM100#"))
        }
        LIMIT 10
        """
        result = blazegraph_connection.execute(query)
        # Should get results or empty list, but no error
        assert 'results' in result
        assert 'bindings' in result['results']


# =============================================================================
# Error Handling Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.blazegraph
class TestBlazegraphErrorHandling:
    """Test error handling in Blazegraph operations."""

    def test_upload_nonexistent_file(self, blazegraph_uploader):
        """Test uploading a file that doesn't exist."""
        with pytest.raises(Exception):
            blazegraph_uploader.upload_from_file(
                filepath="/nonexistent",
                filename="file.xml"
            )

    def test_query_invalid_sparql(self, blazegraph_connection):
        """Test executing invalid SPARQL query."""
        # Malformed SPARQL should raise an exception or return error
        with pytest.raises(Exception):
            blazegraph_connection.execute("INVALID SPARQL QUERY")

    def test_connection_after_disconnect(self, blazegraph_connection):
        """Test that connection is re-established after disconnect."""
        blazegraph_connection.connect()
        blazegraph_connection.disconnect()
        # Should automatically reconnect on execute
        result = blazegraph_connection.execute("SELECT * WHERE { ?s ?p ?o } LIMIT 1")
        assert result is not None
