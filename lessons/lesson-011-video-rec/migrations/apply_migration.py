#!/usr/bin/env python3
"""
Apply SurrealDB migration for video recommendation system.

Usage:
    uv run python migrations/apply_migration.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path to access compose.lib
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from compose.lib.env_loader import load_root_env
from compose.services.surrealdb.config import SurrealDBConfig
from surrealdb import AsyncSurreal


async def apply_migration():
    """Apply the video recommendation schema migration."""
    # Load environment variables
    load_root_env()

    # Get config from environment
    config = SurrealDBConfig()
    config.validate()

    # Connect to SurrealDB (running on GPU server)
    # Use HTTP instead of WS for migration
    url = config.url.replace("ws://", "http://")
    db = AsyncSurreal(url)

    # Use namespace/database first
    await db.use(config.namespace, config.database)

    # Sign in
    await db.signin({"username": config.user, "password": config.password})

    print("Connected to SurrealDB")
    print("Applying migration: 001_video_rec_schema.surql")

    # Read migration file
    migration_file = Path(__file__).parent / "001_video_rec_schema.surql"
    migration_sql = migration_file.read_text()

    # Split by semicolons and execute each statement
    statements = [s.strip() for s in migration_sql.split(";") if s.strip() and not s.strip().startswith("--")]

    success_count = 0
    error_count = 0

    for i, statement in enumerate(statements, 1):
        # Skip comments
        if statement.startswith("--"):
            continue

        try:
            await db.query(statement)
            print(f"[OK] Statement {i}/{len(statements)}: {statement[:60]}...")
            success_count += 1
        except Exception as e:
            print(f"[FAIL] Statement {i}/{len(statements)} failed: {e}")
            print(f"  Statement: {statement[:100]}...")
            error_count += 1

    print()
    print(f"Migration complete: {success_count} succeeded, {error_count} failed")

    return error_count == 0


if __name__ == "__main__":
    success = asyncio.run(apply_migration())
    sys.exit(0 if success else 1)
