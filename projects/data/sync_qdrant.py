#!/usr/bin/env python3
"""
Sync and consolidate Qdrant vector databases across machines.

This script:
1. Backs up local Qdrant storage to qdrant.HOSTNAME/ directory
2. Consolidates all machine-specific backups into the main qdrant storage
3. Deduplicates points based on point IDs across all collections
4. Only the main qdrant/ directory is committed (machine backups are gitignored)

Usage:
    python sync_qdrant.py
"""

import shutil
import platform
import sys
from pathlib import Path
from typing import Dict, List, Set
import time

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams, Distance
except ImportError:
    print("Error: qdrant-client not installed. Install with: uv pip install qdrant-client")
    sys.exit(1)


def get_machine_name() -> str:
    """Get the current machine's hostname."""
    return platform.node()


def backup_local_qdrant(source_dir: Path, backup_dir: Path) -> None:
    """
    Create a machine-specific backup of the current Qdrant storage.

    Args:
        source_dir: Main qdrant storage directory
        backup_dir: Machine-specific backup directory
    """
    if not source_dir.exists():
        print(f"No Qdrant storage found at {source_dir}")
        return

    print(f"Backing up local Qdrant storage...")
    print(f"  From: {source_dir}")
    print(f"  To:   {backup_dir}")

    # Remove existing backup
    if backup_dir.exists():
        shutil.rmtree(backup_dir)

    # Copy entire directory structure
    shutil.copytree(source_dir, backup_dir)

    # Calculate backup size
    total_size = sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file())
    size_mb = total_size / (1024 * 1024)

    print(f"[OK] Backup created: {size_mb:.1f} MB")


def get_all_qdrant_dirs(base_dir: Path) -> List[Path]:
    """
    Find all Qdrant storage directories (main + machine backups).

    Args:
        base_dir: Base directory containing qdrant directories

    Returns:
        List of paths to qdrant storage directories
    """
    qdrant_dirs = []

    # Look for directories matching 'qdrant' or 'qdrant.HOSTNAME'
    for item in base_dir.iterdir():
        if item.is_dir() and (item.name == "qdrant" or item.name.startswith("qdrant.")):
            # Skip temporary directories
            if not item.name.endswith(".tmp") and not item.name.startswith("qdrant.old."):
                qdrant_dirs.append(item)

    return qdrant_dirs


