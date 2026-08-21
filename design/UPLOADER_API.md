# Uploader API

All CIM-Loader uploaders share the same public API. Format is auto-detected
from the file extension (or the URL path extension for `upload_from_url`).

## Public methods

```python
uploader.upload_from_file(filepath: str, filename: str) -> None
uploader.upload_from_url(url: str) -> None
uploader.upload_from_graphmodel(graph_dict: dict) -> None
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

## Base IRI normalization

Every uploader accepts a `base_iri` constructor argument (default
`http://gridappsd.org/cim/`). CIM RDF/XML files routinely use
`rdf:ID="_UUID"` / `rdf:resource="#_UUID"` without declaring a document
base, which strict parsers (Oxigraph, Jena) reject. Before upload, RDF/XML
bytes are rewritten to carry `xml:base="<base_iri>"` on the root element
if one isn't already present — so all four databases produce identical
triples from the same input file. Files that already declare `xml:base`
are left untouched. Non-RDF/XML formats pass through unchanged.

## Uploader specifics

### BlazegraphUploader
- `upload_from_file` / `upload_from_url` both POST via `requests` to the
  SPARQL endpoint after base-IRI normalization.
- Constructor: `base_iri=DEFAULT_BASE_IRI`.

### Neo4jUploader
- `upload_from_file` / `upload_from_url` read the bytes in-process, apply
  base-IRI normalization, stage to a tempfile, then call
  `n10s.rdf.import.fetch` with a `file://` URL.
- Optional `container="<name>"` constructor arg `docker cp`s the rewritten
  bytes into the container's import dir (and chmods them readable) — use
  this when Neo4j runs in Docker but the uploader runs on the host.
- Constructor: `container=None, base_iri=DEFAULT_BASE_IRI`.
- Neo4j requires `uploader.configure()` to be called once per database.

### OxigraphUploader
- `upload_from_file` / `upload_from_url` POST via `requests` to
  `<base>/store?default` (the `?default` ensures triples land in the
  default graph instead of a fresh named graph per request).
- Handles both `http://host:port` and `http://host:port/query` in `CIMG_URL`.
- Constructor: `base_iri=DEFAULT_BASE_IRI`.

### NeptuneUploader
- `upload_from_file` / `upload_from_url` POST via `requests` to the SPARQL
  endpoint after base-IRI normalization.
- Constructor: `base_iri=DEFAULT_BASE_IRI`.
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
target.upload_from_graphmodel(source.graph)
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
- HTTP / n10s / `docker cp` failures → `requests.HTTPError`, Neo4j driver
  exceptions, or `subprocess.CalledProcessError` bubble up — the uploader
  does not catch them.
- `upload_from_graphmodel` accepts the `graph` dict of any `GraphModel`
  subclass (`FeederModel`, `BusBranchModel`, `NodeBreakerModel`). SPARQL
  backends emit `INSERT DATA` per object; Neo4j delegates to cimgraph's
  n10s-based `Neo4jConnection.upload()`.
