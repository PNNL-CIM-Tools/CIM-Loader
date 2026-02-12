#!/usr/bin/env python3
"""Integration test for Oxigraph uploader.

Tests uploading CIM XML files to Oxigraph triplestore and verifies
the data was loaded correctly using SPARQL queries.

Prerequisites:
- Docker daemon running
- Oxigraph container running (docker-compose up -d oxigraph)
- Or Oxigraph running standalone on localhost:7878

Usage:
    python tests/test_oxigraph_uploader.py
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from cimloader.databases import OxigraphConnection
from cimloader.uploaders import OxigraphUploader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_log = logging.getLogger(__name__)


def check_oxigraph_available(url: str = "http://localhost:7878/query") -> bool:
    """Check if Oxigraph is accessible.

    Args:
        url: Oxigraph query endpoint URL

    Returns:
        True if Oxigraph is responding, False otherwise
    """
    try:
        import requests
        response = requests.get(url.replace('/query', ''), timeout=5)
        return response.status_code in (200, 404)  # 404 is normal for root endpoint
    except Exception as e:
        _log.error(f"Cannot connect to Oxigraph at {url}: {e}")
        return False


def count_triples(connection: OxigraphConnection) -> int:
    """Count total number of triples in Oxigraph store.

    Args:
        connection: OxigraphConnection instance

    Returns:
        Number of triples in the store
    """
    query = """
    SELECT (COUNT(*) AS ?count)
    WHERE {
        ?s ?p ?o .
    }
    """
    result = connection.execute(query)
    count = int(result['results']['bindings'][0]['count']['value'])
    return count


def verify_cim_data(connection: OxigraphConnection) -> dict:
    """Verify CIM data was loaded by checking for common CIM classes.

    Args:
        connection: OxigraphConnection instance

    Returns:
        Dictionary with counts of various CIM object types
    """
    # Query for common CIM classes
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


def test_direct_upload():
    """Test direct upload to Oxigraph (no Docker container)."""
    _log.info("=" * 70)
    _log.info("TEST 1: Direct Upload (Oxigraph accessible from host)")
    _log.info("=" * 70)

    # Set environment variables for cimgraph
    os.environ['OXIGRAPH_URL'] = 'http://localhost:7878/query'
    os.environ['CIM_NAMESPACE'] = 'http://iec.ch/TC57/CIM100#'
    os.environ['CIM_PROFILE'] = 'RC4_2021'

    # Check if Oxigraph is available
    if not check_oxigraph_available():
        _log.error("❌ Oxigraph not available at http://localhost:7878")
        _log.info("   Start it with: docker-compose up -d oxigraph")
        return False

    try:
        # Create connection and clear existing data
        _log.info("Connecting to Oxigraph...")
        connection = OxigraphConnection()
        connection.drop_all()
        _log.info("✓ Cleared existing data")

        # Verify store is empty
        initial_count = count_triples(connection)
        _log.info(f"✓ Initial triple count: {initial_count}")

        # Upload test file
        test_file = 'test_models/ieee13_seto.xml'
        filepath = str(Path(__file__).parent / 'test_models')
        filename = 'ieee13_seto.xml'

        _log.info(f"Uploading {filename}...")
        uploader = OxigraphUploader()
        uploader.upload_from_file(filepath=filepath, filename=filename)
        _log.info("✓ Upload completed")

        # Give Oxigraph a moment to index
        time.sleep(1)

        # Count triples after upload
        final_count = count_triples(connection)
        _log.info(f"✓ Final triple count: {final_count}")

        if final_count == initial_count:
            _log.error("❌ No triples were added!")
            return False

        _log.info(f"✓ Added {final_count - initial_count} triples")

        # Verify CIM data
        _log.info("Verifying CIM data structure...")
        cim_counts = verify_cim_data(connection)
        _log.info(f"✓ Found CIM objects:")
        _log.info(f"  - Feeders: {cim_counts['feeders']}")
        _log.info(f"  - Lines: {cim_counts['lines']}")
        _log.info(f"  - Transformers: {cim_counts['transformers']}")
        _log.info(f"  - Loads: {cim_counts['loads']}")

        if sum(cim_counts.values()) == 0:
            _log.warning("⚠ No CIM objects found - data may not be structured as expected")
            return False

        _log.info("✅ Direct upload test PASSED")
        return True

    except Exception as e:
        _log.error(f"❌ Direct upload test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_container_upload():
    """Test upload via Docker container."""
    _log.info("=" * 70)
    _log.info("TEST 2: Container Upload (Docker cp method)")
    _log.info("=" * 70)

    # Check if Docker is available
    try:
        import subprocess
        result = subprocess.run(
            ['docker', 'ps'],
            capture_output=True,
            timeout=5
        )
        if result.returncode != 0:
            _log.error("❌ Docker daemon not running")
            _log.info("   Start Docker and run: docker-compose up -d oxigraph")
            return False
    except Exception as e:
        _log.error(f"❌ Cannot check Docker status: {e}")
        return False

    # Check if oxigraph container exists
    try:
        result = subprocess.run(
            ['docker', 'ps', '-a', '--filter', 'name=oxigraph', '--format', '{{.Names}}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if 'oxigraph' not in result.stdout:
            _log.error("❌ Oxigraph container 'oxigraph' not found")
            _log.info("   Start it with: docker-compose up -d oxigraph")
            return False
    except Exception as e:
        _log.error(f"❌ Cannot check container status: {e}")
        return False

    try:
        # Create connection and clear data
        _log.info("Connecting to Oxigraph...")
        connection = OxigraphConnection()
        connection.drop_all()
        _log.info("✓ Cleared existing data")

        # Upload via container
        filepath = str(Path(__file__).parent / 'test_models')
        filename = 'ieee13_seto.xml'

        _log.info(f"Uploading {filename} via Docker container...")
        uploader = OxigraphUploader(container='oxigraph_cim_loader')
        uploader.upload_from_file(filepath=filepath, filename=filename)
        _log.info("✓ Upload completed")

        # Give Oxigraph a moment to index
        time.sleep(1)

        # Verify upload
        final_count = count_triples(connection)
        _log.info(f"✓ Triple count: {final_count}")

        if final_count == 0:
            _log.error("❌ No triples were added!")
            return False

        # Verify CIM data
        cim_counts = verify_cim_data(connection)
        _log.info(f"✓ Found CIM objects:")
        _log.info(f"  - Feeders: {cim_counts['feeders']}")
        _log.info(f"  - Lines: {cim_counts['lines']}")
        _log.info(f"  - Transformers: {cim_counts['transformers']}")
        _log.info(f"  - Loads: {cim_counts['loads']}")

        _log.info("✅ Container upload test PASSED")
        return True

    except Exception as e:
        _log.error(f"❌ Container upload test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_format_detection():
    """Test automatic format detection for different RDF file types."""
    _log.info("=" * 70)
    _log.info("TEST 3: Format Detection")
    _log.info("=" * 70)

    uploader = OxigraphUploader()

    test_cases = [
        ('test.xml', 'application/rdf+xml'),
        ('test.rdf', 'application/rdf+xml'),
        ('test.ttl', 'text/turtle'),
        ('test.turtle', 'text/turtle'),
        ('test.nt', 'application/n-triples'),
        ('test.ntriples', 'application/n-triples'),
        ('test.nq', 'application/n-quads'),
        ('test.nquads', 'application/n-quads'),
    ]

    all_passed = True
    for filename, expected_type in test_cases:
        try:
            detected_type = uploader._get_content_type(filename)
            if detected_type == expected_type:
                _log.info(f"✓ {filename:20s} -> {detected_type}")
            else:
                _log.error(f"❌ {filename:20s} -> {detected_type} (expected {expected_type})")
                all_passed = False
        except Exception as e:
            _log.error(f"❌ {filename:20s} -> Error: {e}")
            all_passed = False

    # Test unsupported format
    try:
        uploader._get_content_type('test.json')
        _log.error("❌ Should have raised ValueError for unsupported format")
        all_passed = False
    except ValueError as e:
        _log.info(f"✓ Correctly rejected unsupported format: {e}")

    if all_passed:
        _log.info("✅ Format detection test PASSED")
    else:
        _log.error("❌ Format detection test FAILED")

    return all_passed


def main():
    """Run all integration tests."""
    _log.info("Oxigraph Uploader Integration Tests")
    _log.info("=" * 70)

    results = {
        'format_detection': test_format_detection(),
        'direct_upload': test_direct_upload(),
        'container_upload': test_container_upload(),
    }

    # Summary
    _log.info("")
    _log.info("=" * 70)
    _log.info("TEST SUMMARY")
    _log.info("=" * 70)
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        _log.info(f"{test_name:20s}: {status}")

    total = len(results)
    passed = sum(results.values())
    _log.info("")
    _log.info(f"Results: {passed}/{total} tests passed")

    if passed == total:
        _log.info("🎉 All tests passed!")
        return 0
    else:
        _log.error("⚠️  Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
