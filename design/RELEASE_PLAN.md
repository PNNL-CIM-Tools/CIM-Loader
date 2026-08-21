# Release Cleanup Plan

Plan for the PyPI release of CIM-Loader, plus the coupled `Neo4jConnection.upload()`
fix in CIM-Graph. Written 2026-08-20.

Ordered so each phase is independently testable and nothing depends on a later phase.

## Findings that shaped this plan

Verified against live Blazegraph / Neo4j / Oxigraph containers:

1. `cimgraph.databases.neo4j.Neo4jConnection.upload()` is `pass` (neo4j.py:354).
   `GraphModel.upload()` delegates to it, so `network.upload()` **silently
   no-ops** — the user's reported bug. It is the only stubbed `upload()` in
   cimgraph.
2. `upload_from_graphmodel` is broken in **all five** cimloader uploaders:
   `AttributeError: '<X>Uploader' object has no attribute 'create_new_graph'`.
   Each ends with `FeederModel(container=..., connection=self, graph=...)` and
   discards it. Constructing a `FeederModel` is a *read* — `__post_init__` calls
   `connection.create_new_graph()` to download. It never uploaded.
3. Zero test coverage for `upload_from_graphmodel`
   (`grep -c` returns 0 in every test file). That is why #2 shipped.
4. `Neo4jConnection.execute()` (cimloader) swallows `Neo4jError` and returns
   `None` — violates Fail Fast / No Blanket Try-Catch.
5. `test_reconfigure_after_drop` asserts `count(n) == 0` after `configure()`,
   but n10s legitimately creates a `_GraphConfig` node. **The test is wrong.**
6. **Async is NOT broken and must be kept.** Measured against Neo4j Community:
   5 concurrent queries in 0.47s vs 0.41s single = **4.3x speedup**. The
   `asyncio.run`-inside-`async def` pattern in `edge_query_runner` works because
   `nest_asyncio.apply()` patches it. No special license is involved. Dropping
   async would cost ~4x on graph loading.
   → Therefore cimloader's connections **cannot** simply subclass cimgraph's:
   cimgraph Neo4j returns `list` (async driver), cimloader returns
   `(records, summary, keys)` (sync driver). See Phase 2.

## Phase 1 — Implement `Neo4jConnection.upload()` in CIM-Graph

Fixes the reported bug. Independent of all cimloader work.

- Replace the `pass` at `cimgraph/databases/neo4j/neo4j.py:354`.
- Cypher/n10s, not SPARQL: cimgraph's Neo4j `execute()` speaks Cypher, so
  `upload_triples_sparql` is not usable here. Serialize each object to RDF and
  ingest via `n10s.rdf.import.inline(<rdf>, "<format>")`, which needs no
  filesystem access — unlike `n10s.rdf.import.fetch`, which cimloader uses for
  files. Reuse `cimgraph.utils.write_xml`-style serialization for the payload.
- Preserve the existing async pattern (`asyncio.run(self.async_execute(...))`)
  for consistency with the rest of the class.
- Batch objects per call rather than one call per object; `get_all_edges`
  already batches at 100, so match that.
- Interim safety: if the full implementation lands later, make it
  `raise NotImplementedError` **immediately**. A silent no-op is the actual
  harm reported — a loud failure is strictly better.

Verify: build a small graph, `network.upload()`, then re-read it back with a
fresh `FeederModel` and assert object counts match.

Optional cleanup (separate commit, do not bundle): change
`asyncio.run(...)` -> `await ...` inside `edge_query_runner`. Measured 4.86x vs
4.30x. Correctness-neutral, small win, removes the `nest_asyncio` dependence
in that path.

## Phase 2 — Resolve the duplicate `ConnectionInterface`

The root cause of finding #2: cimloader declares its own narrow ABC
(`_base.py`: `connect`/`disconnect`/`execute`) and cimloader's
`Neo4jConnection` **duplicates** rather than extends cimgraph's. The uploader
inherited the thin interface, so `create_new_graph` was absent.

Finding #6 rules out the naive "subclass cimgraph's connection" fix: the sync
and async drivers return different shapes, and cimgraph's read path depends on
the async one.

**Decision: keep cimloader's thin ABC, and make the layer split explicit.**

Rationale — cimloader's job is bulk ingest (n10s format strings, `docker cp`,
base-IRI rewriting, S3 staging). None of that touches the CIM object model.
cimgraph owns object-graph read/write because it owns the data profile.
Two connection classes with the same name is still a hazard, so:

- Document the split at the top of `_base.py`: cimloader connections are
  **bulk-ingest** connections and deliberately do *not* implement cimgraph's
  read interface. Name the async/sync divergence as the concrete reason.
- Add `update()` to the ABC. All five connections already implement it and
  `upload_from_graphmodel` will depend on it — it belongs in the contract.
- Do **not** add `create_new_graph` / `get_all_edges` to cimloader. Users who
  want to *read* should use `cimgraph.databases.*`; that is documented, not
  reimplemented.
- Resolve the name collision in docs and examples by importing explicitly, e.g.
  `from cimgraph.databases import Neo4jConnection as CimgraphNeo4j`. Renaming
  cimloader's classes is a larger breaking change; not worth it for 0.0.x.

