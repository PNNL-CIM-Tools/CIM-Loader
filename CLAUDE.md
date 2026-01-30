# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CIM-Loader is a Python library for uploading/downloading CIM (Common Information Model) files to various databases and converting between CIM formats (XML, TTL). It's designed for power grid modeling and supports multiple graph databases and SPARQL endpoints.

**Key dependency:** This project heavily relies on `cim-graph` (separate package) for CIM profile definitions, namespace configuration, and environment variable management via cached functions like `get_url()`, `get_namespace()`, `get_cim_profile()`, etc.

## Development Setup

### Installation
```bash
# Install for development (editable mode)
git clone https://github.com/PNNL-CIM-Tools/CIM-Loader.git
cd CIM-Loader
pip install -e .

# Or from PyPI
pip install cim-loader
```

### Environment Setup
This project uses uv for fast dependency management:
```bash
# Install uv if you don't have it
pip install uv

# Install dependencies
uv pip install -e .

# Install with dev dependencies
uv pip install -e ".[dev]"
```

Python version: >=3.10

### Running Tests
Tests are Jupyter notebooks in the `tests/` directory:
- `tests/blazegraph_tester.ipynb` - Blazegraph upload/download tests
- `tests/neo4j_tester.ipynb` - Neo4j upload/download tests
- `tests/mysql_test.ipynb` - MySQL tests
- Test models are in `tests/test_models/`

Run test notebooks using Jupyter:
```bash
jupyter notebook tests/
```

### Docker Services
Start database services for testing:
```bash
docker-compose up -d

# Services available:
# - Blazegraph: http://localhost:8889
# - Neo4j: http://localhost:7474 (bolt://localhost:7687)
# - GraphDB: http://localhost:7200
# - MySQL: localhost:3306
```

## Architecture

### Core Design Pattern
The codebase follows a layered architecture:

1. **Connection Layer** (`cimloader/databases/`): Implements `ConnectionInterface` base class
   - Each database has a connection class (e.g., `BlazegraphConnection`, `Neo4jConnection`)
   - Manages connection lifecycle: `connect()`, `disconnect()`, `execute(query)`
   - Uses environment variables from `cim-graph` for configuration

2. **Uploader Layer** (`cimloader/uploaders/`): Inherits from corresponding connection class
   - Implements database-specific upload methods
   - Methods: `upload_from_file()`, `upload_from_xml()`, `upload_from_url()`
   - Handles format conversion (XML, TTL, RDF/XML)

3. **Downloader Layer** (`cimloader/downloaders/`): Database-specific download implementations
   - Queries and exports CIM data from databases

4. **Batch Handlers** (`cimloader/batch_handlers/`): Orchestrates multi-step workflows
   - Example: `naerm_to_neo4j.py` - downloads from NAERM API, converts DSS to CIM, uploads to Neo4j
   - Combines multiple components for complex ETL pipelines

### Environment Variable Pattern
All database connections use `cim-graph` cached functions for configuration:
```python
from cimgraph.databases import get_url, get_namespace, get_cim_profile, get_username, get_password

# Pattern: Always clear cache in __init__ before retrieving values
get_url.cache_clear()
get_namespace.cache_clear()
# ... then retrieve
self.url = get_url()
self.namespace = get_namespace()
```

This allows configuration via environment variables or programmatic override.

### Database-Specific Notes

**Blazegraph**: SPARQL endpoint, uses `SPARQLWrapper`
- Upload uses `curl` subprocess calls
- Connection URL format: `http://localhost:8889/bigdata/namespace/kb/sparql`

**Neo4j**: Graph database with n10s RDF plugin
- Requires n10s configuration: `configure()` must be called before first upload
- Uses `n10s.rdf.import.fetch()` for RDF imports
- Supports docker container file transfers for imports
- Connection URL format: `neo4j://localhost:7687`

**MySQL**: Relational database (less common for CIM, mainly for structured queries)

**GraphDB**: RDF triplestore (connection implemented but uploader/downloader may be incomplete)

## Common Operations

### Upload CIM file to Blazegraph
```python
from cimloader.uploaders import BlazegraphUploader

loader = BlazegraphUploader()  # Uses env vars from cim-graph
loader.upload_from_xml(filename='model.xml')
```

### Upload CIM file to Neo4j
```python
from cimloader.uploaders import Neo4jUploader

loader = Neo4jUploader(container='neo4j')  # Optional: container name for docker cp
loader.upload_from_file(filename='model.xml', filepath='./models')
```

### Query a database
```python
from cimloader.databases import BlazegraphConnection

conn = BlazegraphConnection()
result = conn.execute("SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10")
```

## Module Structure

- `cimloader/databases/` - Database connection interfaces (Blazegraph, Neo4j, MySQL)
- `cimloader/uploaders/` - Upload implementations for each database
- `cimloader/downloaders/` - Download implementations for each database
- `cimloader/batch_handlers/` - Multi-step ETL workflows
- `cimloader/serializations/` - Format conversion utilities (encoders, translators)
