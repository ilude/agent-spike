#!/usr/bin/env python
"""
Migration script: JSON data -> SurrealDB + MinIO

Migrates existing JSON-based storage for:
- Conversations (with messages)
- Artifacts (code/documents)
- Projects (with files uploaded to MinIO)

Usage:
    uv run python compose/cli/migrate_data.py [--dry-run] [--force]

Examples:
    # Preview migrations
    uv run python compose/cli/migrate_data.py --dry-run

    # Migrate all data (skip existing)
    uv run python compose/cli/migrate_data.py

    # Force overwrite existing data
    uv run python compose/cli/migrate_data.py --force
"""

import asyncio
import json
import logging
import mimetypes
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

# Setup script environment before imports
sys.path.insert(0, str(Path(__file__).parent))
from compose.cli.base import setup_script_environment

setup_script_environment(load_env=True)

import typer
from rich.console import Console

from compose.services.minio.factory import create_minio_client
from compose.services.surrealdb.driver import execute_query
from compose.services.surrealdb.repository import init_schema

logger = logging.getLogger(__name__)

app = typer.Typer(help="Migrate JSON data to SurrealDB + MinIO")
console = Console(force_terminal=True, force_interactive=False, width=120)

# Data directories (relative to project root)
DATA_DIR = Path("compose/data")
CONVERSATIONS_DIR = DATA_DIR / "conversations"
ARTIFACTS_DIR = DATA_DIR / "artifacts"
PROJECTS_DIR = DATA_DIR / "projects"


# Migration statistics
class MigrationStats:
    """Track migration statistics."""

    def __init__(self):
        self.conversations = 0
        self.messages = 0
        self.artifacts = 0
        self.projects = 0
        self.files = 0
        self.project_conversations = 0
        self.errors = []

    def print_summary(self):
        """Print migration summary."""
        console.print("\n[bold green]Migration complete![/]")
        console.print(f"  Conversations: {self.conversations}")
        console.print(f"  Messages: {self.messages}")
        console.print(f"  Artifacts: {self.artifacts}")
        console.print(f"  Projects: {self.projects}")
        console.print(f"  Files: {self.files}")
        console.print(f"  Project-Conversation links: {self.project_conversations}")

        if self.errors:
            console.print(f"\n[yellow]Errors ({len(self.errors)}):[/]")
            for error in self.errors[:10]:
                console.print(f"  - {error}")
            if len(self.errors) > 10:
                console.print(f"  ... and {len(self.errors) - 10} more errors")


async def check_exists(table: str, id_value: str) -> bool:
    """Check if a record exists in SurrealDB."""
    query = f"SELECT id FROM {table} WHERE id = $id LIMIT 1;"
    results = await execute_query(query, {"id": id_value})
    return len(results) > 0