## Phase 3 — Fix `upload_from_graphmodel` + thin wrappers

The verified fix. Round-tripped against live Blazegraph: wrote a `BaseVoltage`,
read back 4 triples.

- Add a shared helper (DRY — four backends need the identical loop):

  ```python
  # cimloader/uploaders/_graphmodel.py
  from cimgraph.queries.sparql import upload_triples_sparql

  def upload_graph_via_sparql(connection, graph_dict) -> None:
      """INSERT DATA each object in a cimgraph graph dict."""
      for cim_class, objects in graph_dict.items():
          for obj in objects.values():
              connection.update(upload_triples_sparql(obj))
  ```

- Blazegraph / Oxigraph / Neptune / GraphDB: `upload_from_graphmodel` becomes a
  thin wrapper over that helper. Mirrors `sparql_endpoint.py:493`.
- Neo4j: cannot use SPARQL. Delegate to the Phase 1 cimgraph implementation, or
  serialize + `n10s.rdf.import.inline`. Keep the shared helper SPARQL-only
  rather than bending it to cover both.
- Drop the dead `FeederModel` import and the unused `container` /
  `feeder_mrid` construction from every uploader — they exist only to feed the
  broken read call. **Keep `feeder_mrid` in the signature** (documented public
  API in README / UPLOADER_API / NEPTUNE) and ignore-with-a-comment, or accept a
  breaking change and remove it from the docs in the same commit. Note
  `BlazegraphUploader.upload_from_graphmodel` currently has **no**
  `feeder_mrid` param while the other four do — unify the signature.
- Keep the existing `self.cim is None` -> `RuntimeError` guard (Fail Fast).

### Constructor / `__init__` consistency

- `Neo4jUploader.__init__` calls `self.connect()`; the other four do not.
  Pick one and apply it to all five. Prefer **not** connecting in `__init__`
  (every `execute()` already calls `connect()` lazily) so constructing an
  uploader never does I/O.
- `cimloader/uploaders/__init__.py` has no `__all__`, unlike
  `databases/__init__.py`. Add it, including `GraphDBUploader`.

## Phase 4 — Tests for the gap that let this ship

Non-negotiable before release; finding #3 is the reason the bug existed.

- Per-backend `upload_from_graphmodel` round-trip test: build a small graph
  in memory, upload, query it back, assert the triples/nodes are present.
  Parametrize across Blazegraph / Oxigraph / Neo4j so a future stub cannot
  pass silently.
- A test asserting `upload_from_graphmodel` does not raise `AttributeError` —
  the specific regression.
- cimgraph side: a `network.upload()` round-trip test for Neo4j.

## Phase 5 — Remaining cleanup

Correctness fixes (behavior change — call out in MIGRATION.md):

- `Neo4jConnection.execute()`: re-raise instead of returning `None`. Log and
  `raise`, or drop the try/except entirely. Fixes
  `test_query_invalid_cypher`. Currently callers unpacking three values get a
  confusing `TypeError` instead of the real Neo4j error.
- `Neo4jConnection.configure()`: `_log.exception` outside an exception handler
  is wrong — use `raise RuntimeError(...)` for missing profile/namespace.
- `drop_all()` logs a scary error when `n10s_unique_uri` does not exist. Make
  the DROP tolerant of absence, or note it is expected.

Test fix (finding #5 — the test, not the code):

- `test_reconfigure_after_drop`: assert on `:Resource` node count, not
  `count(n)`, since n10s creates `_GraphConfig`.

Docs / packaging:

- `CLAUDE.md` says "`cimloader/downloaders/` — Currently empty"; it now ships
  `fetch` / `manifest` / `models` / `opc`. Also add `GraphDBUploader` to the
  architecture list.
- Bump `version` in `pyproject.toml`. **The local version was misleading**: it
  read `0.0.2a0`, but PyPI's latest cim-loader is `0.1.3a0` (Dec 2024, the
  pre-rewrite package that still depended on `mysql-connector-python` and
  `cim-graph<0.2.0`). Publishing `0.0.x` would have been a version regression.
  Released as **`0.2.0a0`** — ahead of `0.1.3a0`, with the minor bump marking
  the archive/rewrite break. cim-graph shipped as **`0.5.0a11`** (`0.5.0a9`
  was already on PyPI; `0.5.0a10` was skipped and never published). Clear
  stale `dist/` before building.
- `pyproject.toml` has no `[project.urls]`, `license`, or classifiers — worth
  adding for a public release.
- Add a MIGRATION.md entry for the `upload_from_graphmodel` and `execute()`
  behavior changes.
- Once Phase 3 lands, re-verify the three functions in
  `examples/migrate_database.py` actually run (they currently cannot).

## Out of scope

Tracked in TODO.md, not part of this release: Neptune SigV4 + S3 bulk load,
GraphDB full support, `batch_handlers`, MySQL -> Apache AGE, CIM 18 base-IRI
Option B. The ~20 bare `except:` blocks in cimgraph are a real Fail Fast
concern but too broad to fold in here.
