# Model Provenance & Distribution Design

Status: **stubbed** (2026-06-16). Supersedes the legacy `gridappsd/blazegraph`
pre-populated-image distribution model. Loader mechanism is scaffolded in
`cimloader/downloaders/` (manifest + fetch + OPC bootstrap are real; the 552
metadata-graph parse is stubbed pending a concrete instance). Manifest contract:
`design/model_manifest.linkml.yaml` (+ `design/models.sample.yaml`), to move to
the Powergrid-Models catalog repo.

## Problem

Golden feeder models (IEEE test feeders, PNNL taxonomy feeders, Grid-Kitchen
feeders, EPRI DPV, NREL SMART-DS) are scattered across repos and stores with no
single source of truth:

- ~300 MB of stale/partial fixture copies are committed (not LFS) into CIMHub
  spoke test dirs.
- The original models + (now-defunct) blazegraph build scripts are stranded in
  `github.com/AAndersn/Powergrid-Models` (~1 GB, build broken).
- Internal `atlas.pnnl.gov` (InvenioRDM) is alpha + firewalled → unusable from a
  clean container.
- NREL SMART-DS lives in OEDI's `oedi-data-lake` S3 (no DOI, no per-feeder
  landing page, awkward to navigate).

We need: **one authoritative, FAIR, firewall-free store + a provenance manifest**
that records, per model, *what it is, where it came from, which format is golden,
and how to fetch it by checksum* — consumed identically by CIMHub Tier-4 tests
and the Powergrid-Models docker runtime.

## Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Authoritative store = Zenodo** | Same InvenioRDM stack as atlas, but public + firewall-free + free + versioned DOIs. Resolvable unauthenticated from a clean container. |
| 2 | **DOI granularity = per model-family** (not per-feeder, not per-repo) | Per-feeder = citation/maintenance sprawl; per-repo = kills independent versioning + drowns provenance. Family maps 1:1 onto `golden_direction` (a property of the source). |
| 3 | **Per-part identity = persistent `Id` + checksum** (below the DOI; NOT filename) | 61970-557 §4.4/§4.5: the OPC `Id` is portable across packages and filenames are meaningless. Checksum = fetch-resolve key; DOI = citation; `sources[]` = resilience. Store-agnostic by construction. |
| 4 | **Distribution = runtime fetch, NOT build-time bake** | Powergrid-Models docker pulls at *container start* via `cimloader`, then uploads into the local triplestore. Relaxes "firewall-free" from a hard build constraint to ordinary startup egress. Replaces the fat `gridappsd/blazegraph` image. |
| 5 | **Loader mechanism lives in `cimloader`; the manifest data does NOT** | `cim-loader` is already "CIM Database Uploader **& Downloader**" — it ships ZERO catalog and is pure mechanism. Each *consumer* (Powergrid-Models docker, CIMHub Tier-4 tests) owns its own `models.yaml` describing which models *it* loads and where to fetch them, and passes that path into the loader. No bundled "example" catalog that could be mistaken for authoritative. |
| 6 | **Profile split (EQ/SSH/…) designed-for now, single-file to start** | Manifest carries a `parts[]` list from day one; first uploads are combined RDF. Splitting into CGMES profiles later needs no schema change. |

## Architecture

```
                    Zenodo (authoritative, DOI'd, firewall-free)
                    OEDI S3 / bettergrids / IEEE DataPort (mirrors / upstream)
                                  ▲           ▲
                                  │ fetch-by-checksum (ordered sources[])
                                  │
        ┌─────────────────────────────────────────────────────┐
        │  cimloader  (PyPI) — pure mechanism, NO catalog       │
        │  ┌──────────────────┐      ┌──────────────────────┐   │
        │  │ downloaders/      │      │ uploaders/           │   │
        │  │  manifest resolver│ ───► │  oxigraph / neo4j /  │   │
        │  │  + fetch + OPC    │      │  neptune / ...       │   │
        │  └──────────────────┘      └──────────────────────┘   │
        └─────────────────────────────────────────────────────┘
              ▲ load_manifest(path)          ▲ upload_part(part)
              │ (caller supplies the path)   │
        ┌─────┴──────────────────┐    ┌──────┴──────────────────────┐
        │ Powergrid-Models repo   │    │ CIMHub repo                  │
        │  models.yaml (catalog)  │    │  tiny yardstick manifest     │
        │  → docker: pull→load    │    │  → Tier-4 golden-CIM diff    │
        └─────────────────────────┘    └──────────────────────────────┘
```

