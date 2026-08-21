# CIM-Loader Test Suite

This directory contains the integration test suite for CIM-Loader.

## Overview

The test suite uses **pytest** to run integration tests against real database instances. All tests require Docker containers to be running.

## Test Structure

### Test Files

| File | Description | Database |
|------|-------------|----------|
| `conftest.py` | Shared fixtures and test configuration | All |
| `test_blazegraph.py` | Blazegraph triplestore integration tests | Blazegraph |
| `test_neo4j.py` | Neo4j graph database integration tests | Neo4j |
| `test_oxigraph.py` | Oxigraph triplestore integration tests | Oxigraph |
| `test_mysql.py` | MySQL relational database integration tests | MySQL |

### Test Data

- `test_models/` - Sample CIM XML files used in tests
  - `ieee13_seto.xml` - IEEE 13-bus SETO model
  - `ieee13_2021.xml` - IEEE 13-bus 2021 model

### Legacy Files (Deprecated)

The following files are legacy test files that have been replaced by the pytest suite:
- `blazegraph_tester.ipynb` - Use `test_blazegraph.py` instead
- `neo4j_tester.ipynb` - Use `test_neo4j.py` instead
- `mysql_test.ipynb` - Use `test_mysql.py` instead
- `test_oxigraph_uploader.py` - Refactored into `test_oxigraph.py`
- `quick_test_oxigraph.py` - Kept for manual testing

## Quick Start

1. **Install test dependencies:**
   ```bash
   pip install -e ".[test]"
   ```

2. **Start Docker services:**
   ```bash
   cd /path/to/CIM-Loader
   docker-compose up -d
   ```

3. **Run all tests:**
   ```bash
   pytest tests/ -v
   ```

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_blazegraph.py -v
pytest tests/test_neo4j.py -v
pytest tests/test_oxigraph.py -v
pytest tests/test_mysql.py -v
```

### Run by Marker
```bash
# Run only Blazegraph tests
pytest -m blazegraph -v

# Run only Neo4j tests
pytest -m neo4j -v

# Run only Oxigraph tests
pytest -m oxigraph -v

# Run only MySQL tests
pytest -m mysql -v

# Run only integration tests
pytest -m integration -v
```

### Run Specific Test
```bash
# Run a specific test class
pytest tests/test_blazegraph.py::TestBlazegraphConnection -v

# Run a specific test method
pytest tests/test_blazegraph.py::TestBlazegraphConnection::test_connection_create -v
```

### Skip Slow Tests
```bash
pytest -m "not slow" -v
```

### Run with Coverage
```bash
# Terminal output
pytest --cov=cimloader --cov-report=term-missing

# HTML report
pytest --cov=cimloader --cov-report=html
open htmlcov/index.html
```

## Test Markers

Tests are organized using pytest markers:

| Marker | Description |
|--------|-------------|
| `integration` | Integration tests requiring external services |
| `blazegraph` | Blazegraph-specific tests |
| `neo4j` | Neo4j-specific tests |
| `oxigraph` | Oxigraph-specific tests |
| `mysql` | MySQL-specific tests |
| `slow` | Tests that take significant time to run |
| `requires_docker` | Tests that require Docker daemon |

## Test Fixtures

Common fixtures are defined in `conftest.py`:

### Environment Configuration
- `setup_test_environment` - Sets common environment variables
- `blazegraph_env` - Configures Blazegraph environment
- `neo4j_env` - Configures Neo4j environment
- `mysql_env` - Configures MySQL environment
- `oxigraph_env` - Configures Oxigraph environment

### Database Connections
- `blazegraph_connection` - Provides clean Blazegraph connection
- `neo4j_connection` - Provides clean Neo4j connection with n10s configured
- `mysql_connection` - Provides MySQL connection with schema created
- `oxigraph_connection` - Provides clean Oxigraph connection

### Uploaders
- `blazegraph_uploader` - Blazegraph uploader instance
- `neo4j_uploader` - Neo4j uploader instance (with container support)
- `oxigraph_uploader` - Oxigraph uploader instance

### Test Data
- `test_model_path` - Path to test models directory
- `ieee13_seto_file` - Path to IEEE 13 SETO model
- `ieee13_2021_file` - Path to IEEE 13 2021 model

## Docker Services

The test suite requires the following Docker services from `docker-compose.yml`:

| Service | Container Name | Ports | Purpose |
|---------|---------------|-------|---------|
| blazegraph | blazegraph | 8889 | SPARQL triplestore |
| neo4j-apoc | neo4j-apoc | 7474, 7687 | Graph database with n10s |
| oxigraph | oxigraph | 7878 | RDF triplestore |
| mysql | mysql_json | 3306 | Relational database |

### Service Health Checks

Tests automatically check if services are running and skip if unavailable. To verify services:

```bash
# Check all containers
docker-compose ps

