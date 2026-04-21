# API Migration Guide

## upload_from_file() API Standardization

All uploader classes now use a **consistent API signature** for uploading files:

```python
upload_from_file(filepath: str, filename: str)
```

### Changes by Database

#### Blazegraph

**OLD (Deprecated):**
```python
uploader.upload_from_xml(filename='/full/path/to/model.xml')
```

**NEW:**
```python
uploader.upload_from_file(filepath='./models', filename='model.xml')
```

The old `upload_from_xml()` method still works but logs a deprecation warning.

#### Neo4j

**OLD (Wrong parameter order):**
```python
uploader.upload_from_file(filename='model.xml', filepath='./models')
```

**NEW (Correct parameter order):**
```python
uploader.upload_from_file(filepath='./models', filename='model.xml')
```

⚠️ **Breaking Change**: The parameter order was reversed to match other uploaders.

#### Oxigraph

**No changes** - Oxigraph already used the correct signature.

```python
uploader.upload_from_file(filepath='./models', filename='model.xml')
```

### New: Format-Specific Upload Methods

All uploaders now provide format-specific methods in addition to `upload_from_file()`:

```python
# Auto-detect format from extension
uploader.upload_from_file(filepath='./models', filename='grid.xml')

# Or be explicit about format
uploader.upload_from_xml(filepath='./models', filename='grid.xml')
uploader.upload_from_ttl(filepath='./models', filename='grid.ttl')
uploader.upload_from_ntriples(filepath='./models', filename='grid.nt')
uploader.upload_from_jsonld(filepath='./models', filename='grid.jsonld')
```

**Available on all uploaders:**
- `upload_from_file()` - Auto-detects format from file extension
- `upload_from_xml()` - RDF/XML format
- `upload_from_ttl()` - Turtle format
- `upload_from_ntriples()` - N-Triples format
- `upload_from_jsonld()` - JSON-LD format (Blazegraph, Neo4j only)
- `upload_from_nquads()` - N-Quads format (Oxigraph only)

See `UPLOADER_API.md` for complete documentation.

### Rationale

This change provides:

1. **Consistency** - All uploaders use the same API
2. **Clarity** - `filepath` (directory) comes before `filename` (file)
3. **Convention** - Matches typical file system operations
4. **Type Safety** - Both parameters are explicitly typed as `str`
5. **Format Awareness** - Explicit methods for each RDF format
6. **Flexibility** - Auto-detection OR explicit format specification

### Migration Checklist

- [ ] Replace `upload_from_xml()` calls with `upload_from_file()`
- [ ] Ensure Blazegraph calls split full path into `filepath` and `filename`
- [ ] **Important**: Swap Neo4j parameter order from `(filename, filepath)` to `(filepath, filename)`
- [ ] Update any scripts or automation using the old API
- [ ] Search codebase for `upload_from_xml` and `upload_from_file` usage

### Examples

#### Before (Mixed APIs)
```python
# Blazegraph - full path
blazegraph.upload_from_xml(filename='./models/grid.xml')

# Neo4j - wrong order
neo4j.upload_from_file(filename='grid.xml', filepath='./models')

# Oxigraph - correct
oxigraph.upload_from_file(filepath='./models', filename='grid.xml')
```

#### After (Consistent API)
```python
# All uploaders use the same signature
blazegraph.upload_from_file(filepath='./models', filename='grid.xml')
neo4j.upload_from_file(filepath='./models', filename='grid.xml')
oxigraph.upload_from_file(filepath='./models', filename='grid.xml')
```

### Backward Compatibility

- **Blazegraph**: `upload_from_xml()` still works but logs a deprecation warning
- **Neo4j**: **Breaking change** - parameter order reversed
- **Oxigraph**: No changes required

If you have existing code using Neo4j's `upload_from_file()`, you **must** swap the parameter order.

### Testing

All tests have been updated to use the new consistent API. Run tests to verify:

```bash
pytest tests/test_blazegraph.py -v
pytest tests/test_neo4j.py -v
pytest tests/test_oxigraph.py -v
```

## Environment Variable Configuration

All uploaders now use environment variables from `cim-graph`:

```python
import os

# Common configuration
os.environ['CIMG_CIM_PROFILE'] = 'rc4_2021'
os.environ['CIMG_NAMESPACE'] = 'http://iec.ch/TC57/CIM100#'

# Database-specific URL
os.environ['CIMG_URL'] = 'http://localhost:8889/bigdata/namespace/kb/sparql'  # Blazegraph
# or
os.environ['CIMG_URL'] = 'neo4j://localhost:7687'  # Neo4j
# or
os.environ['CIMG_URL'] = 'http://localhost:7878/query'  # Oxigraph
```

See `.env.example` for a complete reference.

## Removed: ConnectionParameters Class

The `ConnectionParameters` class has been removed. All configuration now happens via environment variables.

**OLD:**
```python
from cimloader.databases import ConnectionParameters

params = ConnectionParameters(url="http://localhost:8889/bigdata/namespace/kb/sparql")
loader = BlazegraphUploader(params)
```

**NEW:**
```python
import os

os.environ['CIMG_URL'] = 'http://localhost:8889/bigdata/namespace/kb/sparql'
loader = BlazegraphUploader()
```

This change improves consistency with `cim-graph` and simplifies configuration management.
