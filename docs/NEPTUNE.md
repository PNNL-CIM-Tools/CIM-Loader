# AWS Neptune Integration

AWS Neptune is Amazon's fully managed graph database service that supports both RDF (SPARQL) and Property Graph (Gremlin) models.

For CIM data, CIM-Loader uses the SPARQL 1.1 endpoint.

## Status: Experimental ⚠️

The Neptune connector is currently **experimental** and has the following limitations:

### ✅ Implemented
- Basic SPARQL query/update via SPARQLWrapper
- File upload via HTTP POST (small datasets)
- Format auto-detection (RDF/XML, Turtle, N-Triples, N-Quads)
- GraphModel upload for database migration
- Environment variable configuration

### ⚠️ Not Yet Implemented
- **AWS Signature V4 authentication** - Required for IAM-authenticated Neptune instances
- **S3 bulk loader integration** - Recommended method for large datasets
- **Load status checking** - Monitor progress of bulk loads
- **Comprehensive error handling** - AWS-specific error codes

### 🔍 Needs Research
- Neptune-specific SPARQL extensions/limitations
- Optimal upload methods for different data sizes
- Performance characteristics vs Blazegraph
- Cost optimization strategies

## Prerequisites

### 1. AWS Neptune Cluster

You need a running Neptune cluster. Options:

**Development/Testing:**
```bash
# Create a Neptune cluster with IAM auth disabled (easier for testing)
aws neptune create-db-cluster \
    --db-cluster-identifier my-cim-cluster \
    --engine neptune \
    --enable-iam-database-authentication false
```

**Production:**
```bash
# Create with IAM auth enabled (recommended)
aws neptune create-db-cluster \
    --db-cluster-identifier my-cim-cluster \
    --engine neptune \
    --enable-iam-database-authentication true \
    --vpc-security-group-ids sg-xxxxx
```

### 2. Network Access

Neptune runs in a VPC. You need:
- EC2 instance in same VPC, OR
- VPN/Direct Connect to VPC, OR
- Neptune VPC endpoint configured

### 3. IAM Permissions

If using IAM authentication:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "neptune-db:*"
      ],
      "Resource": "arn:aws:neptune-db:region:account-id:cluster-id/*"
    }
  ]
}
```

## Configuration

### Environment Variables

```python
import os

# Neptune SPARQL endpoint
os.environ['CIMG_URL'] = 'https://my-cluster.cluster-xyz.us-east-1.neptune.amazonaws.com:8182/sparql'

# CIM configuration
os.environ['CIMG_CIM_PROFILE'] = 'rc4_2021'
os.environ['CIMG_NAMESPACE'] = 'http://iec.ch/TC57/CIM100#'

# AWS authentication (if using IAM)
os.environ['AWS_REGION'] = 'us-east-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'your-access-key'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'your-secret-key'
# os.environ['AWS_SESSION_TOKEN'] = 'token'  # For temporary credentials
```

### Neptune Endpoint Format

```
https://<cluster-endpoint>:<port>/sparql

Examples:
- https://my-cluster.cluster-xyz.us-east-1.neptune.amazonaws.com:8182/sparql
- https://my-cluster.us-east-1.neptune.amazonaws.com:8182/sparql
```

## Usage

### Basic Upload

```python
from cimloader.uploaders import NeptuneUploader
import os

# Configure
os.environ['CIMG_URL'] = 'https://my-cluster.cluster-xyz.us-east-1.neptune.amazonaws.com:8182/sparql'

# Upload file
uploader = NeptuneUploader()
uploader.upload_from_file(filepath='./models', filename='grid.xml')
```

### Querying Data

```python
from cimloader.databases import NeptuneConnection

connection = NeptuneConnection()

# Count triples
query = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }"
result = connection.execute(query)
count = int(result['results']['bindings'][0]['count']['value'])
print(f"Total triples: {count}")
```

### Database Migration

```python
from cimgraph.models import FeederModel
from cimgraph.databases import BlazegraphConnection
from cimloader.uploaders import NeptuneUploader
import cimgraph.data_profile.rc4_2021 as cim

# Load from Blazegraph
os.environ['CIMG_URL'] = 'http://localhost:8889/bigdata/namespace/kb/sparql'
blazegraph = BlazegraphConnection()
feeder = cim.Feeder(mRID='feeder-123')
source = FeederModel(container=feeder, connection=blazegraph)