The catalog YAML is **owned by each consumer**, not by the wheel. `cimloader`
never looks for a manifest on its own — every entry point takes an explicit path
and fails fast if it's missing.

## Manifest schema

Checked into the **consumer** repo (e.g. `Powergrid-Models/manifest/models.yaml`),
**not** the wheel; the loader is handed the path. One entry per feeder, grouped by
`family`. The **checksum is identity**; `doi` is the citation; `sources[]` is tried
in order (first checksum-match wins). The schema is authored in LinkML
(`model_manifest.linkml.yaml`) and SKOS-mapped to the 552 vocabulary (see below);
the runtime loader parses the conforming YAML with plain `pyyaml`.

```yaml
- id: ieee13                            # stable slug, used by tests + loader
  family: ieee-test-feeders             # = Zenodo record = one concept DOI
  version: "2024.1"
  golden_format: cim_rdf                # dss | raw | glm | cim_rdf
  golden_direction: native_is_golden    # native_is_golden | cim_is_golden
  feeder_mrid: "_49AD8E07-3BF9-...-C3722F837B62"
  doi: "10.5281/zenodo.XXXXXX"          # the family's version DOI (null if none, e.g. OEDI)
  parts:                                # CGMES-style profile split (1 entry = combined RDF for now)
    - id: _49ad8e07_3bf9_a4e2...        # persistent OPC NCName id (61970-557 §4.4); portable across packages
      profile: combined                 # combined | EQ | SSH | SV | TP | ...
      content_type: application/rdf+xml  # IANA/IETF-registered (61970-557 §4.6)
      filename: ieee13.cimx             # NOT identity — see §4.5; ID + checksum are identity
      checksum: "sha256:abc123..."      # the resolve key
      sources:                          # ordered: firewall-free first, upstream/mirror after
        - https://zenodo.org/records/<rec>/files/ieee13.cimx?download=1
        - https://oedi-data-lake.s3.amazonaws.com/.../ieee13.cimx   # upstream lineage pointer
```

### `family` groupings (initial)

| family | golden_direction | golden_format | upstream |
|--------|-----------------|---------------|----------|
| `ieee-test-feeders` | `native_is_golden` | dss / raw | IEEE PES |
| `pnnl-taxonomy-feeders` | `native_is_golden` | dss / glm | PNNL / Powergrid-Models |
| `grid-kitchen-feeders` | `cim_is_golden` | cim_rdf | Grid-Kitchen (ArcGIS→CIM) |
| `epri-dpv` | `native_is_golden` | dss | EPRI |
| `nrel-smart-ds` | `native_is_golden` | dss | OEDI S3 (mirror subset to Zenodo) |

`golden_direction` drives how Tier-4 cross-format tests assert (see
CIMHub `TEST_FIXTURE_ARCHITECTURE.md`): `cim_is_golden` → diff exports *out* of a
trusted reference CIM; `native_is_golden` → validate CIM derived *in* (or restrict
to native→CIM→native roundtrips until a CIM is blessed).

## OPC packaging (IEC 61970-557 — normative)

A CIM model is distributed as an **OpenXML / OPC package** (ISO/IEC 29500, the
same container as `.docx`). The 61970-557 packaging restrictions are normative
(`shall`); the key ones that bind our design:

