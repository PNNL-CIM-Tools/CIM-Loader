# NAERM (archived)

One-off integration that downloaded OpenDSS cases from the NAERM API,
converted them to CIM, and uploaded to Neo4j.

## Files

- `naerm_api.py` — HTTP client for the NAERM case-file API
- `naerm_to_neo4j.py` — batch orchestrator

## Why it was archived

The batch handler imports from modules that never existed in this repo:

```python
from cimloader.web_apis.naerm_api import NAERM      # no web_apis/
from cimloader.converters.dss_to_cim import DSStoCIM # no converters/
```

It also references `self.Neo4jConnection` while commenting out the only line
that would assign it — so it would crash at runtime.

Kept for reference in case the NAERM workflow is revived. If it is, the
imports need to be rewritten against the current `cimloader.databases` /
`cimloader.uploaders` structure, and a DSS→CIM converter will have to be
sourced from elsewhere (cimgraph? separate tool?).
