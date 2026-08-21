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

## Base IRI / CIM 18 alignment

All four uploaders now inject `xml:base="http://gridappsd.org/cim/"` into
RDF/XML files that don't declare one, so fragment IRIs (`#_UUID`) resolve
identically across Blazegraph, Neo4j, Oxigraph, and Neptune. This is
Option A — backwards compatible with CIM 15–17 (IEC 61970-301).

CIM 18 moves to `urn:uuid:<UUID>` as the canonical `@id` and the new
`http://cim.ucaiug.io/ns/101.0#` namespace. When CIM 18 ships, revisit
`_base_iri.py` to rewrite `rdf:ID="_UUID"` / `rdf:resource="#_UUID"` into
`urn:uuid:` IRIs (Option B) rather than injecting a local base.

## NAERM integration

`archive/naerm/` contains the old NAERM API client and its Neo4j batch
handler. Imports referenced modules that never existed
(`cimloader.web_apis`, `cimloader.converters`). If revived, rewrite against
the current `cimloader.databases` / `cimloader.uploaders` structure and
sort out where the DSS → CIM converter lives.
