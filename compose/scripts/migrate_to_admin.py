#!/usr/bin/env python
"""
Migration script to assign existing data to the first admin user.

This script:
1. Finds the first admin user in the database
2. Updates all existing conversations, projects, artifacts, etc. to belong to that admin
3. Is idempotent - safe to run multiple times

Usage:
    cd compose && uv run python scripts/migrate_to_admin.py
"""

import asyncio
import sys
from pathlib import Path

# Add compose to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from compose.services.surrealdb import execute_query


# Tables that need user_id migration
TABLES_TO_MIGRATE = [
    "conversation",
    "project",
    "artifact",
    "backup",
]


async def get_first_admin() -> str | None:
    """Get the ID of the first admin user."""
    results = await execute_query(
        "SELECT id, created_at FROM users WHERE role = 'admin' ORDER BY created_at ASC LIMIT 1"
    )

    if not results:
        return None

    user_id = results[0].get("id", "")
    # SurrealDB returns RecordID object or "users:uuid" format, convert to string
    user_id = str(user_id)
    # Extract just the uuid part if in "users:uuid" format
    if ":" in user_id:
        user_id = user_id.split(":", 1)[1]

    return user_id


async def migrate_table(table: str, admin_id: str) -> int:
    """
    Add user_id to all records in a table that don't have one.

    Returns:
        Number of records updated
    """
    # Count records without user_id
    count_query = f"SELECT count() FROM {table} WHERE user_id = NONE GROUP ALL"
    count_result = await execute_query(count_query)

    if not count_result:
        print(f"  {table}: 0 records to migrate")
        return 0

    count = count_result[0].get("count", 0)

    if count == 0:
        print(f"  {table}: 0 records to migrate")
        return 0

    # Update records
    update_query = f"UPDATE {table} SET user_id = $user_id WHERE user_id = NONE"
    await execute_query(update_query, {"user_id": admin_id})

    print(f"  {table}: {count} records assigned to admin")
    return count


async def main():
    """Run the migration."""
    print("=" * 60)
    print("Migration: Assign existing data to admin user")
    print("=" * 60)
    print()

    # Find admin user
    print("Finding admin user...")
    admin_id = await get_first_admin()

    if not admin_id:
        print("ERROR: No admin user found!")
        print("Please create an admin account first by registering on the platform.")
        print("The first user to register automatically becomes admin.")
        sys.exit(1)

    print(f"Found admin user: {admin_id}")
    print()

    # Migrate each table
    print("Migrating tables...")
    total_migrated = 0

    for table in TABLES_TO_MIGRATE:
        try:
            count = await migrate_table(table, admin_id)
            total_migrated += count
        except Exception as e:
            print(f"  {table}: ERROR - {e}")

    print()
    print("=" * 60)
    print(f"Migration complete! {total_migrated} records assigned to admin.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
