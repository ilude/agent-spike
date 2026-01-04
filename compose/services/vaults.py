"""Vault service for managing markdown note vaults.

Vaults are containers for notes, similar to Obsidian vaults.
Supports MinIO storage for note content with SurrealDB for metadata.
"""

import re
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from .minio.client import MinIOClient
from .minio.config import MinIOConfig
from .surrealdb.driver import execute_query
from .surrealdb.models import FileTreeNode, VaultRecord


class VaultMeta(BaseModel):
    """Lightweight vault metadata for listings."""

    id: str
    name: str
    slug: str
    storage_type: str
    note_count: int = 0
    created_at: datetime
    updated_at: datetime


class Vault(VaultMeta):
    """Full vault with settings."""

    minio_bucket: Optional[str] = None
    settings: dict = {}


def _parse_datetime(value) -> datetime:
    """Parse datetime from SurrealDB result."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.now()


def _slugify(name: str) -> str:
    """Convert name to URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _record_to_vault(record: dict, note_count: int = 0) -> Vault:
    """Convert SurrealDB record to Vault model."""
    record_id = str(record.get("id", ""))
    if ":" in record_id:
        record_id = record_id.split(":", 1)[1]

    return Vault(
        id=record_id,
        name=record.get("name", ""),
        slug=record.get("slug", ""),
        storage_type=record.get("storage_type", "minio"),
        minio_bucket=record.get("minio_bucket"),
        settings=record.get("settings", {}),
        note_count=note_count,
        created_at=_parse_datetime(record.get("created_at")),
        updated_at=_parse_datetime(record.get("updated_at")),
    )


def _record_to_meta(record: dict, note_count: int = 0) -> VaultMeta:
    """Convert SurrealDB record to VaultMeta model."""
    record_id = str(record.get("id", ""))
    if ":" in record_id:
        record_id = record_id.split(":", 1)[1]

    return VaultMeta(
        id=record_id,
        name=record.get("name", ""),
        slug=record.get("slug", ""),
        storage_type=record.get("storage_type", "minio"),
        note_count=note_count,
        created_at=_parse_datetime(record.get("created_at")),
        updated_at=_parse_datetime(record.get("updated_at")),
    )