| § | Rule | Impact on us |
|---|------|--------------|
| 4.1 | Package extension **`.cimx`** | manifest `filename`/sources use `.cimx`; loader dispatches on it |
| 4.2 | **Exactly one** business-metadata file, rel-type `http://cim-type.ucaiug.io/package/BusinessProcessMetadata`; may be any CIM-defined serialization (61970-552 is one). Core props **and** custom props files are mandatory; `dcterms:conformsTo` carries the business-process profile IRI | loader reads core/custom props to learn the profile *before* it can interpret grid-part roles |
| 4.3 | **Non-OPC relationship types are business-process-defined** and cannot be interpreted until `dcterms:conformsTo` is read | hard bootstrap dependency: conformsTo → then resolve part roles |
| 4.4 | Each part has a **persistent, portable `Id`** (NCName; recommended UUID-derived, underscore-prefixed if it starts with a digit). Valid even when the part is moved out of / between packages | **this is our `parts[].id`** — stable identity independent of store/filename |
| 4.5 | **Filenames convey no meaning** (`shall not`) | never key off filename; role = rel-type, identity = id + checksum |
| 4.6 | Content types **should** be IANA/IETF-registered; `application/rdf+xml` for 61970-552 | manifest records `content_type` per part; uploader dispatches on it |

**Bootstrap read order (loader `read_package()`):**

```
1. [Content_Types].xml   → serialization per part (Default by ext + per-part Override)
2. .rels                 → parts: Id, Target (incl. TargetMode="External"), Type
                           (OPC types resolve now; business types are still opaque)
3. docProps/core.xml     → Dublin Core + dcterms:conformsTo  (the profile IRI)
   + custom props        → mandatory; business-defined fields
4. resolve business rel-types  (now that conformsTo is known)
5. the one BusinessProcessMetadata part  → 61970-552 Dataset/Activity graph
6. grid parts            → referenced BY Id from the metadata graph; hand each to
                           the uploader by its declared content_type
```

`TargetMode="External"` (§ illustrated by the `http://myserver/CombinedTP.xml`
external part) is the standard's blessed way to say "this part lives on a web
server" — i.e. our ordered `sources[]` / OEDI-remote case expressed in OPC terms.

### Three-layer split (no overlap)

| Layer | Role | Format |
|-------|------|--------|
| OPC `.cimx` package | self-describing bundle (EQ + SSH + boundary + business-metadata for one model) | ISO/IEC 29500 |
| `BusinessMetadata` part (inside) | the `Dataset` / `GridDataset.contains` / `Activity` provenance graph | 61970-552 RDF |
| consumer `models.yaml` | operational index over **packages** + external parts; fetch order + checksum. Lives in Powergrid-Models / CIMHub, not the wheel | our YAML (LinkML-shaped) |

The manifest tracks *packages*, not loose RDF files; profile-stack and lineage
detail live **inside** each package in standard form (`GridDataset.contains` for
the EQ/SSH stack; `Activity.agent/function/generated` for `golden_direction`
lineage). Manifest fields align to `Dataset` semantics: `version`→`Dataset.version`,
publisher→`authority`, timestamp→`issued`, supersession→`replaces`.

## Loader (`cimloader/downloaders/`)

Fills the existing empty stub. Minimal surface (KISS):

```python
# downloaders/manifest.py
load_manifest(path) -> list[ModelEntry]            # path is REQUIRED — no packaged default
find(entries, model_id) -> ModelEntry              # KeyError if absent

# downloaders/fetch.py
fetch_part(part, cache_dir="~/.cache/cimloader") -> Path
    # try part.sources in order; GET; verify sha256 == part.checksum; cache by checksum; offline-friendly
fetch_model(entry, cache_dir=...) -> Path          # the .cimx package, checksum-verified

# downloaders/opc.py  (OPC bootstrap — fully specified by 61970-557 §4)
read_package(cimx_path) -> Package
    # parse [Content_Types].xml + .rels; read core/custom props -> conformsTo;
    # resolve business rel-types; yield grid parts as (id, content_type, bytes|external_url)
```

