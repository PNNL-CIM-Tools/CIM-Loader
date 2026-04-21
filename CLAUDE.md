# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project Overview

CIM-Loader is a Python library for uploading CIM (Common Information Model)
files into various graph databases / SPARQL endpoints, and for moving CIM
data between them. It's designed for power grid modeling.

**Key dependency:** `cim-graph` — provides CIM profile definitions, namespace
configuration, and env-variable-backed getters like `get_url()`,
`get_namespace()`, `get_cim_profile()`.

## Development Setup

```bash
# Editable install for development
git clone https://github.com/PNNL-CIM-Tools/CIM-Loader.git
cd CIM-Loader
uv pip install -e ".[dev]"
```

Python: >= 3.10. This project uses `uv`.

### Running Tests

Tests are pytest integration tests that hit real databases in Docker:

```bash
docker-compose up -d
pytest tests/ -v
# or per-database:
pytest tests/test_blazegraph.py -v
pytest tests/test_neo4j.py -v
pytest tests/test_oxigraph.py -v
pytest tests/test_neptune.py -v
```

Test models live in `tests/test_models/`.

### Docker Services

```bash
docker-compose up -d
# - Blazegraph: http://localhost:8889
# - Neo4j:      http://localhost:7474  (bolt://localhost:7687)
# - Oxigraph:   http://localhost:7878
```

## Architecture

Layered:

1. **`cimloader/databases/`** — Connection classes. All implement the
   `ConnectionInterface` ABC (`connect`, `disconnect`, `execute`). One file
   per database: `blazegraph.py`, `neo4j.py`, `oxigraph.py`, `neptune.py`.
   Base class lives in `_base.py`; shared cimgraph-cache-clearing helper in
   `_config_utils.py`.

2. **`cimloader/uploaders/`** — Each uploader inherits from its Connection
   class via `super().__init__()`. Public API on every uploader:
   - `upload_from_file(filepath, filename)` — auto-detects RDF format from
     the extension via `cimloader._formats.content_type_from_filename`.
   - `upload_from_graphmodel(graph_dict, feeder_mrid=None)` — upload from a
     CIMantic Graphs `GraphModel.graph` dict.

3. **`cimloader/downloaders/`** — Currently empty. Use connection
   `execute()` for ad-hoc queries.

4. **`cimloader/batch_handlers/`** — Placeholder for multi-profile CIM
   package workflows (EQ + TP + SSH append). Not implemented yet.

5. **`archive/`** — Frozen snapshots of legacy code (MySQL, GraphDB stubs,
   NAERM). Not imported by the active package. See each subfolder's README.

6. **`design/`** — Internal design docs: `STYLE_GUIDE.md`, `MIGRATION.md`,
   `UPLOADER_API.md`, `TODO.md`. Future Claude prompts go here too.

### Environment Variable Pattern

All connections clear cimgraph's `@lru_cache`d getters in `__init__`, then
read them:

```python
from cimloader.databases._config_utils import clear_cim_config_cache
from cimgraph.databases import get_url, get_namespace

clear_cim_config_cache()
self.url = get_url()
self.namespace = get_namespace()
```

This lets callers override config by setting env vars before instantiation.

### Database-Specific Notes

**Blazegraph** — SPARQL endpoint via `SPARQLWrapper`. Upload via `curl`
POST. URL: `http://localhost:8889/bigdata/namespace/kb/sparql`.

**Neo4j** — Graph DB with the n10s RDF plugin. `configure()` must be called
once to set up n10s. Uploads use `n10s.rdf.import.fetch`. Optional
`container="<name>"` constructor arg copies files into the Docker container
before import. URL: `neo4j://localhost:7687`.

**Oxigraph** — Lightweight SPARQL 1.1 triplestore. REST API via HTTP POST
to `/store`. Optional container arg works like Neo4j's. Handles both
`http://host:port` and `http://host:port/query` forms in `CIMG_URL`.

**Neptune** — AWS managed SPARQL. Currently works only against
IAM-disabled clusters; AWS SigV4 and S3 bulk load are planned (see
`design/TODO.md`).

## Common Operations

### Upload a file

```python
from cimloader.uploaders import BlazegraphUploader

loader = BlazegraphUploader()
loader.upload_from_file(filepath='./models', filename='model.xml')
loader.upload_from_file(filepath='./models', filename='model.ttl')
```

Format is auto-detected. Unknown extensions raise `ValueError`.

### Migrate between databases

```python
from cimgraph.databases import BlazegraphConnection
from cimgraph.models import FeederModel
from cimloader.uploaders import Neo4jUploader
import cimgraph.data_profile.rc4_2021 as cim

source = FeederModel(
    container=cim.Feeder(mRID='feeder-123'),
    connection=BlazegraphConnection(),
)
target = Neo4jUploader(container='neo4j_cim_loader')
target.configure()
target.upload_from_graphmodel(source.graph, feeder_mrid='feeder-123')
```

### Run a SPARQL query

```python
from cimloader.databases import BlazegraphConnection
conn = BlazegraphConnection()
result = conn.execute("SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10")
```

## Pointers

- Full uploader API reference: `design/UPLOADER_API.md`
- Breaking changes history: `design/MIGRATION.md`
- Coding style: `design/STYLE_GUIDE.md`
- Planned future work: `design/TODO.md`
- Neptune-specific setup: `docs/NEPTUNE.md`
- Reference examples: `examples/migrate_database.py`, `examples/neptune_example.py`