class VaultService:
    """Service for managing vault storage."""

    def __init__(self):
        """Initialize vault service with MinIO client."""
        config = MinIOConfig()
        config.bucket = "mentat-vaults"
        self._minio = MinIOClient(config)
        self._minio.ensure_bucket()

    async def list_vaults(self) -> list[VaultMeta]:
        """List all vaults with note counts.

        Returns:
            List of vault metadata sorted by updated_at desc
        """
        query = """
        SELECT
            *,
            (SELECT count() FROM note WHERE vault_id = $parent.id GROUP ALL)[0].count AS note_count
        FROM vault
        ORDER BY updated_at DESC;
        """

        results = await execute_query(query)

        vaults = []
        for r in results:
            note_count = r.get("note_count")
            if note_count is None:
                note_count = 0
            elif isinstance(note_count, list):
                note_count = note_count[0] if note_count else 0
            vaults.append(_record_to_meta(r, note_count))

        return vaults

    async def create_vault(
        self,
        name: str,
        storage_type: str = "minio",
        settings: Optional[dict] = None,
    ) -> Vault:
        """Create a new vault.

        Args:
            name: Vault display name
            storage_type: "minio" or "local"
            settings: Vault-specific settings

        Returns:
            Created vault
        """
        vault_id = str(uuid.uuid4())
        slug = _slugify(name)

        # Ensure unique slug
        existing = await execute_query(
            "SELECT id FROM vault WHERE slug = $slug LIMIT 1;",
            {"slug": slug},
        )
        if existing:
            slug = f"{slug}-{vault_id[:8]}"

        minio_bucket = "mentat-vaults" if storage_type == "minio" else None

        query = """
        CREATE vault SET
            id = $id,
            name = $name,
            slug = $slug,
            storage_type = $storage_type,
            minio_bucket = $minio_bucket,
            settings = $settings,
            created_at = time::now(),
            updated_at = time::now();
        """

        params = {
            "id": vault_id,
            "name": name,
            "slug": slug,
            "storage_type": storage_type,
            "minio_bucket": minio_bucket,
            "settings": settings or {},
        }

        results = await execute_query(query, params)

        if results:
            return _record_to_vault(results[0])

        now = datetime.utcnow()
        return Vault(
            id=vault_id,
            name=name,
            slug=slug,
            storage_type=storage_type,
            minio_bucket=minio_bucket,
            settings=settings or {},
            note_count=0,
            created_at=now,
            updated_at=now,
        )

    async def get_vault(self, vault_id: str) -> Optional[Vault]:
        """Get vault by ID.

        Args:
            vault_id: Vault ID

        Returns:
            Vault or None if not found
        """
        # SurrealDB stores IDs as table:id format, so we need to use record syntax
        query = """
        SELECT
            *,
            (SELECT count() FROM note WHERE vault_id = $parent.id GROUP ALL)[0].count AS note_count
        FROM type::thing("vault", $id)
        LIMIT 1;
        """

        results = await execute_query(query, {"id": vault_id})

        if not results:
            return None

        r = results[0]
        note_count = r.get("note_count")
        if note_count is None:
            note_count = 0
        elif isinstance(note_count, list):
            note_count = note_count[0] if note_count else 0

        return _record_to_vault(r, note_count)

    async def get_vault_by_slug(self, slug: str) -> Optional[Vault]:
        """Get vault by slug.

        Args:
            slug: URL-safe vault identifier

        Returns:
            Vault or None if not found
        """
        query = """
        SELECT
            *,
            (SELECT count() FROM note WHERE vault_id = $parent.id GROUP ALL)[0].count AS note_count
        FROM vault
        WHERE slug = $slug
        LIMIT 1;
        """

        results = await execute_query(query, {"slug": slug})

        if not results:
            return None

        r = results[0]
        note_count = r.get("note_count")
        if note_count is None:
            note_count = 0
        elif isinstance(note_count, list):
            note_count = note_count[0] if note_count else 0

        return _record_to_vault(r, note_count)

    async def update_vault(
        self,
        vault_id: str,
        name: Optional[str] = None,
        settings: Optional[dict] = None,
    ) -> Optional[Vault]:
        """Update vault metadata.

        Args:
            vault_id: Vault ID
            name: New name (optional)
            settings: New settings (optional)

        Returns:
            Updated vault or None if not found
        """
        set_parts = ["updated_at = time::now()"]
        params = {"id": vault_id}

        if name is not None:
            set_parts.append("name = $name")
            params["name"] = name
            # Update slug too
            slug = _slugify(name)
            set_parts.append("slug = $slug")
            params["slug"] = slug

        if settings is not None:
            set_parts.append("settings = $settings")
            params["settings"] = settings

        query = f"""
        UPDATE vault SET {", ".join(set_parts)}
        WHERE id = $id;
        """

        results = await execute_query(query, params)

        if not results:
            return None

        return _record_to_vault(results[0])

    async def delete_vault(self, vault_id: str) -> bool:
        """Delete vault and all its notes.

        Args:
            vault_id: Vault ID

        Returns:
            True if deleted, False if not found
        """
        # Check if exists
        check_query = "SELECT id FROM vault WHERE id = $id LIMIT 1;"
        exists = await execute_query(check_query, {"id": vault_id})

        if not exists:
            return False

        # Delete all notes in vault first
        await execute_query("DELETE note WHERE vault_id = $id;", {"id": vault_id})

        # Delete note links involving this vault's notes
        await execute_query(
            """
            DELETE note_link WHERE source_id IN
            (SELECT id FROM note WHERE vault_id = $id);
            """,
            {"id": vault_id},
        )

        # Delete entities for this vault
        await execute_query("DELETE entity WHERE vault_id = $id;", {"id": vault_id})

        # Delete the vault
        await execute_query("DELETE vault WHERE id = $id;", {"id": vault_id})

        return True

    async def get_file_tree(self, vault_id: str) -> list[FileTreeNode]:
        """Get file tree structure for a vault.

        Args:
            vault_id: Vault ID

        Returns:
            List of root-level FileTreeNode objects representing folder/file structure
        """
        query = """
        SELECT id, path, title FROM note
        WHERE vault_id = $vault_id
        ORDER BY path ASC;
        """

        results = await execute_query(query, {"vault_id": vault_id})

        # Build tree from flat path list
        root_nodes: dict[str, FileTreeNode] = {}

        for r in results:
            path = r.get("path", "")
            title = r.get("title", "Untitled")
            note_id = str(r.get("id", ""))
            if ":" in note_id:
                note_id = note_id.split(":", 1)[1]

            parts = path.split("/")

            # Create folder nodes as needed
            current_dict = root_nodes
            current_path = ""

            for i, part in enumerate(parts[:-1]):
                current_path = f"{current_path}/{part}" if current_path else part

                if part not in current_dict:
                    folder_node = FileTreeNode(
                        name=part,
                        path=current_path,
                        type="folder",
                        children=[],
                    )
                    current_dict[part] = folder_node

                # Navigate into children dict
                folder = current_dict[part]
                if not hasattr(folder, "_children_dict"):
                    folder._children_dict = {}
                current_dict = folder._children_dict

            # Add file node
            filename = parts[-1]
            file_node = FileTreeNode(
                name=filename,
                path=path,
                type="file",
                note_id=note_id,
            )
            current_dict[filename] = file_node

        # Convert nested dicts to children lists
        def flatten_dict(d: dict) -> list[FileTreeNode]:
            result = []
            for node in d.values():
                if hasattr(node, "_children_dict"):
                    node.children = flatten_dict(node._children_dict)
                    delattr(node, "_children_dict")
                result.append(node)
            # Sort: folders first, then alphabetically
            result.sort(key=lambda n: (0 if n.type == "folder" else 1, n.name.lower()))
            return result

        return flatten_dict(root_nodes)

    def get_minio_path(self, vault_slug: str, note_path: str) -> str:
        """Get MinIO object path for a note.

        Args:
            vault_slug: Vault slug
            note_path: Note path within vault

        Returns:
            Full MinIO object path
        """
        return f"{vault_slug}/notes/{note_path}"

    def save_note_content(self, vault_slug: str, note_path: str, content: str) -> str:
        """Save note content to MinIO.

        Args:
            vault_slug: Vault slug
            note_path: Note path within vault
            content: Markdown content

        Returns:
            MinIO path where content was saved
        """
        minio_path = self.get_minio_path(vault_slug, note_path)
        return self._minio.put_text(minio_path, content)

    def get_note_content(self, vault_slug: str, note_path: str) -> Optional[str]:
        """Get note content from MinIO.

        Args:
            vault_slug: Vault slug
            note_path: Note path within vault

        Returns:
            Note content or None if not found
        """
        minio_path = self.get_minio_path(vault_slug, note_path)
        if not self._minio.exists(minio_path):
            return None
        return self._minio.get_text(minio_path)

    def delete_note_content(self, vault_slug: str, note_path: str) -> None:
        """Delete note content from MinIO.

        Args:
            vault_slug: Vault slug
            note_path: Note path within vault
        """
        minio_path = self.get_minio_path(vault_slug, note_path)
        if self._minio.exists(minio_path):
            self._minio.delete(minio_path)


# Singleton service instance
_vault_service: Optional[VaultService] = None


def get_vault_service() -> VaultService:
    """Get vault service singleton."""
    global _vault_service
    if _vault_service is None:
        _vault_service = VaultService()
    return _vault_service
