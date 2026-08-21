# CIM-Loader
Automated scripts for 
* uploading and downloading CIM files from various databases
* converting CIM files between common formats (XML, TTL, etc.)

## Installation
The library can be pip installed from PyPi using
`pip install cim-loader`

To install a specific branch, clone the repo and install it using
```bash
git clone https://github.com/PNNL-CIM-Tools/CIM-Loader.git -b develop
pip install -e CIM-Loader
```

## Usage

CIM-Loader provides a consistent API for uploading CIM data to various databases. All uploaders support multiple RDF formats and can transfer data between databases using CIMantic Graphs.

### Basic File Upload

All uploaders use a consistent API: `upload_from_file(filepath, filename)`

```python
import os
from cimloader.uploaders import BlazegraphUploader

# Configure via environment variables
os.environ['CIMG_URL'] = 'http://localhost:8889/bigdata/namespace/kb/sparql'

# Create uploader and upload file
loader = BlazegraphUploader()
loader.upload_from_file(filepath='./test_models', filename='ieee13_seto.xml')
```

### Example: Upload to Different Databases

```python
import os

# Blazegraph
os.environ['CIMG_URL'] = 'http://localhost:8889/bigdata/namespace/kb/sparql'
from cimloader.uploaders import BlazegraphUploader
blazegraph = BlazegraphUploader()
blazegraph.upload_from_file(filepath='./models', filename='grid.xml')

# Neo4j
os.environ['CIMG_URL'] = 'neo4j://localhost:7687'
os.environ['CIMG_USERNAME'] = 'neo4j'
os.environ['CIMG_PASSWORD'] = 'password'
from cimloader.uploaders import Neo4jUploader
neo4j = Neo4jUploader()
neo4j.upload_from_file(filepath='./models', filename='grid.xml')

# Oxigraph
os.environ['CIMG_URL'] = 'http://localhost:7878/query'
from cimloader.uploaders import OxigraphUploader
oxigraph = OxigraphUploader()
oxigraph.upload_from_file(filepath='./models', filename='grid.xml')
```

### Database Migration

Transfer data between databases using CIMantic Graphs:

```python
from cimgraph.models import FeederModel
from cimgraph.databases import BlazegraphConnection
from cimloader.uploaders import Neo4jUploader
import cimgraph.data_profile.rc4_2021 as cim

# Load from Blazegraph
os.environ['CIMG_URL'] = 'http://localhost:8889/bigdata/namespace/kb/sparql'
blazegraph = BlazegraphConnection()
feeder = cim.Feeder(mRID='feeder-123')
source = FeederModel(container=feeder, connection=blazegraph)

# Upload to Neo4j
os.environ['CIMG_URL'] = 'neo4j://localhost:7687'
neo4j = Neo4jUploader()
neo4j.upload_from_graphmodel(source.graph)
```

See the `examples/` directory for complete migration and merging examples.

### Format Support

Format is auto-detected from the file extension. Pass any of the supported
extensions to `upload_from_file`:

- **RDF/XML** — `.xml`, `.rdf`
- **Turtle** — `.ttl`, `.turtle`
- **N-Triples** — `.nt`, `.ntriples`
- **N-Quads** — `.nq`, `.nquads`
- **JSON-LD** — `.jsonld`, `.json-ld` (Blazegraph, Neo4j)
- **TriG** — `.trig` (Blazegraph, Neo4j)

```python
uploader.upload_from_file(filepath='./models', filename='grid.xml')
uploader.upload_from_file(filepath='./models', filename='grid.ttl')
```

See `design/UPLOADER_API.md` for full API details and
`design/STYLE_GUIDE.md` for coding conventions.


## Databases Supported
Currently supported:
* Blazegraph
* Neo4j
* Oxigraph
* AWS Neptune (experimental — see `docs/NEPTUNE.md`)

Planned (see `design/TODO.md`):
* Apache AGE (PostgreSQL graph extension — replacing the legacy MySQL connector)
* GraphDB

Support may be added in the future for:
* Apache Tinkerpop
* SQlite
* AVEVA PI Historian
* Others as requested

## Testing

CIM-Loader uses pytest for integration testing. Tests verify functionality against real database instances running in Docker containers.

### Setup Test Environment

1. Install test dependencies:
```bash
pip install -e ".[test]"
```

2. Start database services:
```bash
docker-compose up -d
```

This starts all database services:
- Blazegraph on port 8889
- Neo4j on ports 7474 (HTTP) and 7687 (Bolt)
- Oxigraph on port 7878

### Running Tests

Run all integration tests:
```bash
pytest tests/ -v
```

Run tests for a specific database:
```bash
pytest tests/test_blazegraph.py -v
pytest tests/test_neo4j.py -v
pytest tests/test_oxigraph.py -v
pytest tests/test_mysql.py -v
```

Run tests using markers:
```bash
pytest -m blazegraph -v
pytest -m neo4j -v
pytest -m oxigraph -v
pytest -m mysql -v
```

Skip slow tests:
```bash
pytest -m "not slow" -v
```

Run with coverage report:
```bash
pytest --cov=cimloader --cov-report=html
```

### Test Organization

- `tests/conftest.py` - Shared fixtures and test configuration
- `tests/test_blazegraph.py` - Blazegraph triplestore tests
- `tests/test_neo4j.py` - Neo4j graph database tests
- `tests/test_oxigraph.py` - Oxigraph triplestore tests
- `tests/test_mysql.py` - MySQL relational database tests
- `tests/test_models/` - Sample CIM XML files for testing

### CI/CD

Tests can be integrated into CI/CD pipelines. Make sure Docker is available and services are started before running tests.

Example GitHub Actions workflow:
```yaml
- name: Start services
  run: docker-compose up -d
- name: Wait for services
  run: sleep 10
- name: Run tests
  run: pytest tests/ -v
```


## Attribution and Disclaimer

This software was created under a project sponsored by the U.S. Department of Energy’s Office of Electricity, an agency of the United States Government.  Neither the United States Government nor the United States Department of Energy, nor Battelle, nor any of their employees, nor any jurisdiction or organization that has cooperated in the development of these materials, makes any warranty, express or implied, or assumes any legal liability or responsibility for the accuracy, completeness, or usefulness or any information, apparatus, product, software, or process disclosed, or represents that its use would not infringe privately owned rights.

Reference herein to any specific commercial product, process, or service by trade name, trademark, manufacturer, or otherwise does not necessarily constitute or imply its endorsement, recommendation, or favoring by the United States Government or any agency thereof, or Battelle Memorial Institute. The views and opinions of authors expressed herein do not necessarily state or reflect those of the United States Government or any agency thereof.

PACIFIC NORTHWEST NATIONAL LABORATORY
operated by
BATTELLE
for the
UNITED STATES DEPARTMENT OF ENERGY
under Contract DE-AC05-76RL01830


