"""Pytest configuration and fixtures for CIM-Loader integration tests.

This module provides shared fixtures for database connections, test data,
and helper functions used across all integration tests.

Prerequisites:
    - Docker daemon running
    - Services started: docker-compose up -d
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Generator

import pytest
import requests


# =============================================================================
# Test Configuration
# =============================================================================

TEST_DIR = Path(__file__).parent
TEST_MODELS_DIR = TEST_DIR / "test_models"
IEEE13_SETO_FILE = "ieee13_seto.xml"
IEEE13_2021_FILE = "ieee13_2021.xml"

# Raw-GitHub URLs used by upload_from_url integration tests. These come from
# GRIDAPPSD/Powergrid-Models so the tests don't rely on CIM-Loader having the
# same files at the same path on its own default branch.
_RAW_BASE = (
    "https://raw.githubusercontent.com/GRIDAPPSD/Powergrid-Models"
    "/develop/models/feeders/CIM/XML"
)
IEEE13_URL = f"{_RAW_BASE}/IEEE13.xml"
IEEE13_ASSETS_URL = f"{_RAW_BASE}/IEEE13_Assets.xml"


# =============================================================================
# Environment Configuration Fixtures
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up common environment variables for all tests."""
    os.environ['CIMG_NAMESPACE'] = 'http://iec.ch/TC57/CIM100#'
    os.environ['CIMG_CIM_PROFILE'] = 'rc4_2021'
    os.environ['CIMG_IEC61970_301'] = '8'
    os.environ['CIMG_USE_UNITS'] = 'False'
    yield
    # Cleanup after all tests (optional)


@pytest.fixture
def blazegraph_env():
    """Configure environment for Blazegraph tests."""
    os.environ['CIMG_URL'] = 'http://localhost:8889/bigdata/namespace/kb/sparql'
    yield
    # Clear after test to avoid cross-contamination


@pytest.fixture
def neo4j_env():
    """Configure environment for Neo4j tests."""
    os.environ['CIMG_URL'] = 'neo4j://localhost:7687'
    os.environ['CIMG_HOST'] = 'localhost'
    os.environ['CIMG_PORT'] = '7687'
    os.environ['CIMG_USERNAME'] = 'neo4j'
    os.environ['CIMG_PASSWORD'] = 'test1234'
    os.environ['CIMG_DATABASE'] = 'neo4j'
    yield


@pytest.fixture
def oxigraph_env():
    """Configure environment for Oxigraph tests."""
    os.environ['CIMG_URL'] = 'http://localhost:7878/query'
    yield


# =============================================================================
# Docker Service Availability Checks
# =============================================================================

