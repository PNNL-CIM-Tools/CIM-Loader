# Future Work

Tracked items that were deliberately left out of the cleanup pass.

## MySQL → Apache AGE

`archive/mysql_legacy/` contains the previous MySQLConnection. It stores
JSON-LD blobs in VARCHAR/JSON columns — fast but not a sound relational
schema. Rewrite against **Apache AGE** (PostgreSQL graph extension) so CIM
relationships map to real graph edges. New home: `cimloader/databases/age.py`
and `cimloader/uploaders/age.py`.

## GraphDB full support

`archive/graphdb/` was only ever empty stubs — actual GraphDB usage has gone
through the web workbench. Implement:

- Repository creation via the GraphDB REST API
- Bulk upload via REST
- SPARQL endpoint connection (trivial via `SPARQLWrapper`, same pattern as
  Blazegraph / Oxigraph / Neptune)

## AWS Neptune

Current `NeptuneUploader` works only against IAM-disabled clusters.

- Implement AWS Signature V4 authentication
- Implement S3 bulk loader integration (recommended for >100MB datasets)
- Verify JSON-LD and TriG support end-to-end

## batch_handlers

Planned workflow: upload a full CIM package (EQ + TP + SSH profiles) to a
single target database and **append** profile-specific attributes to
existing objects instead of overwriting them per-file. See
`cimloader/batch_handlers/README.md`.

## Oxigraph rough edges

Uncovered while writing the `upload_from_url` integration tests. Pre-existing,
not introduced by the cleanup:

- `tests/test_models/ieee13_2021.xml` fails to parse in Oxigraph because it
  uses bare-fragment IRIs (`#_ABCD...`) with no document base. Blazegraph is
  permissive; Oxigraph enforces RFC 3987. Either fix the model to declare
  `xml:base`, or find a tolerant parser path.
- `TestOxigraphContainerUpload` execs `curl` inside the `ghcr.io/oxigraph/oxigraph`
  image, which doesn't ship curl. Either switch to a variant that has curl
  or upload via a different in-container mechanism (e.g. `wget`, or a POST
  from the host without `docker cp`).

## NAERM integration

`archive/naerm/` contains the old NAERM API client and its Neo4j batch
handler. Imports referenced modules that never existed
(`cimloader.web_apis`, `cimloader.converters`). If revived, rewrite against
the current `cimloader.databases` / `cimloader.uploaders` structure and
sort out where the DSS → CIM converter lives.
