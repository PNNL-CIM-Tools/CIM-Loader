#!/usr/bin/env python3
"""Example: Migrate CIM data between databases using CIMantic Graphs.

This example shows how to:
1. Load CIM data from one database (Blazegraph)
2. Upload to another database (Neo4j or Oxigraph)
3. Merge multiple feeders into a single graph

Prerequisites:
    - Docker services running: docker-compose up -d
    - Data already loaded in source database
    - CIM profile configured

Usage:
    python examples/migrate_database.py
"""

import os
from cimgraph.models import FeederModel
from cimgraph.databases import BlazegraphConnection
from cimloader.uploaders import Neo4jUploader, OxigraphUploader
import cimgraph.data_profile.rc4_2021 as cim


def migrate_blazegraph_to_neo4j(feeder_mrid: str):
    """Migrate a single feeder from Blazegraph to Neo4j.

    Args:
        feeder_mrid: The mRID of the feeder to migrate
    """
    print("=" * 70)
    print("Migrating from Blazegraph to Neo4j")
    print("=" * 70)

    # Configure source database (Blazegraph)
    os.environ['CIMG_URL'] = 'http://localhost:8889/bigdata/namespace/kb/sparql'
    os.environ['CIMG_CIM_PROFILE'] = 'rc4_2021'
    os.environ['CIMG_NAMESPACE'] = 'http://iec.ch/TC57/CIM100#'

    print(f"\n1. Loading feeder {feeder_mrid} from Blazegraph...")
    blazegraph = BlazegraphConnection()
    feeder = cim.Feeder(mRID=feeder_mrid)
    source_network = FeederModel(container=feeder, connection=blazegraph)

    print(f"   ✓ Loaded {len(source_network.graph)} object types")
    total_objects = sum(len(objs) for objs in source_network.graph.values())
    print(f"   ✓ Total objects: {total_objects}")

    # Configure target database (Neo4j)
    os.environ['CIMG_URL'] = 'neo4j://localhost:7687'
    os.environ['CIMG_USERNAME'] = 'neo4j'
    os.environ['CIMG_PASSWORD'] = 'test1234'
    os.environ['CIMG_DATABASE'] = 'neo4j'

    print(f"\n2. Uploading to Neo4j...")
    neo4j = Neo4jUploader(container='neo4j_cim_loader')
    neo4j.drop_all()  # Clear existing data
    neo4j.configure()  # Setup n10s

    neo4j.upload_from_graphmodel(
        graph_dict=source_network.graph,
        feeder_mrid=feeder_mrid
    )

    print(f"   ✓ Migration complete!")


def migrate_blazegraph_to_oxigraph(feeder_mrid: str):
    """Migrate a single feeder from Blazegraph to Oxigraph.

    Args:
        feeder_mrid: The mRID of the feeder to migrate
    """
    print("=" * 70)
    print("Migrating from Blazegraph to Oxigraph")
    print("=" * 70)

    # Configure source database (Blazegraph)
    os.environ['CIMG_URL'] = 'http://localhost:8889/bigdata/namespace/kb/sparql'
    os.environ['CIMG_CIM_PROFILE'] = 'rc4_2021'
    os.environ['CIMG_NAMESPACE'] = 'http://iec.ch/TC57/CIM100#'

    print(f"\n1. Loading feeder {feeder_mrid} from Blazegraph...")
    blazegraph = BlazegraphConnection()
    feeder = cim.Feeder(mRID=feeder_mrid)
    source_network = FeederModel(container=feeder, connection=blazegraph)

    print(f"   ✓ Loaded {len(source_network.graph)} object types")

    # Configure target database (Oxigraph)
    os.environ['CIMG_URL'] = 'http://localhost:7878/query'

    print(f"\n2. Uploading to Oxigraph...")
    oxigraph = OxigraphUploader()
    oxigraph.drop_all()  # Clear existing data

    oxigraph.upload_from_graphmodel(
        graph_dict=source_network.graph,
        feeder_mrid=feeder_mrid
    )

    print(f"   ✓ Migration complete!")


def merge_multiple_feeders(feeder_mrids: list[str], target_mrid: str = None):
    """Merge multiple feeders from Blazegraph and upload to Neo4j.

    Args:
        feeder_mrids: List of feeder mRIDs to merge
        target_mrid: Optional mRID for the merged feeder
    """
    print("=" * 70)
    print("Merging Multiple Feeders")
    print("=" * 70)

    # Configure source database
    os.environ['CIMG_URL'] = 'http://localhost:8889/bigdata/namespace/kb/sparql'
    os.environ['CIMG_CIM_PROFILE'] = 'rc4_2021'

    blazegraph = BlazegraphConnection()
    merged_graph = None

    print(f"\n1. Loading and merging {len(feeder_mrids)} feeders...")
    for i, mrid in enumerate(feeder_mrids, 1):
        print(f"   Loading feeder {i}/{len(feeder_mrids)}: {mrid}")
        feeder = cim.Feeder(mRID=mrid)

        if merged_graph is None:
            # First feeder - create new graph
            network = FeederModel(container=feeder, connection=blazegraph)
            merged_graph = network.graph
        else:
            # Subsequent feeders - merge into existing graph
            network = FeederModel(
                container=feeder,
                connection=blazegraph,
                graph=merged_graph
            )
            merged_graph = network.graph

    print(f"   ✓ Merged graph has {len(merged_graph)} object types")
    total_objects = sum(len(objs) for objs in merged_graph.values())
    print(f"   ✓ Total objects: {total_objects}")

    # Configure target database
    os.environ['CIMG_URL'] = 'neo4j://localhost:7687'
    os.environ['CIMG_USERNAME'] = 'neo4j'
    os.environ['CIMG_PASSWORD'] = 'test1234'

    print(f"\n2. Uploading merged graph to Neo4j...")
    neo4j = Neo4jUploader(container='neo4j_cim_loader')
    neo4j.drop_all()
    neo4j.configure()

    neo4j.upload_from_graphmodel(
        graph_dict=merged_graph,
        feeder_mrid=target_mrid or 'merged-feeders'
    )

    print(f"   ✓ Merge and upload complete!")


def main():
    """Run migration examples."""
    import sys

    # Example feeder mRID (IEEE 13 bus)
    feeder_mrid = '49AD8E07-3BF9-A4E2-CB8F-C3722F837B62'

    print("\nCIM-Loader Database Migration Examples")
    print("=" * 70)
    print("\nOptions:")
    print("  1. Migrate Blazegraph → Neo4j")
    print("  2. Migrate Blazegraph → Oxigraph")
    print("  3. Merge multiple feeders to Neo4j")
    print("  0. Exit")

    choice = input("\nEnter choice (0-3): ").strip()

    if choice == '1':
        migrate_blazegraph_to_neo4j(feeder_mrid)

    elif choice == '2':
        migrate_blazegraph_to_oxigraph(feeder_mrid)

    elif choice == '3':
        # Example: merge 3 feeders
        feeder_mrids = [
            '49AD8E07-3BF9-A4E2-CB8F-C3722F837B62',
            # Add more feeder mRIDs as needed
        ]
        merge_multiple_feeders(feeder_mrids, target_mrid='merged-example')

    elif choice == '0':
        print("Exiting...")
        return

    else:
        print("Invalid choice")
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