async def migrate_conversations(
    stats: MigrationStats,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    """Migrate conversations from JSON to SurrealDB."""
    if not CONVERSATIONS_DIR.exists():
        console.print(f"[yellow]Conversations directory not found: {CONVERSATIONS_DIR}[/]")
        return

    index_file = CONVERSATIONS_DIR / "index.json"
    if not index_file.exists():
        console.print(f"[yellow]No conversations index.json found[/]")
        return

    console.print("[bold blue]Migrating conversations...[/]")

    with open(index_file) as f:
        conversations_index = json.load(f)

    for conv_entry in conversations_index:
        conv_id = conv_entry.get("id")
        if not conv_id:
            continue

        conv_file = CONVERSATIONS_DIR / f"{conv_id}.json"
        if not conv_file.exists():
            stats.errors.append(f"Conversation file not found: {conv_file}")
            continue

        try:
            with open(conv_file) as f:
                conv_data = json.load(f)

            # Check if exists
            if not force and not dry_run:
                if await check_exists("conversation", conv_id):
                    console.print(f"  - [dim]Skipped conversation {conv_id} (exists)[/]")
                    continue

            messages = conv_data.get("messages", [])

            if dry_run:
                console.print(f"  - [dim]Would migrate conversation {conv_id} ({len(messages)} messages)[/]")
                continue

            # Insert conversation
            conv_query = """
            INSERT INTO conversation {
                id: $id,
                title: $title,
                model: $model,
                created_at: $created_at,
                updated_at: $updated_at
            };
            """

            created_at = conv_data.get("created_at") or conv_entry.get("created_at")
            updated_at = conv_data.get("updated_at") or conv_entry.get("updated_at")

            await execute_query(conv_query, {
                "id": conv_id,
                "title": conv_data.get("title", conv_entry.get("title", "Untitled")),
                "model": conv_data.get("model"),
                "created_at": created_at or datetime.now().isoformat(),
                "updated_at": updated_at or datetime.now().isoformat(),
            })
            stats.conversations += 1

            # Insert messages
            for msg in messages:
                msg_id = msg.get("id")
                if not msg_id:
                    continue

                msg_query = """
                INSERT INTO message {
                    id: $id,
                    conversation_id: $conversation_id,
                    role: $role,
                    content: $content,
                    sources: $sources,
                    timestamp: $timestamp
                };
                """

                await execute_query(msg_query, {
                    "id": msg_id,
                    "conversation_id": conv_id,
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                    "sources": msg.get("sources", []),
                    "timestamp": msg.get("timestamp") or datetime.now().isoformat(),
                })
                stats.messages += 1

            console.print(f"  - Migrated conversation {conv_id} ({len(messages)} messages)")

        except Exception as e:
            stats.errors.append(f"Conversation {conv_id}: {str(e)}")
            console.print(f"  - [red]Error migrating {conv_id}: {e}[/]")


async def migrate_artifacts(
    stats: MigrationStats,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    """Migrate artifacts from JSON to SurrealDB."""
    if not ARTIFACTS_DIR.exists():
        console.print(f"[yellow]Artifacts directory not found: {ARTIFACTS_DIR}[/]")
        return

    index_file = ARTIFACTS_DIR / "index.json"
    if not index_file.exists():
        console.print(f"[yellow]No artifacts index.json found[/]")
        return

    console.print("[bold blue]Migrating artifacts...[/]")

    with open(index_file) as f:
        artifacts_index = json.load(f)

    for artifact_entry in artifacts_index:
        artifact_id = artifact_entry.get("id")
        if not artifact_id:
            continue

        artifact_file = ARTIFACTS_DIR / f"{artifact_id}.json"
        if not artifact_file.exists():
            stats.errors.append(f"Artifact file not found: {artifact_file}")
            continue

        try:
            with open(artifact_file) as f:
                artifact_data = json.load(f)

            # Check if exists
            if not force and not dry_run:
                if await check_exists("artifact", artifact_id):
                    console.print(f"  - [dim]Skipped artifact {artifact_id} (exists)[/]")
                    continue

            if dry_run:
                console.print(f"  - [dim]Would migrate artifact {artifact_id}[/]")
                continue

            # Insert artifact
            artifact_query = """
            INSERT INTO artifact {
                id: $id,
                title: $title,
                artifact_type: $artifact_type,
                language: $language,
                content: $content,
                preview: $preview,
                conversation_id: $conversation_id,
                project_id: $project_id,
                created_at: $created_at,
                updated_at: $updated_at
            };
            """

            content = artifact_data.get("content", "")
            preview = content[:200] if content else ""

            await execute_query(artifact_query, {
                "id": artifact_id,
                "title": artifact_data.get("title", "Untitled"),
                "artifact_type": artifact_data.get("artifact_type", artifact_data.get("type", "document")),
                "language": artifact_data.get("language"),
                "content": content,
                "preview": preview,
                "conversation_id": artifact_data.get("conversation_id"),
                "project_id": artifact_data.get("project_id"),
                "created_at": artifact_data.get("created_at") or datetime.now().isoformat(),
                "updated_at": artifact_data.get("updated_at") or datetime.now().isoformat(),
            })
            stats.artifacts += 1

            console.print(f"  - Migrated artifact {artifact_id}")

        except Exception as e:
            stats.errors.append(f"Artifact {artifact_id}: {str(e)}")
            console.print(f"  - [red]Error migrating {artifact_id}: {e}[/]")


async def migrate_projects(
    stats: MigrationStats,
    minio_client: Optional[object] = None,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    """Migrate projects from JSON to SurrealDB + MinIO."""
    if not PROJECTS_DIR.exists():
        console.print(f"[yellow]Projects directory not found: {PROJECTS_DIR}[/]")
        return

    index_file = PROJECTS_DIR / "index.json"
    if not index_file.exists():
        console.print(f"[yellow]No projects index.json found[/]")
        return

    console.print("[bold blue]Migrating projects...[/]")

    with open(index_file) as f:
        projects_index = json.load(f)

    for project_entry in projects_index:
        project_id = project_entry.get("id")
        if not project_id:
            continue

        project_dir = PROJECTS_DIR / project_id
        project_file = project_dir / "project.json"

        if not project_file.exists():
            # Try root-level file
            project_file = PROJECTS_DIR / f"{project_id}.json"
            if not project_file.exists():
                stats.errors.append(f"Project file not found for {project_id}")
                continue

        try:
            with open(project_file) as f:
                project_data = json.load(f)

            # Check if exists
            if not force and not dry_run:
                if await check_exists("project", project_id):
                    console.print(f"  - [dim]Skipped project {project_id} (exists)[/]")
                    continue

            files = project_data.get("files", [])
            conversations = project_data.get("conversations", [])

            if dry_run:
                console.print(f"  - [dim]Would migrate project {project_id} ({len(files)} files)[/]")
                continue

            # Insert project
            project_query = """
            INSERT INTO project {
                id: $id,
                name: $name,
                description: $description,
                custom_instructions: $custom_instructions,
                created_at: $created_at,
                updated_at: $updated_at
            };
            """

            await execute_query(project_query, {
                "id": project_id,
                "name": project_data.get("name", project_entry.get("name", "Untitled")),
                "description": project_data.get("description"),
                "custom_instructions": project_data.get("custom_instructions"),
                "created_at": project_data.get("created_at") or datetime.now().isoformat(),
                "updated_at": project_data.get("updated_at") or datetime.now().isoformat(),
            })
            stats.projects += 1

            # Process files
            files_dir = project_dir / "files"
            for file_info in files:
                file_id = file_info.get("id")
                filename = file_info.get("filename")
                original_filename = file_info.get("original_filename", filename)

                if not file_id or not filename:
                    continue

                # Find the file (could be stored as {file_id}_{filename} or just filename)
                possible_paths = [
                    files_dir / f"{file_id}_{filename}",
                    files_dir / filename,
                    files_dir / f"{file_id}_{original_filename}",
                    files_dir / original_filename,
                ]

                file_path = None
                for p in possible_paths:
                    if p.exists():
                        file_path = p
                        break

                if not file_path:
                    stats.errors.append(f"File not found for project {project_id}: {filename}")
                    continue

                try:
                    # Upload to MinIO
                    minio_key = f"projects/{project_id}/{file_id}_{original_filename}"
                    size_bytes = file_path.stat().st_size

                    if minio_client:
                        with open(file_path, "rb") as f:
                            content = f.read()

                        content_type = file_info.get("content_type")
                        if not content_type:
                            content_type, _ = mimetypes.guess_type(original_filename)
                            content_type = content_type or "application/octet-stream"

                        minio_client.client.put_object(
                            minio_client.bucket,
                            minio_key,
                            BytesIO(content),
                            len(content),
                            content_type=content_type,
                        )

                    # Insert file record
                    file_query = """
                    INSERT INTO project_file {
                        id: $id,
                        project_id: $project_id,
                        filename: $filename,
                        original_filename: $original_filename,
                        content_type: $content_type,
                        size_bytes: $size_bytes,
                        minio_key: $minio_key,
                        processed: $processed,
                        qdrant_indexed: $qdrant_indexed,
                        uploaded_at: $uploaded_at
                    };
                    """

                    content_type = file_info.get("content_type")
                    if not content_type:
                        content_type, _ = mimetypes.guess_type(original_filename)
                        content_type = content_type or "application/octet-stream"

                    await execute_query(file_query, {
                        "id": file_id,
                        "project_id": project_id,
                        "filename": filename,
                        "original_filename": original_filename,
                        "content_type": content_type,
                        "size_bytes": size_bytes,
                        "minio_key": minio_key,
                        "processed": file_info.get("processed", False),
                        "qdrant_indexed": file_info.get("qdrant_indexed", False),
                        "uploaded_at": file_info.get("uploaded_at") or datetime.now().isoformat(),
                    })
                    stats.files += 1

                    # Format file size nicely
                    size_str = _format_size(size_bytes)
                    console.print(f"    - Uploaded file: {original_filename} ({size_str})")

                except Exception as e:
                    stats.errors.append(f"File {file_id} in project {project_id}: {str(e)}")
                    console.print(f"    - [red]Error uploading {filename}: {e}[/]")

            # Link conversations to project
            for conv_id in conversations:
                if isinstance(conv_id, dict):
                    conv_id = conv_id.get("id", conv_id.get("conversation_id"))

                if not conv_id:
                    continue

                try:
                    link_query = """
                    INSERT INTO project_conversation {
                        project_id: $project_id,
                        conversation_id: $conversation_id,
                        created_at: $created_at
                    };
                    """

                    await execute_query(link_query, {
                        "project_id": project_id,
                        "conversation_id": conv_id,
                        "created_at": datetime.now().isoformat(),
                    })
                    stats.project_conversations += 1

                except Exception as e:
                    # May fail if relationship already exists
                    logger.debug(f"Project-conversation link error: {e}")

            console.print(f"  - Migrated project {project_id} ({len(files)} files)")

        except Exception as e:
            stats.errors.append(f"Project {project_id}: {str(e)}")
            console.print(f"  - [red]Error migrating {project_id}: {e}[/]")


def _format_size(size_bytes: int) -> str:
    """Format file size as human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


@app.command()
def migrate(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be migrated without doing it",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing data in SurrealDB",
    ),
):
    """Migrate JSON data to SurrealDB + MinIO."""

    stats = MigrationStats()

    if dry_run:
        console.print("[yellow]DRY RUN - no changes will be made[/]\n")
    elif force:
        console.print("[yellow]FORCE MODE - existing data will be overwritten[/]\n")

    # Initialize clients
    minio_client = None
    if not dry_run:
        try:
            minio_client = create_minio_client()
            console.print("[green]OK MinIO client initialized[/]")
        except Exception as e:
            console.print(f"[red]Failed to initialize MinIO: {e}[/]")
            console.print("[yellow]Continuing without file uploads...[/]")

    async def run_migrations():
        """Run all migrations asynchronously."""
        # Initialize SurrealDB schema
        console.print("Initializing SurrealDB schema...")
        if not dry_run:
            try:
                await init_schema()
                console.print("[green]OK SurrealDB schema initialized[/]\n")
            except Exception as e:
                console.print(f"[yellow]Schema init warning: {e}[/]\n")
        else:
            console.print("[dim]Skipping schema init (dry run)[/]\n")

        # Run migrations
        await migrate_conversations(stats, dry_run=dry_run, force=force)
        await migrate_artifacts(stats, dry_run=dry_run, force=force)
        await migrate_projects(stats, minio_client=minio_client, dry_run=dry_run, force=force)

    # Run migrations
    asyncio.run(run_migrations())

    # Print summary
    stats.print_summary()


@app.command()
def status():
    """Show current data status (what's available to migrate)."""

    console.print("[bold blue]Data Migration Status[/]\n")

    # Check conversations
    if CONVERSATIONS_DIR.exists():
        index_file = CONVERSATIONS_DIR / "index.json"
        if index_file.exists():
            with open(index_file) as f:
                conversations = json.load(f)
            console.print(f"[green]Conversations: {len(conversations)} found[/]")
        else:
            console.print("[yellow]Conversations: no index.json[/]")
    else:
        console.print(f"[dim]Conversations: directory not found ({CONVERSATIONS_DIR})[/]")

    # Check artifacts
    if ARTIFACTS_DIR.exists():
        index_file = ARTIFACTS_DIR / "index.json"
        if index_file.exists():
            with open(index_file) as f:
                artifacts = json.load(f)
            console.print(f"[green]Artifacts: {len(artifacts)} found[/]")
        else:
            console.print("[yellow]Artifacts: no index.json[/]")
    else:
        console.print(f"[dim]Artifacts: directory not found ({ARTIFACTS_DIR})[/]")

    # Check projects
    if PROJECTS_DIR.exists():
        index_file = PROJECTS_DIR / "index.json"
        if index_file.exists():
            with open(index_file) as f:
                projects = json.load(f)
            console.print(f"[green]Projects: {len(projects)} found[/]")

            # Count files
            total_files = 0
            for project in projects:
                project_id = project.get("id")
                if project_id:
                    project_dir = PROJECTS_DIR / project_id
                    project_file = project_dir / "project.json"
                    if project_file.exists():
                        with open(project_file) as f:
                            project_data = json.load(f)
                        total_files += len(project_data.get("files", []))
            if total_files:
                console.print(f"  [dim]Total files: {total_files}[/]")
        else:
            console.print("[yellow]Projects: no index.json[/]")
    else:
        console.print(f"[dim]Projects: directory not found ({PROJECTS_DIR})[/]")


if __name__ == "__main__":
    app()
