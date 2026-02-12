#!/usr/bin/env python3
"""Quick manual test for Oxigraph uploader.

Simple script to quickly test uploading a file to Oxigraph.
Useful for manual testing and debugging.

Usage:
    python tests/quick_test_oxigraph.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from cimloader.databases import OxigraphConnection
from cimloader.uploaders import OxigraphUploader


def main():
    print("=" * 70)
    print("Oxigraph Quick Test")
    print("=" * 70)

    # Set environment variables
    os.environ['OXIGRAPH_URL'] = 'http://localhost:7878/query'
    os.environ['CIM_NAMESPACE'] = 'http://iec.ch/TC57/CIM100#'
    os.environ['CIM_PROFILE'] = 'RC4_2021'

    # Test file
    filepath = str(Path(__file__).parent / 'test_models')
    filename = 'ieee13_seto.xml'
    full_path = f"{filepath}/{filename}"

    print(f"\nTest file: {full_path}")
    print(f"File exists: {Path(full_path).exists()}")
    print(f"File size: {Path(full_path).stat().st_size:,} bytes")

    # Ask user for test mode
    print("\nTest modes:")
    print("  1. Direct upload (Oxigraph accessible from host)")
    print("  2. Container upload (via Docker)")
    print("  3. Just clear database")
    print("  4. Just count triples")

    choice = input("\nEnter choice (1-4): ").strip()

    try:
        connection = OxigraphConnection()

        if choice == '3':
            print("\nClearing database...")
            connection.drop_all()
            print("✓ Database cleared")
            return

        if choice == '4':
            print("\nCounting triples...")
            query = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o . }"
            result = connection.execute(query)
            count = int(result['results']['bindings'][0]['count']['value'])
            print(f"✓ Total triples: {count:,}")
            return

        # Clear database first
        print("\nClearing existing data...")
        connection.drop_all()
        print("✓ Database cleared")

        # Count before
        query = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o . }"
        result = connection.execute(query)
        before_count = int(result['results']['bindings'][0]['count']['value'])
        print(f"Triples before: {before_count}")

        # Upload
        if choice == '1':
            print(f"\nUploading {filename} (direct mode)...")
            uploader = OxigraphUploader()
            uploader.upload_from_file(filepath=filepath, filename=filename)

        elif choice == '2':
            print(f"\nUploading {filename} (container mode)...")
            uploader = OxigraphUploader(container='oxigraph_cim_loader')
            uploader.upload_from_file(filepath=filepath, filename=filename)

        else:
            print("Invalid choice")
            return

        print("✓ Upload completed")

        # Count after
        result = connection.execute(query)
        after_count = int(result['results']['bindings'][0]['count']['value'])
        print(f"Triples after: {after_count:,}")
        print(f"Added: {after_count - before_count:,} triples")

        # Query for some CIM objects
        print("\nQuerying for CIM objects...")
        cim_query = """
        PREFIX cim: <http://iec.ch/TC57/CIM100#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?type (COUNT(?obj) AS ?count)
        WHERE {
            ?obj rdf:type ?type .
            FILTER(STRSTARTS(STR(?type), "http://iec.ch/TC57/CIM100#"))
        }
        GROUP BY ?type
        ORDER BY DESC(?count)
        LIMIT 10
        """
        result = connection.execute(cim_query)
        print("\nTop 10 CIM classes:")
        for binding in result['results']['bindings']:
            type_uri = binding['type']['value']
            count = binding['count']['value']
            # Extract class name from URI
            class_name = type_uri.split('#')[-1]
            print(f"  {class_name:30s}: {count:>5s}")

        print("\n✅ Test completed successfully!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
