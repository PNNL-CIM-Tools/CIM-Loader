"""Integration tests for Oxigraph uploader and connection.

Tests uploading CIM XML files to Oxigraph triplestore and verifies
data integrity using SPARQL queries.

Prerequisites:
    - Docker daemon running
    - Oxigraph container: docker-compose up -d oxigraph

Usage:
    pytest tests/test_oxigraph.py -v
    pytest tests/test_oxigraph.py -v -k test_upload
    pytest -m oxigraph
"""

import pytest
from pathlib import Path

from cimloader.databases import OxigraphConnection
from cimloader.uploaders import OxigraphUploader
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
@pytest.mark.oxigraph
class TestOxigraphConnection:
    """Test Oxigraph connection functionality."""

    def test_connection_create(self, oxigraph_connection):
        """Test that connection can be created."""
        assert oxigraph_connection is not None
        assert oxigraph_connection.url == 'http://localhost:7878/query'

    def test_connection_connect(self, oxigraph_connection):
        """Test that connection can be established."""
        oxigraph_connection.connect()
        assert oxigraph_connection.sparql_obj is not None

    def test_connection_execute_query(self, oxigraph_connection):
        """Test executing a simple SPARQL query."""
        query = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o . }"
        result = oxigraph_connection.execute(query)
        assert result is not None
        assert 'results' in result
        assert 'bindings' in result['results']

    def test_connection_drop_all(self, oxigraph_connection):
        """Test dropping all data from store."""
        oxigraph_connection.drop_all()
        triple_count = count_triples(oxigraph_connection)
        assert triple_count == 0, "Store should be empty after drop_all()"

    def test_connection_disconnect(self, oxigraph_connection):
        """Test disconnection."""
        oxigraph_connection.connect()
        oxigraph_connection.disconnect()
        assert oxigraph_connection.sparql_obj is None


# =============================================================================
# Upload Tests - Direct Mode
# =============================================================================

@pytest.mark.integration
@pytest.mark.oxigraph
class TestOxigraphDirectUpload:
    """Test Oxigraph direct upload (no Docker container)."""

    def test_upload_from_file_ieee13_seto(self, oxigraph_uploader, oxigraph_connection, test_model_path):
        """Test uploading IEEE 13 bus SETO model."""
        # Clear store
        oxigraph_connection.drop_all()
        initial_count = count_triples(oxigraph_connection)
        assert initial_count == 0

        # Upload file
        oxigraph_uploader.upload_from_file(
            filepath=str(test_model_path),
            filename="ieee13_seto.xml"
        )

        # Verify upload
        final_count = count_triples(oxigraph_connection)
        assert final_count > initial_count, "Triples should have been added"
        assert final_count > 1000, "IEEE 13 model should have substantial data"

    def test_upload_from_file_ieee13_2021(self, oxigraph_uploader, oxigraph_connection, test_model_path):
        """Test uploading IEEE 13 bus 2021 model."""
        # Clear store
        oxigraph_connection.drop_all()

        # Upload file
        oxigraph_uploader.upload_from_file(
            filepath=str(test_model_path),
            filename="ieee13_2021.xml"
        )

        # Verify upload
        final_count = count_triples(oxigraph_connection)
        assert final_count > 1000, "IEEE 13 2021 model should have substantial data"

    def test_upload_multiple_files(self, oxigraph_uploader, oxigraph_connection, test_model_path):
        """Test uploading multiple files to the same store."""
        oxigraph_connection.drop_all()

        # Upload first file
        oxigraph_uploader.upload_from_file(
            filepath=str(test_model_path),
            filename="ieee13_seto.xml"
        )
        count1 = count_triples(oxigraph_connection)

        # Upload second file
        oxigraph_uploader.upload_from_file(
            filepath=str(test_model_path),
            filename="ieee13_2021.xml"
        )
        count2 = count_triples(oxigraph_connection)

        assert count2 > count1, "Second upload should add more triples"

    def test_upload_verify_cim_structure(self, oxigraph_uploader, oxigraph_connection, test_model_path):
        """Test that uploaded data contains expected CIM classes."""
        oxigraph_connection.drop_all()

        # Upload file
        oxigraph_uploader.upload_from_file(
            filepath=str(test_model_path),
            filename="ieee13_seto.xml"
        )

        # Verify CIM structure
        cim_counts = verify_cim_objects(oxigraph_connection)

        assert cim_counts['feeders'] > 0, "Should have at least one Feeder"
        assert cim_counts['lines'] > 0, "Should have ACLineSegments"
        assert sum(cim_counts.values()) > 0, "Should have some CIM objects"