# Upload to Neptune
os.environ['CIMG_URL'] = 'https://my-cluster.cluster-xyz.us-east-1.neptune.amazonaws.com:8182/sparql'
neptune = NeptuneUploader()
neptune.upload_from_graphmodel(source.graph, feeder_mrid='feeder-123')
```

## Current Limitations

### 1. Authentication

**Issue:** AWS SigV4 authentication not implemented

**Workaround:** Use Neptune with IAM auth disabled (development only)

**To Fix:** Need to implement SigV4 signing. Options:
- Use AWS4Auth from requests-aws4auth library
- Use boto3's request signer
- Implement manual signing (complex)

### 2. Large Datasets

**Issue:** HTTP POST has size limits and is slow for large files

**Solution:** Use Neptune's bulk loader (not yet implemented)

```python
# Future API (not yet working):
uploader.upload_to_s3_and_load(
    filepath='./models',
    filename='large_grid.xml',
    s3_bucket='my-neptune-data',
    s3_key='cim/large_grid.xml',
    iam_role_arn='arn:aws:iam::123456789012:role/NeptuneLoadRole'
)
```

### 3. Error Handling

**Issue:** AWS-specific errors not handled

**Workaround:** Check CloudWatch logs for Neptune errors

## Performance Considerations

### Small Datasets (<10MB)
- Use `upload_from_file()` - Works fine via HTTP POST
- Similar performance to Blazegraph

### Medium Datasets (10MB-1GB)
- Consider using multiple smaller files
- Or implement S3 bulk loader

### Large Datasets (>1GB)
- **Must use S3 bulk loader** (not yet implemented)
- Neptune bulk loader is optimized for large datasets
- Can load terabytes of data efficiently

## Cost Optimization

Neptune pricing:
- Instance costs (db.r5.large, db.r6g.xlarge, etc.)
- Storage costs (per GB-month)
- I/O costs (per million requests)
- Backup storage

Tips:
1. Use appropriate instance size for workload
2. Consider serverless for variable workloads
3. Use bulk loader to reduce I/O costs
4. Monitor with CloudWatch

## Development Roadmap

### Phase 1: Basic Functionality (Current)
- [x] SPARQL query/update via SPARQLWrapper
- [x] HTTP POST file upload
- [x] Format auto-detection
- [x] GraphModel upload

### Phase 2: AWS Integration (TODO)
- [ ] AWS SigV4 authentication
- [ ] IAM role assumption
- [ ] S3 bulk loader integration
- [ ] Load status monitoring

### Phase 3: Optimization (Future)
- [ ] Connection pooling
- [ ] Batch upload optimization
- [ ] CloudWatch metrics
- [ ] Cost tracking

### Phase 4: Advanced Features (Future)
- [ ] Neptune Streams integration
- [ ] Full-text search (if available)
- [ ] Graph algorithms (if available)

## Testing

### Prerequisites
- AWS account with Neptune access
- Neptune cluster running
- Network connectivity to cluster

### Run Tests
```bash
# Set Neptune endpoint
export CIMG_URL='https://my-cluster.cluster-xyz.us-east-1.neptune.amazonaws.com:8182/sparql'
export AWS_REGION='us-east-1'

# Run Neptune-specific tests
pytest tests/test_neptune.py -v

# Skip if Neptune not available
pytest tests/ -v -m "not neptune"
```

## Troubleshooting

### Connection Timeout
```
Error: Connection timeout to Neptune endpoint
```

**Solution:**
- Check VPC connectivity
- Verify security group allows inbound on port 8182
- Ensure you're connecting from within VPC or via VPN

### Authentication Error
```
Error: 403 Forbidden
```

**Solution:**
- Check IAM permissions
- Verify AWS credentials are set
- Try disabling IAM auth on Neptune (dev only)

### SPARQL Syntax Error
```
Error: Malformed query
```

**Solution:**
- Neptune uses SPARQL 1.1 standard
- Check for Neptune-specific limitations
- Test query in Neptune workbench first

## Resources

- [Neptune Documentation](https://docs.aws.amazon.com/neptune/latest/userguide/)
- [SPARQL Support](https://docs.aws.amazon.com/neptune/latest/userguide/sparql-api.html)
- [Bulk Loader](https://docs.aws.amazon.com/neptune/latest/userguide/bulk-load.html)
- [IAM Authentication](https://docs.aws.amazon.com/neptune/latest/userguide/iam-auth.html)
- [Neptune Pricing](https://aws.amazon.com/neptune/pricing/)

## Contributing

Help us improve Neptune support! Especially needed:

1. **AWS Authentication Implementation**
   - SigV4 signing for requests
   - IAM role integration
   - Temporary credential handling

2. **S3 Bulk Loader**
   - Upload to S3
   - Initiate bulk load
   - Monitor load status
   - Handle errors

3. **Performance Testing**
   - Benchmark vs Blazegraph
   - Optimal instance sizes
   - Query performance

4. **Documentation**
   - Neptune-specific SPARQL features
   - Best practices for CIM data
   - Cost optimization strategies

## Questions?

If you're using Neptune with CIM-Loader, please share:
- Your Neptune configuration
- Any issues or solutions you found
- Performance characteristics
- Documentation gaps

Open an issue on GitHub with your findings!
