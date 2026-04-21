#!/usr/bin/env python3
"""Example: Using CIM-Loader with AWS Neptune.

This example demonstrates basic usage of Neptune connector.

Prerequisites:
    - AWS account with Neptune cluster
    - Network access to Neptune (VPC, VPN, Direct Connect)
    - Neptune with IAM auth disabled (for testing) OR AWS credentials configured

Setup:
    export CIMG_URL='https://your-cluster.neptune.amazonaws.com:8182/sparql'
    export AWS_REGION='us-east-1'
    # Optional: export AWS_ACCESS_KEY_ID='...'
    # Optional: export AWS_SECRET_ACCESS_KEY='...'

Usage:
    python examples/neptune_example.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from cimloader.databases import NeptuneConnection
from cimloader.uploaders import NeptuneUploader


def check_neptune_configured():
    """Check if Neptune endpoint is configured."""
    url = os.environ.get('CIMG_URL', '')
    if 'neptune' not in url.lower():
        print("❌ Neptune endpoint not configured")
        print("\nPlease set environment variable:")
        print("  export CIMG_URL='https://your-cluster.neptune.amazonaws.com:8182/sparql'")
        print("\nSee docs/NEPTUNE.md for setup instructions.")
        return False
    return True


def test_connection():
    """Test Neptune connection."""
    print("=" * 70)
    print("Testing Neptune Connection")
    print("=" * 70)

    try:
        connection = NeptuneConnection()
        print(f"\n✓ Created connection to: {connection.url}")

        # Try a simple query
        print("\nExecuting test query...")
        query = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o . }"
        result = connection.execute(query)

        count = int(result['results']['bindings'][0]['count']['value'])
        print(f"✓ Query successful! Triple count: {count:,}")

        return True

    except Exception as e:
        error_msg = str(e)
        if '403' in error_msg or 'Forbidden' in error_msg:
            print("\n⚠️  Authentication error (403 Forbidden)")
            print("\nOptions:")
            print("1. Disable IAM auth on Neptune (development only)")
            print("2. Implement AWS SigV4 authentication (see docs/NEPTUNE.md)")
            print("3. Configure AWS credentials:")
            print("   export AWS_ACCESS_KEY_ID='...'")
            print("   export AWS_SECRET_ACCESS_KEY='...'")
        else:
            print(f"\n❌ Connection failed: {error_msg}")

        return False


def upload_example():
    """Example of uploading CIM data to Neptune."""
    print("\n" + "=" * 70)
    print("Uploading CIM Data to Neptune")
    print("=" * 70)

    # Check for test file
    test_file = project_root / 'tests' / 'test_models' / 'ieee13_seto.xml'
    if not test_file.exists():
        print(f"\n❌ Test file not found: {test_file}")
        return False

    try:
        uploader = NeptuneUploader()
        print(f"\n✓ Created uploader for: {uploader.url}")

        print(f"\nUploading {test_file.name}...")
        uploader.upload_from_file(
            filepath=str(test_file.parent),
            filename=test_file.name
        )

        print("✓ Upload completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Upload failed: {e}")
        return False


def query_example():
    """Example queries against Neptune."""
    print("\n" + "=" * 70)
    print("Querying CIM Data from Neptune")
    print("=" * 70)

    try:
        connection = NeptuneConnection()

        # Query for CIM Feeders
        print("\n1. Searching for Feeders...")
        query = """
        PREFIX cim: <http://iec.ch/TC57/CIM100#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?feeder ?name
        WHERE {
            ?feeder rdf:type cim:Feeder .
            OPTIONAL { ?feeder cim:IdentifiedObject.name ?name . }
        }
        LIMIT 10
        """
        result = connection.execute(query)
        feeders = result['results']['bindings']

        if feeders:
            print(f"   ✓ Found {len(feeders)} feeder(s):")
            for feeder in feeders:
                name = feeder.get('name', {}).get('value', 'Unnamed')
                print(f"      - {name}")
        else:
            print("   ℹ No feeders found (database may be empty)")

        # Count ACLineSegments
        print("\n2. Counting ACLineSegments...")
        query = """
        PREFIX cim: <http://iec.ch/TC57/CIM100#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT (COUNT(?line) AS ?count)
        WHERE {
            ?line rdf:type cim:ACLineSegment .
        }
        """
        result = connection.execute(query)
        count = int(result['results']['bindings'][0]['count']['value'])
        print(f"   ✓ Found {count} ACLineSegment(s)")

        return True

    except Exception as e:
        print(f"\n❌ Query failed: {e}")
        return False


def migration_example():
    """Example of migrating data from Blazegraph to Neptune."""
    print("\n" + "=" * 70)
    print("Database Migration: Blazegraph → Neptune")
    print("=" * 70)

    print("\nThis example requires:")
    print("1. Blazegraph running with data")
    print("2. Neptune endpoint configured")

    response = input("\nDo you have data in Blazegraph? (y/n): ").strip().lower()
    if response != 'y':
        print("Skipping migration example.")
        return False

    try:
        from cimgraph.models import FeederModel
        from cimgraph.databases import BlazegraphConnection
        import cimgraph.data_profile.rc4_2021 as cim

        feeder_mrid = input("Enter Feeder mRID: ").strip()
        if not feeder_mrid:
            print("No feeder mRID provided. Skipping.")
            return False

        # Load from Blazegraph
        print("\n1. Loading from Blazegraph...")
        blazegraph_url = input("   Blazegraph URL (or press Enter for default): ").strip()
        if not blazegraph_url:
            blazegraph_url = 'http://localhost:8889/bigdata/namespace/kb/sparql'

        os.environ['CIMG_URL'] = blazegraph_url
        blazegraph = BlazegraphConnection()
        feeder = cim.Feeder(mRID=feeder_mrid)
        source = FeederModel(container=feeder, connection=blazegraph)

        print(f"   ✓ Loaded {len(source.graph)} object types")

        # Upload to Neptune
        print("\n2. Uploading to Neptune...")
        # Neptune URL should already be set
        neptune = NeptuneUploader()
        neptune.upload_from_graphmodel(source.graph, feeder_mrid=feeder_mrid)

        print("   ✓ Migration completed!")
        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        return False


def main():
    """Run Neptune examples."""
    print("\nCIM-Loader AWS Neptune Examples")
    print("=" * 70)

    # Check configuration
    if not check_neptune_configured():
        return 1

    # Set CIM configuration
    os.environ['CIMG_CIM_PROFILE'] = 'rc4_2021'
    os.environ['CIMG_NAMESPACE'] = 'http://iec.ch/TC57/CIM100#'

    # Menu
    print("\nOptions:")
    print("  1. Test connection")
    print("  2. Upload example file")
    print("  3. Run example queries")
    print("  4. Migrate from Blazegraph")
    print("  0. Exit")

    choice = input("\nEnter choice (0-4): ").strip()

    if choice == '1':
        success = test_connection()
    elif choice == '2':
        success = upload_example()
    elif choice == '3':
        success = query_example()
    elif choice == '4':
        success = migration_example()
    elif choice == '0':
        print("Exiting...")
        return 0
    else:
        print("Invalid choice")
        return 1

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