# =============================================================================
# Upload Tests - Container Mode
# =============================================================================

@pytest.mark.integration
@pytest.mark.oxigraph
@pytest.mark.requires_docker
class TestOxigraphContainerUpload:
    """Test Oxigraph upload via Docker container."""

    def test_upload_via_container(self, oxigraph_connection, test_model_path):
        """Test uploading via Docker container using docker cp."""
        from cimloader.uploaders import OxigraphUploader

        # Create uploader with container name
        uploader = OxigraphUploader(container='oxigraph_cim_loader')

        # Clear store
        oxigraph_connection.drop_all()

        # Upload file via container
        uploader.upload_from_file(
            filepath=str(test_model_path),
            filename="ieee13_seto.xml"
        )

        # Verify upload
        final_count = count_triples(oxigraph_connection)
        assert final_count > 1000, "Should have uploaded data via container"

        # Verify CIM structure
        cim_counts = verify_cim_objects(oxigraph_connection)
        assert sum(cim_counts.values()) > 0, "Should have CIM objects"


# =============================================================================
# URL Upload Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.oxigraph
class TestOxigraphUploadFromURL:
    """Test uploading CIM models fetched directly from a raw GitHub URL."""

    def test_upload_from_url_ieee13(
        self, oxigraph_uploader, oxigraph_connection, raw_github_reachable
    ):
        """Download IEEE13.xml from raw GitHub and verify it loaded."""
        oxigraph_connection.drop_all()
        assert count_triples(oxigraph_connection) == 0

        oxigraph_uploader.upload_from_url(IEEE13_URL)

        assert count_triples(oxigraph_connection) > 1000
        cim_counts = verify_cim_objects(oxigraph_connection)
        assert cim_counts['feeders'] > 0, "Should have at least one Feeder"
        assert cim_counts['lines'] > 0, "Should have ACLineSegments"

    def test_upload_from_url_ieee13_assets(
        self, oxigraph_uploader, oxigraph_connection, raw_github_reachable
    ):
        """Download IEEE13_Assets.xml from raw GitHub and verify it loaded."""
        oxigraph_connection.drop_all()

        oxigraph_uploader.upload_from_url(IEEE13_ASSETS_URL)

        assert count_triples(oxigraph_connection) > 1000


# =============================================================================
# Format Detection Tests
# =============================================================================

class TestFormatDetection:
    """Test the shared `cimloader._formats` helpers.

    These live here historically — they aren't Oxigraph-specific. They exercise
    the single source of truth used by every uploader.
    """

    def test_format_detection_xml(self):
        from cimloader._formats import content_type_from_filename
        assert content_type_from_filename('test.xml') == 'application/rdf+xml'
        assert content_type_from_filename('test.rdf') == 'application/rdf+xml'

    def test_format_detection_turtle(self):
        from cimloader._formats import content_type_from_filename
        assert content_type_from_filename('test.ttl') == 'text/turtle'
        assert content_type_from_filename('test.turtle') == 'text/turtle'

    def test_format_detection_ntriples(self):
        from cimloader._formats import content_type_from_filename
        assert content_type_from_filename('test.nt') == 'application/n-triples'
        assert content_type_from_filename('test.ntriples') == 'application/n-triples'

    def test_format_detection_nquads(self):
        from cimloader._formats import content_type_from_filename
        assert content_type_from_filename('test.nq') == 'application/n-quads'
        assert content_type_from_filename('test.nquads') == 'application/n-quads'

    def test_format_detection_case_insensitive(self):
        from cimloader._formats import content_type_from_filename
        assert content_type_from_filename('TEST.XML') == 'application/rdf+xml'
        assert content_type_from_filename('Test.TTL') == 'text/turtle'

    def test_format_detection_unsupported(self):
        from cimloader._formats import content_type_from_filename
        with pytest.raises(ValueError, match="Unsupported RDF format"):
            content_type_from_filename('test.json')
        with pytest.raises(ValueError, match="Unsupported RDF format"):
            content_type_from_filename('test.txt')

    def test_format_detection_from_url_strips_query_and_fragment(self):
        from cimloader._formats import content_type_from_url
        assert content_type_from_url(
            'https://example.com/a/b/feeder.xml?ref=main'
        ) == 'application/rdf+xml'
        assert content_type_from_url(
            'https://example.com/a/b/feeder.ttl#section'
        ) == 'text/turtle'


