# GraphDB (archived stubs)

Previous GraphDB uploader/downloader classes. Both were empty stubs that
only raised `NotImplementedError`.

Historically, GraphDB has been driven through its web UI — repositories are
created via the workbench and initial bulk uploads are done through the
import page. Programmatic upload/download was never wired up.

## Planned work

- Repository creation via GraphDB REST API
- Bulk upload via REST
- SPARQL endpoint connection (trivial via `SPARQLWrapper`, same pattern as
  Blazegraph/Oxigraph/Neptune)

See `design/TODO.md`.