def consolidate_qdrant_databases(base_dir: Path) -> None:
    """
    Consolidate all Qdrant databases (main + machine backups) into one.
    Deduplicates points by ID across all collections.

    Args:
        base_dir: Base directory containing qdrant directories
    """
    qdrant_dirs = get_all_qdrant_dirs(base_dir)

    if not qdrant_dirs:
        print("No Qdrant databases to consolidate")
        return

    print(f"\nConsolidating {len(qdrant_dirs)} Qdrant database(s)...")
    for qdir in qdrant_dirs:
        print(f"  - {qdir.name}")

    # Create temporary consolidated database
    temp_dir = base_dir / "qdrant.tmp"
    final_dir = base_dir / "qdrant"

    # Remove any existing temp directory
    if temp_dir.exists():
        shutil.rmtree(temp_dir)

    temp_dir.mkdir(parents=True, exist_ok=True)

    # Initialize temporary client
    temp_client = QdrantClient(path=str(temp_dir))

    # Track statistics per collection
    stats: Dict[str, Dict[str, int]] = {}

    # Get all collections across all databases
    all_collections: Set[str] = set()
    for qdir in qdrant_dirs:
        try:
            client = QdrantClient(path=str(qdir))
            collections = client.get_collections().collections
            for col in collections:
                all_collections.add(col.name)
        except Exception as e:
            print(f"  Warning: Could not read {qdir.name}: {e}")
            continue

    print(f"\nProcessing {len(all_collections)} collection(s)...")

    # Process each collection
    for collection_name in sorted(all_collections):
        print(f"  Collection: {collection_name}")
        stats[collection_name] = {"sources": 0, "points": 0, "duplicates": 0}

        # Track seen point IDs to deduplicate
        seen_ids: Set[str] = set()

        # Get collection config from first available source
        collection_config = None

        # Collect all points from all sources
        for qdir in qdrant_dirs:
            try:
                client = QdrantClient(path=str(qdir))

                # Check if collection exists in this database
                collections = client.get_collections().collections
                collection_names = [c.name for c in collections]

                if collection_name not in collection_names:
                    continue

                stats[collection_name]["sources"] += 1

                # Get collection config on first encounter
                if collection_config is None:
                    collection_info = client.get_collection(collection_name)
                    collection_config = collection_info.config

                    # Create collection in temp database
                    temp_client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=collection_config.params.vectors.size,
                            distance=Distance.COSINE
                        )
                    )

                # Get all points from this collection
                points, next_offset = client.scroll(
                    collection_name=collection_name,
                    limit=10000,  # Batch size
                    with_vectors=True,
                    with_payload=True,
                )

                # Process points and deduplicate
                new_points = []
                for point in points:
                    point_id = str(point.id)

                    if point_id not in seen_ids:
                        seen_ids.add(point_id)
                        new_points.append(point)
                        stats[collection_name]["points"] += 1
                    else:
                        stats[collection_name]["duplicates"] += 1

                # Upsert new points to temp database
                if new_points:
                    temp_client.upsert(
                        collection_name=collection_name,
                        points=new_points
                    )

                # Handle pagination if needed
                while next_offset is not None:
                    points, next_offset = client.scroll(
                        collection_name=collection_name,
                        offset=next_offset,
                        limit=10000,
                        with_vectors=True,
                        with_payload=True,
                    )

                    new_points = []
                    for point in points:
                        point_id = str(point.id)

                        if point_id not in seen_ids:
                            seen_ids.add(point_id)
                            new_points.append(point)
                            stats[collection_name]["points"] += 1
                        else:
                            stats[collection_name]["duplicates"] += 1

                    if new_points:
                        temp_client.upsert(
                            collection_name=collection_name,
                            points=new_points
                        )

            except Exception as e:
                print(f"    Warning: Error processing {qdir.name}/{collection_name}: {e}")
                continue

        print(f"    [OK] {stats[collection_name]['points']} points " +
              f"({stats[collection_name]['duplicates']} duplicates removed)")

    # Close connections before file operations
    del temp_client

    # Replace old database with consolidated one
    if final_dir.exists():
        # Move old database out of the way (Windows-safe)
        old_dir = base_dir / f"qdrant.old.{int(time.time())}"
        final_dir.rename(old_dir)
        temp_dir.rename(final_dir)

        # Try to clean up old directory (best effort)
        try:
            shutil.rmtree(old_dir)
        except:
            print(f"  Note: Old database saved to {old_dir.name} (manual cleanup needed)")
    else:
        temp_dir.rename(final_dir)

    # Print summary
    print("\n[OK] Consolidated database created:")
    total_points = sum(s["points"] for s in stats.values())
    total_dupes = sum(s["duplicates"] for s in stats.values())
    print(f"  Total collections: {len(stats)}")
    print(f"  Total points: {total_points:,}")
    print(f"  Duplicates removed: {total_dupes:,}")

    # Calculate final size
    total_size = sum(f.stat().st_size for f in final_dir.rglob('*') if f.is_file())
    size_mb = total_size / (1024 * 1024)
    print(f"  Storage size: {size_mb:.1f} MB")


def main():
    """Main sync workflow."""
    # Get paths
    script_dir = Path(__file__).parent  # projects/data
    source_dir = script_dir / "qdrant"
    machine_name = get_machine_name()
    backup_dir = script_dir / f"qdrant.{machine_name}"

    # Step 1: Backup local Qdrant storage
    if source_dir.exists():
        backup_local_qdrant(source_dir, backup_dir)
    else:
        print("No local Qdrant storage to backup (first time setup)")

    # Step 2: Consolidate all Qdrant databases
    consolidate_qdrant_databases(script_dir)

    print("\n[OK] Qdrant sync complete!")


if __name__ == "__main__":
    main()