# =============================================================================
# Query Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.oxigraph
class TestOxigraphQuery:
    """Test SPARQL query functionality on Oxigraph."""

    @pytest.fixture(autouse=True)
    def setup_data(self, oxigraph_uploader, oxigraph_connection, test_model_path):
        """Load test data before each query test."""
        oxigraph_connection.drop_all()
        oxigraph_uploader.upload_from_file(
            filepath=str(test_model_path),
            filename="ieee13_seto.xml"
        )
        yield

    def test_query_count_all_triples(self, oxigraph_connection):
        """Test counting all triples."""
        count = count_triples(oxigraph_connection)
        assert count > 0, "Should have triples loaded"

    def test_query_cim_feeders(self, oxigraph_connection):
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
        result = oxigraph_connection.execute(query)
        assert len(result['results']['bindings']) > 0, "Should find at least one feeder"

    def test_query_cim_lines(self, oxigraph_connection):
        """Test querying for ACLineSegment objects."""
        query = """
        PREFIX cim: <http://iec.ch/TC57/CIM100#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT (COUNT(?line) AS ?count)
        WHERE {
            ?line rdf:type cim:ACLineSegment .
        }
        """
        result = oxigraph_connection.execute(query)
        count = int(result['results']['bindings'][0]['count']['value'])
        assert count >= 0, "Should successfully count lines"

    def test_query_with_filter(self, oxigraph_connection):
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
        result = oxigraph_connection.execute(query)
        assert 'results' in result
        assert 'bindings' in result['results']

    def test_query_update(self, oxigraph_connection):
        """Test SPARQL UPDATE operation."""
        # Insert some test data
        update = """
        PREFIX test: <http://example.org/test#>
        INSERT DATA {
            test:subject test:predicate "test object" .
        }
        """
        oxigraph_connection.update(update)

        # Verify it was inserted
        query = """
        PREFIX test: <http://example.org/test#>
        SELECT ?o
        WHERE {
            test:subject test:predicate ?o .
        }
        """
        result = oxigraph_connection.execute(query)
        assert len(result['results']['bindings']) > 0


# =============================================================================
# Error Handling Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.oxigraph
class TestOxigraphErrorHandling:
    """Test error handling in Oxigraph operations."""

    def test_upload_unknown_extension(self, oxigraph_uploader):
        """Uploading a file whose extension isn't a known RDF format raises."""
        with pytest.raises(ValueError, match="Unsupported RDF format"):
            oxigraph_uploader.upload_from_file(
                filepath="/nonexistent",
                filename="nonexistent.xyz",
            )

    def test_query_invalid_sparql(self, oxigraph_connection):
        """Test executing invalid SPARQL query."""
        with pytest.raises(Exception):
            oxigraph_connection.execute("INVALID SPARQL QUERY")

    def test_connection_after_disconnect(self, oxigraph_connection):
        """Test that connection is re-established after disconnect."""
        oxigraph_connection.connect()
        oxigraph_connection.disconnect()
        # Should automatically reconnect on execute
        result = oxigraph_connection.execute("SELECT * WHERE { ?s ?p ?o } LIMIT 1")
        assert result is not None


# =============================================================================
# Performance / Benchmark Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.oxigraph
@pytest.mark.slow
class TestOxigraphPerformance:
    """Performance and benchmark tests for Oxigraph."""

    def test_large_file_upload(self, oxigraph_uploader, oxigraph_connection, test_model_path):
        """Test uploading larger CIM model."""
        import time

        oxigraph_connection.drop_all()

        # Upload and time it
        start = time.time()
        oxigraph_uploader.upload_from_file(
            filepath=str(test_model_path),
            filename="ieee13_seto.xml"
        )
        duration = time.time() - start

        # Verify
        count = count_triples(oxigraph_connection)
        assert count > 0

        # Log performance (not asserting on time, just measuring)
        print(f"\nUploaded {count} triples in {duration:.2f} seconds")

    def test_query_performance(self, oxigraph_uploader, oxigraph_connection, test_model_path):
        """Test query performance."""
        import time

        # Load data
        oxigraph_connection.drop_all()
        oxigraph_uploader.upload_from_file(
            filepath=str(test_model_path),
            filename="ieee13_seto.xml"
        )

        # Complex query
        query = """
        PREFIX cim: <http://iec.ch/TC57/CIM100#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?line ?name ?length
        WHERE {
            ?line rdf:type cim:ACLineSegment .
            OPTIONAL { ?line cim:IdentifiedObject.name ?name . }
            OPTIONAL { ?line cim:Conductor.length ?length . }
        }
        """

        start = time.time()
        result = oxigraph_connection.execute(query)
        duration = time.time() - start

        count = len(result['results']['bindings'])
        print(f"\nQueried {count} lines in {duration:.2f} seconds")
        assert count >= 0