**Runtime upload path** (Powergrid-Models docker; reuses existing uploader):

```python
from cimloader.downloaders import load_manifest, find, fetch_model, read_package
from cimloader.uploaders import OxigraphUploader

entries = load_manifest("/etc/powergrid-models/models.yaml")   # consumer owns the catalog
up = OxigraphUploader()
for model_id in MODELS_TO_LOAD:
    entry = find(entries, model_id)
    pkg = read_package(fetch_model(entry))         # fetch .cimx + OPC bootstrap
    for part in pkg.grid_parts:                    # roles resolved via rel-type, not filename
        up.upload_part(part)                        # dispatch by part.content_type
```

`OxigraphUploader.upload_from_url` already auto-detects format and injects
`xml:base`; `upload_part` is the thin wrapper that feeds it a bootstrapped part
(internal bytes or `TargetMode="External"` URL) by declared content-type — so the
EQ/SSH stack is transparent: read package once, POST each grid part, same feeder
graph.

### Packaging note

Runtime deps are `cim-graph`, `requests`, `pyyaml` — and deliberately **NOT**
`linkml`/`linkml-runtime`. The LinkML schema is contract + docs; the wheel parses
the conforming YAML with plain `pyyaml`, so the bare-metal install stays small.

## What stays in CIMHub (decoupling)

- Tiny hand-verified **IEEE-13/14 yardsticks** stay in-repo (hermetic, no network,
  99% of the Tier-4 test path).
- Tier-4 harness can be built/proven against yardsticks **without** resolving the
  store — manifest/loader work unblocks only the LARGE models (9500, EPRI), a
  parallel track, not a prerequisite.
- Separately: stop tracking the committed ~300 MB (`git rm` + `.gitignore`).
  History purge (filter-repo / BFG) is an optional later step.

## Open items / next steps

1. Create the Zenodo records (one per family); mint concept + version DOIs.
2. Upload combined RDF + native goldens; record checksums into the consumer `models.yaml`.
3. ✅ `downloaders/manifest.py` + `fetch.py` + `opc.py` (`read_package`) implemented
   and unit-tested; `requests`/`pyyaml` promoted to runtime deps.
4. Move `model_manifest.linkml.yaml` + a real `models.yaml` into the
   Powergrid-Models catalog repo (currently parked in `design/` as the worked example).
5. Write the Powergrid-Models docker runtime routine (pull → read_package → upload-via-cimloader).
5. Mirror the SMART-DS subset we actually test from OEDI into a `nrel-smart-ds`
   Zenodo record; keep the OEDI S3 URL as the upstream `sources[]` pointer.
6. Mirror the SMART-DS subset we actually test from OEDI into a `nrel-smart-ds`
   Zenodo record; keep the OEDI S3 URL as the upstream `sources[]` pointer.
7. Decide EQ/SSH split timing per family (schema already supports it).
8. **Blocked on team:** a concrete `BusinessMetadata` instance (real 61970-552
   `Dataset`/`Activity` RDF, namespace prefix) — the *package* bootstrap is fully
   specified, only the metadata-graph parsing waits on this.

---

## For the CIM Metadata Team (IEC 61970-552 / 55X)

**What we're doing and why we need you.** We distribute golden feeder models as
OPC `.cimx` packages (per 61970-557). Inside each package, the single
`BusinessProcessMetadata` part is where the model's *provenance* lives — and we
want that to be a real **61970-552 `Dataset`/`Activity` graph**, not a bespoke
header. Our package bootstrap (Content_Types → .rels → `dcterms:conformsTo` →
resolve business rel-types → locate the metadata part) is fully implemented
against the §4 normative text. The one piece we have **stubbed** is parsing the
552 graph itself, because we don't yet have a concrete serialized instance.

**The one ask:** a real, serialized 552 metadata instance — even a single model —
with:
- the actual namespace prefix/IRI in use (we've been assuming
  `http://www.ucaiug.org/Metadata#`),