# Check specific service
docker ps | grep blazegraph
docker ps | grep neo4j
docker ps | grep oxigraph
docker ps | grep mysql
```

### Service Logs

View logs if tests fail:

```bash
docker-compose logs blazegraph
docker-compose logs neo4j-apoc
docker-compose logs oxigraph
docker-compose logs mysql
```

## Test Categories

### Connection Tests
- Verify database connections can be established
- Test authentication and configuration
- Test connection lifecycle (connect/disconnect)

### Upload Tests
- Test uploading CIM XML files
- Verify data integrity after upload
- Test multiple upload scenarios
- Test different file formats (Oxigraph)

### Query Tests
- Test SPARQL queries (Blazegraph, Oxigraph)
- Test Cypher queries (Neo4j)
- Test SQL queries (MySQL)
- Verify CIM data structure

### Error Handling Tests
- Test handling of invalid inputs
- Test handling of nonexistent files
- Test handling of invalid queries
- Test recovery from errors

## Troubleshooting

### Tests Are Skipped

If tests are being skipped, check:

1. **Docker daemon is running:**
   ```bash
   docker ps
   ```

2. **Services are started:**
   ```bash
   docker-compose up -d
   ```

3. **Ports are not blocked:**
   ```bash
   netstat -an | grep 8889  # Blazegraph
   netstat -an | grep 7687  # Neo4j
   netstat -an | grep 7878  # Oxigraph
   netstat -an | grep 3306  # MySQL
   ```

### Tests Fail

If tests fail:

1. **Check service logs:**
   ```bash
   docker-compose logs [service-name]
   ```

2. **Restart services:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

3. **Clear data volumes:**
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

4. **Run tests in verbose mode:**
   ```bash
   pytest tests/ -vv -s
   ```

### Permission Errors (Docker)

If you get permission errors with Docker:

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Re-login for group changes to take effect
newgrp docker
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -e ".[test]"

      - name: Start services
        run: |
          docker-compose up -d
          sleep 15  # Wait for services to be ready

      - name: Run tests
        run: |
          pytest tests/ -v --cov=cimloader

      - name: Stop services
        if: always()
        run: docker-compose down
```

## Writing New Tests

When adding new tests:

1. **Use appropriate markers:**
   ```python
   @pytest.mark.integration
   @pytest.mark.blazegraph
   def test_new_feature(blazegraph_connection):
       pass
   ```

2. **Use fixtures for setup/teardown:**
   ```python
   def test_upload(blazegraph_uploader, blazegraph_connection, test_model_path):
       # Test automatically has clean database
       pass
   ```

3. **Follow naming conventions:**
   - Test files: `test_*.py`
   - Test classes: `Test*`
   - Test methods: `test_*`

4. **Add docstrings:**
   ```python
   def test_upload_file(self, uploader, connection):
       """Test uploading a CIM XML file to the database."""
       pass
   ```

5. **Use assertions with messages:**
   ```python
   assert count > 0, "Should have uploaded some triples"
   ```

## Performance Testing

For performance benchmarking:

```bash
# Run with timing information
pytest tests/ -v --durations=10

# Run only slow tests
pytest -m slow -v
```

## Questions?

For questions or issues with tests:
1. Check this README
2. Review test code in `conftest.py`
3. Open an issue on GitHub
