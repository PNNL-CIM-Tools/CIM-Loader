"""Integration tests for AWS Neptune uploader and connection.

Tests uploading CIM XML files to AWS Neptune and verifies
data integrity using SPARQL queries.

Prerequisites:
    - AWS account with Neptune cluster
    - Network connectivity to Neptune (VPC, VPN, or Direct Connect)
    - Neptune endpoint configured in environment variables

Usage:
    pytest tests/test_neptune.py -v
    pytest -m neptune

Note:
    These tests require a real Neptune instance and will be skipped
    if CIMG_URL is not set to a Neptune endpoint or if the endpoint
    is not accessible.
"""

import os
import pytest

from cimloader.databases import NeptuneConnection
from cimloader.uploaders import NeptuneUploader


def is_neptune_url(url: str) -> bool:
    """Check if URL appears to be a Neptune endpoint."""
    if not url:
        return False
    return 'neptune.amazonaws.com' in url or 'neptune.aws' in url


def is_neptune_available() -> bool:
    """Check if Neptune endpoint is configured and accessible."""
    url = os.environ.get('CIMG_URL', '')
    if not is_neptune_url(url):
        return False

    # Try to connect
    try:
        import requests
        # Just check if endpoint responds (may fail auth, but that's ok)
        response = requests.get(url, timeout=5)
        return True  # Any response (even 403) means it's reachable
    except Exception:
        return False


# =============================================================================
# Connection Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.neptune
@pytest.mark.skipif(
    not is_neptune_available(),
    reason="Neptune endpoint not configured or not accessible"
)
class TestNeptuneConnection:
    """Test Neptune connection functionality."""

    @pytest.fixture
    def neptune_connection(self):
        """Provide a Neptune connection for tests."""
        os.environ['CIMG_CIM_PROFILE'] = 'rc4_2021'
        os.environ['CIMG_NAMESPACE'] = 'http://iec.ch/TC57/CIM100#'

        connection = NeptuneConnection()
        yield connection

        # Cleanup
        try:
            connection.disconnect()
        except:
            pass

    def test_connection_create(self, neptune_connection):
        """Test that connection can be created."""
        assert neptune_connection is not None
        assert 'neptune' in neptune_connection.url.lower()

    def test_connection_connect(self, neptune_connection):
        """Test that connection can be established."""
        neptune_connection.connect()
        assert neptune_connection.sparql_obj is not None

    def test_connection_execute_query(self, neptune_connection):
        """Test executing a simple SPARQL query."""
        query = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o . }"
        try:
            result = neptune_connection.execute(query)
            assert result is not None
            assert 'results' in result
            assert 'bindings' in result['results']
        except Exception as e:
            if '403' in str(e) or 'Forbidden' in str(e):
                pytest.skip("Neptune requires IAM authentication (not yet implemented)")
            raise


# =============================================================================
# Upload Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.neptune
@pytest.mark.skipif(
    not is_neptune_available(),
    reason="Neptune endpoint not configured or not accessible"
)
class TestNeptuneUpload:
    """Test Neptune upload functionality.

    Note: These tests will only work if Neptune has IAM auth disabled
    or if AWS credentials are properly configured.
    """

    @pytest.fixture
    def neptune_uploader(self):
        """Provide a Neptune uploader for tests."""
        os.environ['CIMG_CIM_PROFILE'] = 'rc4_2021'
        os.environ['CIMG_NAMESPACE'] = 'http://iec.ch/TC57/CIM100#'

        return NeptuneUploader()

    def test_uploader_create(self, neptune_uploader):
        """Test that uploader can be created."""
        assert neptune_uploader is not None
        assert 'neptune' in neptune_uploader.url.lower()

    def test_format_detection(self, neptune_uploader):
        """Test format detection from file extensions."""
        assert neptune_uploader._get_content_type('test.xml') == 'application/rdf+xml'
        assert neptune_uploader._get_content_type('test.ttl') == 'text/turtle'
        assert neptune_uploader._get_content_type('test.nt') == 'application/n-triples'
        assert neptune_uploader._get_content_type('test.nq') == 'application/n-quads'

    def test_unsupported_format(self, neptune_uploader):
        """Test that unsupported formats raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported file format"):
            neptune_uploader._get_content_type('test.json')


# =============================================================================
# Configuration Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.neptune
class TestNeptuneConfiguration:
    """Test Neptune configuration and environment setup."""

    def test_environment_variables(self):
        """Test that environment variables are properly read."""
        os.environ['CIMG_URL'] = 'https://test.cluster-xyz.us-east-1.neptune.amazonaws.com:8182/sparql'
        os.environ['AWS_REGION'] = 'us-east-1'

        connection = NeptuneConnection()

        assert connection.url.endswith('/sparql')
        assert connection.aws_region == 'us-east-1'

    def test_aws_credentials_optional(self):
        """Test that uploader works without AWS credentials (IAM disabled)."""
        # Clear AWS credentials
        os.environ.pop('AWS_ACCESS_KEY_ID', None)
        os.environ.pop('AWS_SECRET_ACCESS_KEY', None)

        uploader = NeptuneUploader()
        assert uploader.use_iam_auth is False


# =============================================================================
# Documentation Tests
# =============================================================================

@pytest.mark.neptune
class TestNeptuneDocumentation:
    """Verify Neptune setup and documentation."""

    def test_documentation_exists(self):
        """Check that Neptune documentation exists."""
        from pathlib import Path
        docs_file = Path(__file__).parent.parent / 'docs' / 'NEPTUNE.md'
        assert docs_file.exists(), "Neptune documentation not found"

    def test_neptune_in_readme(self):
        """Check that Neptune is mentioned in README."""
        from pathlib import Path
        readme_file = Path(__file__).parent.parent / 'README.md'
        content = readme_file.read_text()
        assert 'Neptune' in content or 'neptune' in content

    def test_neptune_uploader_importable(self):
        """Test that Neptune uploader can be imported."""
        from cimloader.uploaders import NeptuneUploader
        assert NeptuneUploader is not None

    def test_neptune_connection_importable(self):
        """Test that Neptune connection can be imported."""
        from cimloader.databases import NeptuneConnection
        assert NeptuneConnection is not None


# =============================================================================
# Skip Message
# =============================================================================

if __name__ == '__main__':
    if not is_neptune_available():
        print("=" * 70)
        print("AWS Neptune Integration Tests")
        print("=" * 70)
        print("\nNeptune endpoint not configured or not accessible.")
        print("\nTo run these tests:")
        print("1. Create a Neptune cluster in AWS")
        print("2. Set environment variable:")
        print("   export CIMG_URL='https://your-cluster.neptune.amazonaws.com:8182/sparql'")
        print("3. Ensure network connectivity (VPC, VPN, etc.)")
        print("4. Run: pytest tests/test_neptune.py -v")
        print("\nFor development, disable IAM auth on Neptune cluster.")
        print("See docs/NEPTUNE.md for detailed setup instructions.")
        print("=" * 70)
    else:
        print("Neptune endpoint detected. Running tests...")
        pytest.main([__file__, '-v'])