- a `Dataset`/`GridDataset` with `authority`, `issued`, `version`, and a
  `contains` profile-stack (EQ/SSH/…),
- an `Activity` with `agent`/`function`/`generated` so we can record
  `golden_direction` lineage (was the CIM derived from the native model, or vice
  versa),
- the chosen serialization (we default to `application/rdf+xml` per §4.6, but the
  spec allows any CIM serialization — please confirm).

With that, `parse_business_metadata()` (currently a single
`NotImplementedError`) lights up; nothing else in the pipeline changes.

**Forward-looking — LinkML, not Sparx UML.** We've authored our operational
manifest as a **LinkML schema** (`model_manifest.linkml.yaml`) whose slots are
SKOS-mapped to the 552 vocabulary (`family`→`md:Dataset.authority`,
`version`→`md:Dataset.version`, `profile`→`md:GridDataset.contains`, classes
`class_uri`'d to `md:GridModel`/`md:Distribution`). This is a deliberate bet on
the effort to move 61970 metadata to LinkML YAML. If/when 552 ships as LinkML,
our manifest becomes a thin **profile** of the upstream schema — an `import` plus
a few extra operational slots (`checksum`, `sources`, `golden_direction`) — not a
migration. We'd welcome aligning our SKOS mappings against whatever you publish so
the round-trip is exact.

## For the GridAPPS-D Dev Team (replacing the monolithic image)

**What changes.** Today a populated triplestore ships as one fat pre-baked image
(`gridappsd/blazegraph`): the models are *inside* the image, so every model
change means a rebuild + re-push of a multi-hundred-MB artifact, and there's no
provenance trail for what's in there. We're replacing **bake-time** with
**run-time fetch**.

**The new shape:**
- The image ships **empty** (just the triplestore — Oxigraph/Blazegraph/… — plus
  `cim-loader` from PyPI). No models baked in. Small, rebuilt rarely.
- A **`models.yaml`** catalog lives in **Powergrid-Models** (the consumer repo,
  *not* the `cim-loader` wheel). It lists which feeders to load, their checksums,
  and ordered fetch `sources[]` (Zenodo first, upstream/OEDI as fallback).
- At **container start**, an entrypoint script calls `cimloader`:
  `load_manifest(path)` → for each model `fetch_model()` (downloads the `.cimx`,
  verifies sha256, caches under `~/.cache/cimloader`) → `read_package()` (OPC
  bootstrap) → `upload_part()` into the local store. ~15 lines, shown above.

**Why it's better:**
- **No more giant image pushes.** Models are pulled from a DOI'd, versioned,
  firewall-free store (Zenodo) at startup. Changing a model = update one
  `models.yaml` line, not a rebuild.
- **Provenance is first-class.** Every model is checksum-pinned and DOI-citable;
  the `.cimx` carries its own 552 metadata graph.
- **Same tool both ways.** `cim-loader` already does the uploading; it now also
  does the downloading — one dependency, not a pile of `curl`/`unzip` shell.
- **Offline-friendly.** The checksum-keyed cache means a warm container skips the
  network entirely; CI can pre-seed the cache.

**Migration path (incremental, no flag-day):**
1. Add `cim-loader` + an entrypoint to the existing image; keep baked models as a
   fallback. Prove one feeder loads from Zenodo at startup.
2. Move the model list into Powergrid-Models `models.yaml`; load from it.
3. Drop the baked models; ship the empty image. Rebuilds become rare.

**What you'd need from us:** the populated Zenodo records + the
Powergrid-Models `models.yaml` (open items 1–4 above). The loader and OPC bootstrap
are done and unit-tested today.

## Verified constraints (2026-06-16)

- Zenodo limits: **50 GB / file, 50 GB / record, 100 files / record** — all
  artifacts (9500 ~38 MB, EPRI DPV) fit comfortably; size does not force
  granularity.
- Anonymous file fetch pattern (no auth, container-safe):
  `https://zenodo.org/records/<id>/files/<filename>?download=1`.
