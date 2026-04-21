# Archive

Code that has been removed from the active `cimloader/` package but is kept
around for reference or future rework. Nothing in here is imported by the
library — these are frozen snapshots.

| Directory | Why it's here |
|-----------|---------------|
| `mysql_legacy/` | Previous MySQL connector stored JSON-LD blobs in VARCHAR columns. Works, but pending a rewrite against Apache AGE. See `design/TODO.md`. |
| `graphdb/` | GraphDB has historically been driven through its web GUI. Programmatic support is planned. See `design/TODO.md`. |
| `naerm/` | One-off NAERM API → Neo4j workflow. Imports were already broken at archive time; kept for reference if that integration is revived. |

If you need any of this code, copy it out — don't depend on the `archive/`
path, which may be moved or restructured again without warning.
