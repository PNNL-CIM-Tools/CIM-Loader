# API Migration Notes

History of breaking API changes. For the current API, see `UPLOADER_API.md`.

## 2026-08: `upload_from_graphmodel` fixed; `feeder_mrid` removed (breaking)

`upload_from_graphmodel` never worked on any backend. Every uploader ended with
`FeederModel(container=..., connection=self, graph=graph_dict)` and discarded
the result — but constructing a `GraphModel` is a database *read*
(`__post_init__` calls `connection.create_new_graph()`), so nothing was written.
It raised `AttributeError: no attribute 'create_new_graph'`.

**Fixed:** SPARQL backends (Blazegraph / Oxigraph / Neptune / GraphDB) now emit
`INSERT DATA` per object via a shared helper. Neo4j delegates to cimgraph's
`Neo4jConnection.upload()`, which serializes to RDF/XML and ingests through
`n10s.rdf.import.inline`.

**Removed:** the `feeder_mrid` parameter. It only fed the bogus container
construction. Dropping it makes the method work for any `GraphModel` subclass —
`BusBranchModel` and `NodeBreakerModel` for transmission, not just
`FeederModel`.

```python
# Old (raised AttributeError)
uploader.upload_from_graphmodel(network.graph, feeder_mrid='feeder-123')

# New
uploader.upload_from_graphmodel(network.graph)
```

`BlazegraphUploader.upload_from_graphmodel` previously had no `feeder_mrid`
parameter while the other four did; all five now share one signature.

## 2026-08: `Neo4jConnection.execute()` raises instead of returning None

It caught `DriverError` / `Neo4jError`, logged, and returned `None`. Callers
doing `records, summary, keys = conn.execute(...)` got an opaque `TypeError`
instead of the real Neo4j error, and invalid queries looked like successes.
It now logs the failing query and re-raises.

`configure()` uses `CREATE CONSTRAINT ... IF NOT EXISTS` and `drop_all()` uses
`DROP CONSTRAINT ... IF EXISTS`, so both stay idempotent under the stricter
error handling. `configure()` also raises `RuntimeError` for a missing CIM
profile / namespace instead of calling `_log.exception` outside a handler.

## 2026-08: requires cim-graph >= 0.5.0a9

Two fixes land on the cimgraph side and the floor was raised to match:

- `Neo4jConnection.upload()` was `pass` — a silent no-op, so
  `GraphModel.upload()` reported success while writing nothing.
- `BusBranchModel` / `NodeBreakerModel` called
  `create_new_graph(container)` without passing `self.graph`, silently
  discarding a caller-supplied graph. They now match `FeederModel`.

`clear_cim_config_cache()` also no longer assumes every cimgraph getter is
`@cache`d (`get_iec61970_301` was deprecated and un-cached in 0.5.x, which made
constructing *any* connection raise `AttributeError`). cimloader now reads
`get_iec61970_552()` and exposes `connection.iec61970_552`; the unused
`iec61970_301` attribute is gone.

## 2026-04: Single `upload_from_file` method (breaking)

All format-specific upload methods were removed in favor of a single
auto-detecting `upload_from_file`.

**Removed:**
- `upload_from_xml`
- `upload_from_ttl`
- `upload_from_ntriples`
- `upload_from_jsonld`
- `upload_from_nquads`
- `upload_from_rdflib` (stub)
- Neptune's `upload_to_s3_and_load` (stub; tracked in `TODO.md`)

**Kept and fixed:**
- `upload_from_url` — previously stubbed or broken (Neo4j had an
  `UnboundLocalError`). Now implemented on all four uploaders. Format is
  auto-detected from the URL path extension (query strings / fragments are
  stripped). Blazegraph / Oxigraph / Neptune download via `requests.get`
  and POST the bytes to the DB endpoint; Neo4j passes the URL straight to
  `n10s.rdf.import.fetch`.

**Migrate:**

```python
# Old
uploader.upload_from_xml(filepath='./m', filename='grid.xml')
uploader.upload_from_ttl(filepath='./m', filename='grid.ttl')

# New
uploader.upload_from_file('./m', 'grid.xml')
uploader.upload_from_file('./m', 'grid.ttl')
```

Extension detection lives in `cimloader/_formats.py`. Passing an unknown
extension raises `ValueError`.

## 2026-04: Archived legacy integrations

- `MySQLConnection` / `MySQLUploader` / `MySQLDownloader` → `archive/mysql_legacy/`
- `GraphDBUploader` / `GraphDBDownloader` (stubs) → `archive/graphdb/`
- `NAERM` / `NAERMtoNeo4j` → `archive/naerm/`
- `BlazegraphtoMySQL` batch handler → `archive/mysql_legacy/`
- `cimloader.serializations` package → deleted (use
  `cimgraph.utils.write_xml` / `cimgraph.utils.write_jsonld` instead)

If you depended on any of these, see the per-directory README in `archive/`.

## Earlier (2026-03-ish): `upload_from_file` parameter order

Before this cleanup, Blazegraph used `upload_from_xml(filename=<full path>)`,
Neo4j had the parameter order reversed (`filename, filepath`), and Oxigraph
was already correct. All are now `upload_from_file(filepath, filename)`.

## Earlier: `ConnectionParameters` removed

Configuration is entirely via environment variables from cimgraph
(`CIMG_URL`, `CIMG_CIM_PROFILE`, `CIMG_USERNAME`, etc.). There is no longer
a `ConnectionParameters` dataclass.
