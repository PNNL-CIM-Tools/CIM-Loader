# API Migration Notes

History of breaking API changes. For the current API, see `UPLOADER_API.md`.

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
