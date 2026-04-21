# Uploader API Reference

All CIM-Loader uploaders provide a **consistent, format-aware API** for uploading RDF data to different databases.

## Common Pattern

All uploaders follow this architecture:

```python
# Auto-detect format from file extension
uploader.upload_from_file(filepath='./models', filename='grid.xml')

# Or use format-specific methods
uploader.upload_from_xml(filepath='./models', filename='grid.xml')
uploader.upload_from_ttl(filepath='./models', filename='grid.ttl')
uploader.upload_from_ntriples(filepath='./models', filename='grid.nt')
uploader.upload_from_jsonld(filepath='./models', filename='grid.jsonld')
```

## Blazegraph Uploader

### Supported Formats

| Method | Format | File Extensions | Content-Type |
|--------|--------|----------------|--------------|
| `upload_from_file()` | Auto-detect | All below | Detected |
| `upload_from_xml()` | RDF/XML | `.xml`, `.rdf` | `application/rdf+xml` |
| `upload_from_ttl()` | Turtle | `.ttl`, `.turtle` | `text/turtle` |
| `upload_from_ntriples()` | N-Triples | `.nt`, `.ntriples` | `application/n-triples` |
| `upload_from_jsonld()` | JSON-LD | `.jsonld`, `.json-ld` | `application/ld+json` |

### Example

```python
import os
from cimloader.uploaders import BlazegraphUploader

os.environ['CIMG_URL'] = 'http://localhost:8889/bigdata/namespace/kb/sparql'

uploader = BlazegraphUploader()

# Auto-detect format
uploader.upload_from_file(filepath='./models', filename='grid.xml')

# Explicit format
uploader.upload_from_ttl(filepath='./models', filename='grid.ttl')
```

### Supported Extensions
- `.xml`, `.rdf` → RDF/XML
- `.ttl`, `.turtle` → Turtle
- `.nt`, `.ntriples` → N-Triples
- `.nq`, `.nquads` → N-Quads
- `.jsonld`, `.json-ld` → JSON-LD
- `.trig` → TriG

## Neo4j Uploader (via n10s)

### Supported Formats

| Method | Format | File Extensions | n10s Format |
|--------|--------|----------------|-------------|
| `upload_from_file()` | Auto-detect | All below | Detected |
| `upload_from_xml()` | RDF/XML | `.xml`, `.rdf` | `RDF/XML` |
| `upload_from_ttl()` | Turtle | `.ttl`, `.turtle` | `Turtle` |
| `upload_from_ntriples()` | N-Triples | `.nt`, `.ntriples` | `N-Triples` |
| `upload_from_jsonld()` | JSON-LD | `.jsonld`, `.json-ld` | `JSON-LD` |

### Example

```python
import os
from cimloader.uploaders import Neo4jUploader

os.environ['CIMG_URL'] = 'neo4j://localhost:7687'
os.environ['CIMG_USERNAME'] = 'neo4j'
os.environ['CIMG_PASSWORD'] = 'password'

# Optional: container name for docker cp
uploader = Neo4jUploader(container='neo4j_cim_loader')

# Auto-detect format
uploader.upload_from_file(filepath='./models', filename='grid.xml')

# Explicit format
uploader.upload_from_ttl(filepath='./models', filename='grid.ttl')
```

### Container Mode

When `container` parameter is provided, files are copied to the Neo4j container before import:

```python
# With container - uses docker cp
uploader = Neo4jUploader(container='neo4j_cim_loader')
uploader.upload_from_file(filepath='./models', filename='grid.xml')

# Without container - direct file path (Neo4j must have access)
uploader = Neo4jUploader()
uploader.upload_from_file(filepath='/var/lib/neo4j/import/models', filename='grid.xml')
```

### Supported Extensions
- `.xml`, `.rdf` → RDF/XML
- `.ttl`, `.turtle` → Turtle
- `.nt`, `.ntriples` → N-Triples
- `.jsonld`, `.json-ld` → JSON-LD
- `.nq`, `.nquads` → N-Quads
- `.trig` → TriG

## Oxigraph Uploader

### Supported Formats

| Method | Format | File Extensions | Content-Type |
|--------|--------|----------------|--------------|
| `upload_from_file()` | Auto-detect | All below | Detected |
| `upload_from_xml()` | RDF/XML | `.xml`, `.rdf` | `application/rdf+xml` |
| `upload_from_ttl()` | Turtle | `.ttl`, `.turtle` | `text/turtle` |
| `upload_from_ntriples()` | N-Triples | `.nt`, `.ntriples` | `application/n-triples` |
| `upload_from_nquads()` | N-Quads | `.nq`, `.nquads` | `application/n-quads` |

### Example

```python
import os
from cimloader.uploaders import OxigraphUploader

os.environ['CIMG_URL'] = 'http://localhost:7878/query'

# Direct upload
uploader = OxigraphUploader()
uploader.upload_from_file(filepath='./models', filename='grid.xml')

# Container mode
uploader = OxigraphUploader(container='oxigraph_cim_loader')
uploader.upload_from_file(filepath='./models', filename='grid.xml')
```

### Container Mode

Similar to Neo4j, Oxigraph supports container mode:

```python
# With container - uses docker cp and curl inside container
uploader = OxigraphUploader(container='oxigraph_cim_loader')

# Without container - direct HTTP upload
uploader = OxigraphUploader()
```

### Supported Extensions
- `.xml`, `.rdf` → RDF/XML
- `.ttl`, `.turtle` → Turtle
- `.nt`, `.ntriples` → N-Triples
- `.nq`, `.nquads` → N-Quads

## API Design Principles

### 1. Format-Specific Methods

Each uploader provides format-specific methods (`upload_from_xml()`, `upload_from_ttl()`, etc.) that:
- Accept `filepath` and `filename` parameters
- Call internal `_upload()` method with appropriate content-type/format
- Are explicit and self-documenting

### 2. Auto-Detection

The `upload_from_file()` method:
- Detects format from file extension using `_get_content_type()` or `_get_n10s_format()`
- Convenient for generic file uploads
- Raises `ValueError` if extension is not recognized

### 3. Internal Methods

Private methods handle the actual upload:
- **Blazegraph**: `_upload(filepath, filename, content_type)`
- **Neo4j**: `_upload(filepath, filename, format)`
- **Oxigraph**: `_upload_with_format(filepath, filename, content_type)`

### 4. Consistent Signatures

All public methods use the same signature:
```python
def upload_from_X(self, filepath: str, filename: str) -> Optional[Records]:
    pass
```

This makes it easy to switch between:
- Different databases (Blazegraph ↔ Oxigraph)
- Different formats (XML ↔ Turtle)

## Error Handling

All uploaders raise exceptions for:
- **Unsupported file formats**: `ValueError` with list of supported extensions
- **Upload failures**: `subprocess.CalledProcessError` or database-specific exceptions
- **Missing files**: `FileNotFoundError` (from subprocess or filesystem)

Example:
```python
try:
    uploader.upload_from_file(filepath='./models', filename='data.txt')
except ValueError as e:
    print(f"Unsupported format: {e}")
except subprocess.CalledProcessError as e:
    print(f"Upload failed: {e}")
```

## Best Practices

### 1. Use Format-Specific Methods When Possible

More explicit and self-documenting:
```python
# Good - clear intent
uploader.upload_from_xml(filepath='./models', filename='grid.xml')

# Less clear
uploader.upload_from_file(filepath='./models', filename='grid.xml')
```

### 2. Use Auto-Detection for Generic Code

When writing generic upload logic:
```python
def upload_model(uploader, filepath, filename):
    """Works with any uploader and format"""
    uploader.upload_from_file(filepath=filepath, filename=filename)
```

### 3. Configure via Environment Variables

Set configuration before creating uploaders:
```python
import os

os.environ['CIMG_URL'] = 'http://localhost:8889/bigdata/namespace/kb/sparql'
os.environ['CIMG_CIM_PROFILE'] = 'rc4_2021'
os.environ['CIMG_NAMESPACE'] = 'http://iec.ch/TC57/CIM100#'

uploader = BlazegraphUploader()
```

### 4. Use Container Mode When Appropriate

For Neo4j and Oxigraph, use container mode when:
- Running in Docker
- Database doesn't have direct filesystem access
- Files are on host but database is in container

```python
# Container mode
uploader = Neo4jUploader(container='neo4j_cim_loader')

# Direct mode (database can access files directly)
uploader = Neo4jUploader()
```

## Complete Example

```python
import os
from cimloader.uploaders import BlazegraphUploader, Neo4jUploader, OxigraphUploader

# Configure common settings
os.environ['CIMG_CIM_PROFILE'] = 'rc4_2021'
os.environ['CIMG_NAMESPACE'] = 'http://iec.ch/TC57/CIM100#'

# Upload to Blazegraph
os.environ['CIMG_URL'] = 'http://localhost:8889/bigdata/namespace/kb/sparql'
blazegraph = BlazegraphUploader()
blazegraph.upload_from_xml(filepath='./models', filename='grid.xml')

# Upload to Neo4j
os.environ['CIMG_URL'] = 'neo4j://localhost:7687'
os.environ['CIMG_USERNAME'] = 'neo4j'
os.environ['CIMG_PASSWORD'] = 'password'
neo4j = Neo4jUploader(container='neo4j_cim_loader')
neo4j.upload_from_ttl(filepath='./models', filename='grid.ttl')

# Upload to Oxigraph
os.environ['CIMG_URL'] = 'http://localhost:7878/query'
oxigraph = OxigraphUploader()
oxigraph.upload_from_ntriples(filepath='./models', filename='grid.nt')
```

## Format Compatibility Matrix

| Format | Blazegraph | Neo4j (n10s) | Oxigraph |
|--------|-----------|-------------|----------|
| RDF/XML | ✅ | ✅ | ✅ |
| Turtle | ✅ | ✅ | ✅ |
| N-Triples | ✅ | ✅ | ✅ |
| N-Quads | ✅ | ✅ | ✅ |
| JSON-LD | ✅ | ✅ | ❌ |
| TriG | ✅ | ✅ | ❌ |

Note: All databases support the core RDF formats (RDF/XML, Turtle, N-Triples, N-Quads). JSON-LD and TriG support varies.