def is_docker_running() -> bool:
    """Check if Docker daemon is running."""
    try:
        result = subprocess.run(
            ['docker', 'ps'],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def is_container_running(container_name: str) -> bool:
    """Check if a specific Docker container is running."""
    try:
        result = subprocess.run(
            ['docker', 'ps', '--filter', f'name={container_name}', '--format', '{{.Names}}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return container_name in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def wait_for_service(url: str, timeout: int = 30) -> bool:
    """Wait for a service to become available.

    Args:
        url: Service URL to check
        timeout: Maximum time to wait in seconds

    Returns:
        True if service became available, False otherwise
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code in (200, 404):  # 404 is OK for some endpoints
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False


@pytest.fixture(scope="session")
def docker_compose_check():
    """Verify Docker Compose services are running."""
    if not is_docker_running():
        pytest.skip("Docker daemon not running. Start with: docker-compose up -d")
    yield


# =============================================================================
# Database Connection Fixtures
# =============================================================================

@pytest.fixture
def blazegraph_connection(blazegraph_env, docker_compose_check):
    """Provide a Blazegraph connection for tests."""
    from cimloader.databases import BlazegraphConnection

    if not is_container_running('blazegraph_cim_loader'):
        pytest.skip("Blazegraph container not running. Start with: docker-compose up -d blazegraph")

    if not wait_for_service('http://localhost:8889'):
        pytest.skip("Blazegraph service not responding")

    connection = BlazegraphConnection()
    connection.drop_all()  # Clean state for each test
    yield connection
    # Cleanup after test
    try:
        connection.drop_all()
    except:
        pass


@pytest.fixture
def neo4j_connection(neo4j_env, docker_compose_check):
    """Provide a Neo4j connection for tests."""
    from cimloader.databases import Neo4jConnection

    if not is_container_running('neo4j_cim_loader'):
        pytest.skip("Neo4j container not running. Start with: docker-compose up -d neo4j-apoc")

    if not wait_for_service('http://localhost:7474'):
        pytest.skip("Neo4j service not responding")

    connection = Neo4jConnection()
    connection.connect()

    # Clean state
    try:
        connection.drop_all()
        connection.configure()
    except:
        connection.configure()

    yield connection

    # Cleanup after test
    try:
        connection.drop_all()
        connection.disconnect()
    except:
        pass


@pytest.fixture
def oxigraph_connection(oxigraph_env, docker_compose_check):
    """Provide an Oxigraph connection for tests."""
    from cimloader.databases import OxigraphConnection

    if not is_container_running('oxigraph_cim_loader'):
        pytest.skip("Oxigraph container not running. Start with: docker-compose up -d oxigraph")

    if not wait_for_service('http://localhost:7878'):
        pytest.skip("Oxigraph service not responding")

    connection = OxigraphConnection()
    connection.drop_all()  # Clean state
    yield connection

    # Cleanup
    try:
        connection.drop_all()
    except:
        pass


# =============================================================================
# Uploader Fixtures
# =============================================================================

@pytest.fixture
def blazegraph_uploader(blazegraph_env, docker_compose_check):
    """Provide a Blazegraph uploader for tests."""
    from cimloader.uploaders import BlazegraphUploader

    if not is_container_running('blazegraph_cim_loader'):
        pytest.skip("Blazegraph container not running")

    return BlazegraphUploader()


@pytest.fixture
def neo4j_uploader(neo4j_env, docker_compose_check):
    """Provide a Neo4j uploader for tests."""
    from cimloader.uploaders import Neo4jUploader

    if not is_container_running('neo4j_cim_loader'):
        pytest.skip("Neo4j container not running")

    # Use the actual container name from docker-compose.yml
    uploader = Neo4jUploader(container='neo4j_cim_loader')
    uploader.connect()
    uploader.drop_all()
    uploader.configure()

    return uploader


@pytest.fixture
def oxigraph_uploader(oxigraph_env, docker_compose_check):
    """Provide an Oxigraph uploader for tests."""
    from cimloader.uploaders import OxigraphUploader

    if not is_container_running('oxigraph_cim_loader'):
        pytest.skip("Oxigraph container not running")

    return OxigraphUploader()


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def raw_github_reachable() -> bool:
    """Skip URL tests if raw.githubusercontent.com can't be reached."""
    try:
        r = requests.head(IEEE13_URL, timeout=5, allow_redirects=True)
        if r.status_code != 200:
            pytest.skip(f"Test model URL returned {r.status_code}: {IEEE13_URL}")
    except requests.RequestException as e:
        pytest.skip(f"raw.githubusercontent.com unreachable: {e}")
    return True


@pytest.fixture
def test_model_path() -> Path:
    """Provide path to test models directory."""
    return TEST_MODELS_DIR


@pytest.fixture
def ieee13_seto_file() -> str:
    """Provide path to IEEE 13 bus SETO model."""
    filepath = TEST_MODELS_DIR / IEEE13_SETO_FILE
    if not filepath.exists():
        pytest.skip(f"Test model not found: {filepath}")
    return str(filepath)


@pytest.fixture
def ieee13_2021_file() -> str:
    """Provide path to IEEE 13 bus 2021 model."""
    filepath = TEST_MODELS_DIR / IEEE13_2021_FILE
    if not filepath.exists():
        pytest.skip(f"Test model not found: {filepath}")
    return str(filepath)


# =============================================================================
# Helper Functions
# =============================================================================

def count_triples(connection) -> int:
    """Count total number of triples in a SPARQL endpoint.

    Args:
        connection: Database connection (Blazegraph or Oxigraph)

    Returns:
        Number of triples in the store
    """
    query = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o . }"
    result = connection.execute(query)
    return int(result['results']['bindings'][0]['count']['value'])


def verify_cim_objects(connection) -> dict:
    """Verify CIM objects were loaded by counting common classes.

    Args:
        connection: Database connection (Blazegraph or Oxigraph)

    Returns:
        Dictionary with counts of CIM object types
    """
    query = """
    PREFIX cim: <http://iec.ch/TC57/CIM100#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT
        (COUNT(DISTINCT ?feeder) AS ?feeders)
        (COUNT(DISTINCT ?line) AS ?lines)
        (COUNT(DISTINCT ?transformer) AS ?transformers)
        (COUNT(DISTINCT ?load) AS ?loads)
    WHERE {
        OPTIONAL { ?feeder rdf:type cim:Feeder . }
        OPTIONAL { ?line rdf:type cim:ACLineSegment . }
        OPTIONAL { ?transformer rdf:type cim:PowerTransformer . }
        OPTIONAL { ?load rdf:type cim:EnergyConsumer . }
    }
    """
    result = connection.execute(query)
    bindings = result['results']['bindings'][0]

    return {
        'feeders': int(bindings.get('feeders', {}).get('value', 0)),
        'lines': int(bindings.get('lines', {}).get('value', 0)),
        'transformers': int(bindings.get('transformers', {}).get('value', 0)),
        'loads': int(bindings.get('loads', {}).get('value', 0))
    }


# Export helper functions for use in tests
pytest.count_triples = count_triples
pytest.verify_cim_objects = verify_cim_objects
