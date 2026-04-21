# Uploader API

All CIM-Loader uploaders share the same public API. Format is auto-detected
from the file extension (or the URL path extension for `upload_from_url`).

## Public methods

```python
uploader.upload_from_file(filepath: str, filename: str) -> None
uploader.upload_from_url(url: str) -> None
uploader.upload_from_graphmodel(graph_dict: dict, feeder_mrid: str | None = None) -> None
```

Uploaders inherit from their corresponding `Connection` class, so they also
expose `connect`, `disconnect`, `execute`, `configure`, `drop_all`.

## Extension → content type mapping

Single source of truth: `cimloader/_formats.py`.

| Extension(s) | Content type |
|--------------|--------------|
| `.xml`, `.rdf` | `application/rdf+xml` |
| `.ttl`, `.turtle` | `text/turtle` |
| `.nt`, `.ntriples` | `application/n-triples` |
| `.nq`, `.nquads` | `application/n-quads` |
| `.jsonld`, `.json-ld` | `application/ld+json` |
| `.trig` | `application/trig` |

Unknown extensions raise `ValueError` at upload time.

## Uploader specifics

### BlazegraphUploader
- `upload_from_file` uploads via `curl` POST to the SPARQL endpoint.
- `upload_from_url` fetches with `requests.get` then POSTs the bytes.
- No constructor arguments.

### Neo4jUploader
- `upload_from_file` / `upload_from_url` both call the `n10s.rdf.import.fetch`
  Cypher procedure. The URL variant passes the URL straight through to n10s
  rather than downloading locally first.
- Optional `container="<name>"` constructor arg `docker cp`s files into
  the Neo4j container — use this when the DB is in Docker but the file is
  on the host. (Irrelevant for `upload_from_url`, which n10s fetches itself.)
- Neo4j requires `uploader.configure()` to be called once per database.

### OxigraphUploader
- `upload_from_file` uploads via HTTP POST to `<base>/store`.
- `upload_from_url` fetches with `requests.get` then POSTs to the same endpoint.
- Optional `container="<name>"` constructor arg behaves the same as Neo4j's.
- Handles both `http://host:port` and `http://host:port/query` in `CIMG_URL`.

### NeptuneUploader
- `upload_from_file` uploads via `curl` POST to the SPARQL endpoint.
- `upload_from_url` fetches with `requests.get` then POSTs the bytes.
- AWS SigV4 auth and S3 bulk loading are planned (see `design/TODO.md`);
  today the uploader only works against IAM-disabled Neptune clusters.

## Basic usage

```python
import os
from cimloader.uploaders import BlazegraphUploader

os.environ['CIMG_URL'] = 'http://localhost:8889/bigdata/namespace/kb/sparql'
os.environ['CIMG_CIM_PROFILE'] = 'rc4_2021'
os.environ['CIMG_NAMESPACE'] = 'http://iec.ch/TC57/CIM100#'

uploader = BlazegraphUploader()
uploader.upload_from_file('./models', 'ieee13.xml')
uploader.upload_from_file('./models', 'ieee13.ttl')  # same method, different format

# Or straight from a raw URL (e.g. GitHub raw):
uploader.upload_from_url(
    'https://raw.githubusercontent.com/PNNL-CIM-Tools/CIM-Loader/main/tests/test_models/ieee13_seto.xml'
)
```

## Database migration (GraphModel)

All four uploaders accept a CIMantic Graphs `GraphModel.graph` dict. This
is the canonical way to move data between databases:

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

Merging multiple feeders: chain `FeederModel(graph=previous.graph)` calls,
then upload the final graph once.

## Format compatibility

| Format | Blazegraph | Neo4j | Oxigraph | Neptune |
|--------|-----------|-------|----------|---------|
| RDF/XML  | ✅ | ✅ | ✅ | ✅ |
| Turtle   | ✅ | ✅ | ✅ | ✅ |
| N-Triples | ✅ | ✅ | ✅ | ✅ |
| N-Quads  | ✅ | ✅ | ✅ | ✅ |
| JSON-LD  | ✅ | ✅ | ❌ | ⚠️ |
| TriG     | ✅ | ✅ | ❌ | ⚠️ |

⚠️ = SPARQL 1.1 supports it, but it hasn't been verified end-to-end.

## Error handling

- Unknown file extension → `ValueError` (from `content_type_from_filename`)
- Curl / n10s / HTTP failures → `subprocess.CalledProcessError` or Neo4j
  driver exceptions bubble up — they are not caught by the uploader.
- Missing CIM profile when calling `upload_from_graphmodel` → `RuntimeError`.
