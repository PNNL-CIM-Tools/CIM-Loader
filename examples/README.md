# CIM-Loader Examples

This directory contains example scripts demonstrating various use cases for CIM-Loader.

## Prerequisites

All examples require:
- Docker services running: `docker-compose up -d`
- Python environment with CIM-Loader installed: `pip install -e .`
- Environment variables configured (see `.env.example`)

## Examples

### migrate_database.py

**Database Migration and Graph Merging**

Demonstrates how to:
- Migrate CIM data from one database to another (Blazegraph → Neo4j/Oxigraph)
- Merge multiple feeders into a single graph
- Use CIMantic Graphs `FeederModel` with `graph` parameter

**Usage:**
```bash
python examples/migrate_database.py
```

**Key Features:**
- Load data from source database using CIMantic Graphs
- Transfer to target database using `upload_from_graphmodel()`
- Merge multiple feeders by passing `graph` parameter

**Common Use Cases:**
1. **Migrate to faster database**: Move from Blazegraph to Oxigraph for better performance
2. **Multi-database architecture**: Keep data in multiple databases (SPARQL + Graph)
3. **Data consolidation**: Merge regional feeders into a single national grid model
4. **Backup and restore**: Export from one database, import to another

## Running Examples

### Basic Migration

Migrate a single feeder from Blazegraph to Neo4j:

```bash
# 1. Upload data to Blazegraph first
python -c "
from cimloader.uploaders import BlazegraphUploader
import os
os.environ['CIMG_URL'] = 'http://localhost:8889/bigdata/namespace/kb/sparql'
uploader = BlazegraphUploader()
uploader.upload_from_file(filepath='./tests/test_models', filename='ieee13_seto.xml')
"

# 2. Run migration example
python examples/migrate_database.py
# Choose option 1
```

### Merging Feeders

```python
# First, ensure you have multiple feeders in Blazegraph
from examples.migrate_database import merge_multiple_feeders

feeder_mrids = [
    '49AD8E07-3BF9-A4E2-CB8F-C3722F837B62',
    '8ef3f7b6-25be-476f-af48-2dcf85042b36',
    'f856769a-363c-401e-a0cd-bd0a48b83ef0'
]

merge_multiple_feeders(feeder_mrids, target_mrid='merged-grid')
```

## Creating Your Own Examples

### Template Structure

```python
#!/usr/bin/env python3
"""Description of what this example does."""

import os
from cimloader.uploaders import BlazegraphUploader
import cimgraph.data_profile.rc4_2021 as cim

def main():
    # Configure environment
    os.environ['CIMG_CIM_PROFILE'] = 'rc4_2021'
    os.environ['CIMG_URL'] = 'http://localhost:8889/bigdata/namespace/kb/sparql'

    # Your code here
    uploader = BlazegraphUploader()
    uploader.upload_from_file(filepath='./models', filename='grid.xml')

if __name__ == '__main__':
    main()
```

### Best Practices

1. **Document prerequisites** at the top of each example
2. **Use environment variables** for configuration
3. **Add error handling** for common issues
4. **Print progress messages** so users can follow along
5. **Clean up** resources (clear databases, close connections)

## Common Patterns

### Database Migration

```python
from cimgraph.models import FeederModel
from cimgraph.databases import BlazegraphConnection
from cimloader.uploaders import Neo4jUploader

# Load from source
blazegraph = BlazegraphConnection()
feeder = cim.Feeder(mRID='feeder-123')
source = FeederModel(container=feeder, connection=blazegraph)

# Upload to target
neo4j = Neo4jUploader()
neo4j.upload_from_graphmodel(source.graph, feeder_mrid='feeder-123')
```

### Format Conversion

```python
from cimloader.uploaders import OxigraphUploader

# Upload XML file
uploader = OxigraphUploader()
uploader.upload_from_file(filepath='./models', filename='grid.xml')

# Oxigraph can export as Turtle, N-Triples, etc.
# Then download in different format
```

### Batch Processing

```python
import glob
from cimloader.uploaders import BlazegraphUploader

uploader = BlazegraphUploader()

for xml_file in glob.glob('./models/*.xml'):
    filename = os.path.basename(xml_file)
    filepath = os.path.dirname(xml_file)
    uploader.upload_from_file(filepath=filepath, filename=filename)
    print(f"Uploaded {filename}")
```

## Troubleshooting

### Docker Services Not Running

```bash
# Check services
docker-compose ps

# Start all services
docker-compose up -d

# Check specific service logs
docker-compose logs blazegraph
docker-compose logs neo4j-apoc
```

### Environment Variables Not Set

```bash
# Check current values
env | grep CIMG_

# Set required variables
export CIMG_URL='http://localhost:8889/bigdata/namespace/kb/sparql'
export CIMG_CIM_PROFILE='rc4_2021'
export CIMG_NAMESPACE='http://iec.ch/TC57/CIM100#'
```

### Import Errors

```bash
# Reinstall in development mode
pip install -e .

# Or install with all dependencies
pip install -e ".[dev,test]"
```

## Contributing Examples

Have a useful example? Please contribute!

1. Create a new Python file in `examples/`
2. Follow the template structure above
3. Add documentation to this README
4. Test with `docker-compose up -d`
5. Submit a pull request

Examples we'd love to see:
- Real-world feeder merging scenarios
- Performance benchmarking between databases
- Data validation workflows
- Integration with GridAPPS-D
- Custom CIM transformations
