"""Note service for managing markdown notes within vaults.

Handles:
- Note CRUD operations
- Wiki-link parsing and management
- Backlinks and outlinks
- Graph data generation
- AI suggestion integration
"""

import re
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from .surrealdb.driver import execute_query
from .surrealdb.models import (
    AISuggestionRecord,
    GraphData,
    GraphEdge,
    GraphNode,
    NoteLinkRecord,
    NoteRecord,
)
from .vaults import get_vault_service


class NoteMeta(BaseModel):
    """Lightweight note metadata for listings."""

    id: str
    vault_id: str
    path: str
    title: str
    preview: Optional[str] = None
    word_count: int = 0
    created_at: datetime
    updated_at: datetime


class Note(NoteMeta):
    """Full note with content."""

    content: str
    embedding: Optional[list[float]] = None
    ai_processed_at: Optional[datetime] = None


class NoteLink(BaseModel):
    """Link between notes."""

    id: str
    source_id: str
    target_id: Optional[str]
    link_text: str
    link_type: str
    accepted: bool
    confidence: Optional[float]
    # Enriched with note info
    source_title: Optional[str] = None
    target_title: Optional[str] = None
    target_path: Optional[str] = None


def _parse_datetime(value) -> datetime:
    """Parse datetime from SurrealDB result."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.now()


def _extract_id(record_id: str) -> str:
    """Extract ID from SurrealDB record format (table:uuid)."""
    if ":" in str(record_id):
        return str(record_id).split(":", 1)[1]
    return str(record_id)


def _record_to_note(record: dict) -> Note:
    """Convert SurrealDB record to Note model."""
    return Note(
        id=_extract_id(record.get("id", "")),
        vault_id=record.get("vault_id", ""),
        path=record.get("path", ""),
        title=record.get("title", ""),
        content=record.get("content", ""),
        preview=record.get("preview"),
        word_count=record.get("word_count", 0),
        embedding=record.get("embedding"),
        ai_processed_at=_parse_datetime(record.get("ai_processed_at"))
        if record.get("ai_processed_at")
        else None,
        created_at=_parse_datetime(record.get("created_at")),
        updated_at=_parse_datetime(record.get("updated_at")),
    )


def _record_to_meta(record: dict) -> NoteMeta:
    """Convert SurrealDB record to NoteMeta model."""
    return NoteMeta(
        id=_extract_id(record.get("id", "")),
        vault_id=record.get("vault_id", ""),
        path=record.get("path", ""),
        title=record.get("title", ""),
        preview=record.get("preview"),
        word_count=record.get("word_count", 0),
        created_at=_parse_datetime(record.get("created_at")),
        updated_at=_parse_datetime(record.get("updated_at")),
    )


def _count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def _generate_preview(content: str, max_length: int = 200) -> str:
    """Generate preview from content."""
    # Strip markdown headers and formatting
    preview = re.sub(r"^#+\s+", "", content, flags=re.MULTILINE)
    preview = re.sub(r"\*\*|__|\*|_", "", preview)
    preview = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", preview)
    preview = re.sub(r"\[\[([^\]]+)\]\]", r"\1", preview)
    preview = preview.strip()

    if len(preview) > max_length:
        preview = preview[:max_length] + "..."

    return preview


def _extract_title(content: str, path: str) -> str:
    """Extract title from content or path.

    Looks for first H1 header, falls back to filename.
    """
    # Look for # Title
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()

    # Fall back to filename without extension
    filename = path.split("/")[-1]
    if filename.endswith(".md"):
        filename = filename[:-3]

    return filename


class NoteService:
    """Service for managing notes and links."""

    # Regex for [[wiki-links]] with optional |alias
    WIKI_LINK_PATTERN = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")

    async def list_notes(
        self,
        vault_id: str,
        folder_path: Optional[str] = None,
    ) -> list[NoteMeta]:
        """List notes in a vault, optionally filtered by folder.

        Args:
            vault_id: Vault ID
            folder_path: Filter to notes under this path

        Returns:
            List of note metadata sorted by updated_at desc
        """
        # vault_id stored as record reference, convert string param
        conditions = ["vault_id = type::thing($vault_id)"]
        params = {"vault_id": f"vault:{vault_id}"}

        if folder_path:
            conditions.append("string::startsWith(path, $folder_path)")
            params["folder_path"] = folder_path

        where_clause = " AND ".join(conditions)

        query = f"""
        SELECT id, vault_id, path, title, preview, word_count, created_at, updated_at
        FROM note
        WHERE {where_clause}
        ORDER BY updated_at DESC;
        """

        results = await execute_query(query, params)
        return [_record_to_meta(r) for r in results]

    async def create_note(
        self,
        vault_id: str,
        path: str,
        content: str = "",
        title: Optional[str] = None,
    ) -> Note:
        """Create a new note.

        Args:
            vault_id: Vault ID
            path: Note path within vault (e.g., "inbox/idea.md")
            content: Markdown content
            title: Optional title (extracted from content if not provided)

        Returns:
            Created note
        """
        note_id = str(uuid.uuid4())

        # Ensure .md extension
        if not path.endswith(".md"):
            path = f"{path}.md"

        # Extract title from content if not provided
        if not title:
            title = _extract_title(content, path)

        preview = _generate_preview(content)
        word_count = _count_words(content)

        # Store vault_id as record reference for proper joins
        query = """
        CREATE note SET
            id = $id,
            vault_id = type::thing($vault_id),
            path = $path,
            title = $title,
            content = $content,
            preview = $preview,
            word_count = $word_count,
            created_at = time::now(),
            updated_at = time::now();
        """

        params = {
            "id": note_id,
            "vault_id": f"vault:{vault_id}",
            "path": path,
            "title": title,
            "content": content,
            "preview": preview,
            "word_count": word_count,
        }

        results = await execute_query(query, params)

        # Save to MinIO
        vault_service = get_vault_service()
        vault = await vault_service.get_vault(vault_id)
        if vault and vault.storage_type == "minio":
            vault_service.save_note_content(vault.slug, path, content)

        # Parse and create wiki-links
        await self._sync_links_from_content(note_id, vault_id, content)

        if results:
            return _record_to_note(results[0])

        now = datetime.utcnow()
        return Note(
            id=note_id,
            vault_id=vault_id,
            path=path,
            title=title,
            content=content,
            preview=preview,
            word_count=word_count,
            created_at=now,
            updated_at=now,
        )

    async def get_note(self, note_id: str) -> Optional[Note]:
        """Get note by ID.

        Args:
            note_id: Note ID

        Returns:
            Note or None if not found
        """
        query = "SELECT * FROM note WHERE id = $id LIMIT 1;"
        results = await execute_query(query, {"id": note_id})

        if not results:
            return None

        return _record_to_note(results[0])

    async def get_note_by_path(self, vault_id: str, path: str) -> Optional[Note]:
        """Get note by vault and path.

        Args:
            vault_id: Vault ID
            path: Note path

        Returns:
            Note or None if not found
        """
        # vault_id stored as record reference
        query = """
        SELECT * FROM note
        WHERE vault_id = type::thing($vault_id) AND path = $path
        LIMIT 1;
        """
        results = await execute_query(query, {"vault_id": f"vault:{vault_id}", "path": path})

        if not results:
            return None

        return _record_to_note(results[0])

    async def update_note(
        self,
        note_id: str,
        content: Optional[str] = None,
        title: Optional[str] = None,
        path: Optional[str] = None,
    ) -> Optional[Note]:
        """Update a note.

        Args:
            note_id: Note ID
            content: New content (optional)
            title: New title (optional)
            path: New path for move/rename (optional)

        Returns:
            Updated note or None if not found
        """
        # Get current note for MinIO operations
        current = await self.get_note(note_id)
        if not current:
            return None

        set_parts = ["updated_at = time::now()"]
        params = {"id": note_id}

        if content is not None:
            set_parts.append("content = $content")
            params["content"] = content
            set_parts.append("preview = $preview")
            params["preview"] = _generate_preview(content)
            set_parts.append("word_count = $word_count")
            params["word_count"] = _count_words(content)

            # Update title from content if not explicitly provided
            if title is None:
                title = _extract_title(content, current.path)
                set_parts.append("title = $title")
                params["title"] = title

        if title is not None and "title = $title" not in set_parts:
            set_parts.append("title = $title")
            params["title"] = title

        if path is not None:
            if not path.endswith(".md"):
                path = f"{path}.md"
            set_parts.append("path = $path")
            params["path"] = path

        query = f"""
        UPDATE note SET {", ".join(set_parts)}
        WHERE id = $id;
        """

        results = await execute_query(query, params)

        if not results:
            return None

        note = _record_to_note(results[0])

        # Update MinIO
        vault_service = get_vault_service()
        vault = await vault_service.get_vault(note.vault_id)
        if vault and vault.storage_type == "minio":
            # If path changed, delete old and create new
            if path is not None and path != current.path:
                vault_service.delete_note_content(vault.slug, current.path)
            vault_service.save_note_content(vault.slug, note.path, note.content)

        # Re-sync wiki-links if content changed
        if content is not None:
            await self._sync_links_from_content(note_id, note.vault_id, content)

        return note

    async def delete_note(self, note_id: str) -> bool:
        """Delete a note.

        Args:
            note_id: Note ID

        Returns:
            True if deleted, False if not found
        """
        # Get note for MinIO cleanup
        note = await self.get_note(note_id)
        if not note:
            return False

        # Delete links (note_link stores record references)
        await execute_query(
            "DELETE note_link WHERE source_id = type::thing($id) OR target_id = type::thing($id);",
            {"id": f"note:{note_id}"},
        )

        # Delete AI suggestions
        await execute_query(
            "DELETE ai_suggestion WHERE note_id = $id;",
            {"id": note_id},
        )

        # Delete note-entity relationships
        await execute_query(
            "DELETE note_entity WHERE note_id = $id;",
            {"id": note_id},
        )

        # Delete note
        await execute_query("DELETE type::thing($table, $id);", {"table": "note", "id": note_id})

        # Delete from MinIO
        vault_service = get_vault_service()
        vault = await vault_service.get_vault(note.vault_id)
        if vault and vault.storage_type == "minio":
            vault_service.delete_note_content(vault.slug, note.path)

        return True

    # =========================================================================
    # Wiki-Link Management
    # =========================================================================

    def parse_wiki_links(self, content: str) -> list[tuple[str, Optional[str]]]:
        """Extract [[wiki-links]] from content.

        Args:
            content: Markdown content

        Returns:
            List of (link_text, alias) tuples
        """
        return self.WIKI_LINK_PATTERN.findall(content)

    async def _sync_links_from_content(
        self, note_id: str, vault_id: str, content: str
    ) -> None:
        """Parse content and sync wiki-links to database.

        Removes old links and creates new ones.
        """
        # Delete existing manual links from this note
        await execute_query(
            "DELETE note_link WHERE source_id = type::thing($id) AND link_type = 'manual';",
            {"id": f"note:{note_id}"},
        )

        # Parse links from content
        links = self.parse_wiki_links(content)

        for link_text, alias in links:
            # Try to resolve target
            target_id = await self._resolve_link_target(vault_id, link_text)

            link_id = str(uuid.uuid4())
            query = """
            CREATE note_link SET
                id = $id,
                source_id = $source_id,
                target_id = $target_id,
                link_text = $link_text,
                link_type = 'manual',
                accepted = true,
                created_at = time::now();
            """

            await execute_query(query, {
                "id": link_id,
                "source_id": note_id,
                "target_id": target_id,
                "link_text": link_text,
            })

    async def _resolve_link_target(
        self, vault_id: str, link_text: str
    ) -> Optional[str]:
        """Find note matching link text.

        Matches by title (case-insensitive) or path.
        """
        # Try exact title match (vault_id stored as record reference)
        query = """
        SELECT id FROM note
        WHERE vault_id = type::thing($vault_id)
        AND (
            string::lowercase(title) = string::lowercase($link_text)
            OR path = $path
            OR string::endsWith(path, $path_suffix)
        )
        LIMIT 1;
        """

        results = await execute_query(query, {
            "vault_id": f"vault:{vault_id}",
            "link_text": link_text,
            "path": f"{link_text}.md",
            "path_suffix": f"/{link_text}.md",
        })

        if results:
            return _extract_id(results[0].get("id", ""))

        return None

    async def get_outlinks(self, note_id: str) -> list[NoteLink]:
        """Get links from a note to other notes.

        Args:
            note_id: Source note ID

        Returns:
            List of outgoing links
        """
        query = """
        SELECT
            *,
            (SELECT title FROM note WHERE id = $parent.target_id)[0].title AS target_title,
            (SELECT path FROM note WHERE id = $parent.target_id)[0].path AS target_path
        FROM note_link
        WHERE source_id = type::thing($note_id) AND accepted = true
        ORDER BY created_at ASC;
        """

        results = await execute_query(query, {"note_id": f"note:{note_id}"})

        links = []
        for r in results:
            links.append(NoteLink(
                id=_extract_id(r.get("id", "")),
                source_id=r.get("source_id", ""),
                target_id=r.get("target_id"),
                link_text=r.get("link_text", ""),
                link_type=r.get("link_type", "manual"),
                accepted=r.get("accepted", True),
                confidence=r.get("confidence"),
                target_title=r.get("target_title"),
                target_path=r.get("target_path"),
            ))

        return links

    async def get_backlinks(self, note_id: str) -> list[NoteLink]:
        """Get links to a note from other notes.

        Args:
            note_id: Target note ID

        Returns:
            List of incoming links (backlinks)
        """
        query = """
        SELECT
            *,
            (SELECT title FROM note WHERE id = $parent.source_id)[0].title AS source_title
        FROM note_link
        WHERE target_id = type::thing($note_id) AND accepted = true
        ORDER BY created_at DESC;
        """

        results = await execute_query(query, {"note_id": f"note:{note_id}"})

        links = []
        for r in results:
            links.append(NoteLink(
                id=_extract_id(r.get("id", "")),
                source_id=r.get("source_id", ""),
                target_id=r.get("target_id"),
                link_text=r.get("link_text", ""),
                link_type=r.get("link_type", "manual"),
                accepted=r.get("accepted", True),
                confidence=r.get("confidence"),
                source_title=r.get("source_title"),
            ))

        return links

    async def create_link(
        self,
        source_id: str,
        target_id: str,
        link_text: str,
        link_type: str = "manual",
    ) -> NoteLink:
        """Create a link between notes.

        Args:
            source_id: Source note ID
            target_id: Target note ID
            link_text: Display text
            link_type: Type of link

        Returns:
            Created link
        """
        link_id = str(uuid.uuid4())

        query = """
        CREATE note_link SET
            id = $id,
            source_id = $source_id,
            target_id = $target_id,
            link_text = $link_text,
            link_type = $link_type,
            accepted = true,
            created_at = time::now();
        """

        await execute_query(query, {
            "id": link_id,
            "source_id": source_id,
            "target_id": target_id,
            "link_text": link_text,
            "link_type": link_type,
        })

        return NoteLink(
            id=link_id,
            source_id=source_id,
            target_id=target_id,
            link_text=link_text,
            link_type=link_type,
            accepted=True,
            confidence=None,
        )

    async def delete_link(self, link_id: str) -> bool:
        """Delete a link.

        Args:
            link_id: Link ID

        Returns:
            True if deleted
        """
        await execute_query("DELETE note_link WHERE id = $id;", {"id": link_id})
        return True

    # =========================================================================
    # Graph Data
    # =========================================================================

    async def get_graph_data(self, vault_id: str) -> GraphData:
        """Get graph data for visualization.

        Args:
            vault_id: Vault ID

        Returns:
            GraphData with nodes and edges
        """
        # Get all notes (vault_id stored as record reference)
        vault_ref = f"vault:{vault_id}"
        notes_query = """
        SELECT id, title FROM note
        WHERE vault_id = type::thing($vault_id);
        """
        notes = await execute_query(notes_query, {"vault_id": vault_ref})

        # Get all links (filter by notes in vault)
        links_query = """
        SELECT source_id, target_id FROM note_link
        WHERE source_id IN (SELECT id FROM note WHERE vault_id = type::thing($vault_id))
        AND target_id IS NOT NULL
        AND accepted = true;
        """
        links = await execute_query(links_query, {"vault_id": vault_ref})

        # Count links per note for sizing
        link_counts: dict[str, int] = {}
        for link in links:
            src = link.get("source_id", "")
            tgt = link.get("target_id", "")
            link_counts[src] = link_counts.get(src, 0) + 1
            link_counts[tgt] = link_counts.get(tgt, 0) + 1

        # Build nodes
        nodes = []
        for n in notes:
            note_id = _extract_id(n.get("id", ""))
            nodes.append(GraphNode(
                id=note_id,
                title=n.get("title", ""),
                type="note",
                size=link_counts.get(note_id, 1),
            ))

        # Build edges
        edges = []
        for link in links:
            edges.append(GraphEdge(
                source=link.get("source_id", ""),
                target=link.get("target_id", ""),
                type="wiki-link",
            ))

        return GraphData(nodes=nodes, edges=edges)

    # =========================================================================
    # AI Suggestions
    # =========================================================================

    async def get_suggestions(
        self,
        note_id: str,
        status: str = "pending",
    ) -> list[AISuggestionRecord]:
        """Get AI suggestions for a note.

        Args:
            note_id: Note ID
            status: Filter by status

        Returns:
            List of suggestions
        """
        query = """
        SELECT * FROM ai_suggestion
        WHERE note_id = $note_id AND status = $status
        ORDER BY confidence DESC;
        """

        results = await execute_query(query, {
            "note_id": note_id,
            "status": status,
        })

        return [
            AISuggestionRecord(
                id=_extract_id(r.get("id", "")),
                note_id=r.get("note_id", ""),
                suggestion_type=r.get("suggestion_type", ""),
                suggestion_data=r.get("suggestion_data", {}),
                confidence=r.get("confidence", 0.0),
                status=r.get("status", "pending"),
                created_at=_parse_datetime(r.get("created_at")),
                resolved_at=_parse_datetime(r.get("resolved_at"))
                if r.get("resolved_at")
                else None,
            )
            for r in results
        ]

    async def accept_suggestion(self, suggestion_id: str) -> bool:
        """Accept an AI suggestion.

        Args:
            suggestion_id: Suggestion ID

        Returns:
            True if accepted
        """
        # Get suggestion
        query = "SELECT * FROM ai_suggestion WHERE id = $id LIMIT 1;"
        results = await execute_query(query, {"id": suggestion_id})

        if not results:
            return False

        suggestion = results[0]

        # Handle based on type
        if suggestion.get("suggestion_type") == "link":
            data = suggestion.get("suggestion_data", {})
            await self.create_link(
                source_id=suggestion.get("note_id"),
                target_id=data.get("target_id"),
                link_text=data.get("link_text", ""),
                link_type="ai_suggested",
            )

        # Update status
        await execute_query(
            """
            UPDATE ai_suggestion SET
                status = 'accepted',
                resolved_at = time::now()
            WHERE id = $id;
            """,
            {"id": suggestion_id},
        )

        return True

    async def reject_suggestion(self, suggestion_id: str) -> bool:
        """Reject an AI suggestion.

        Args:
            suggestion_id: Suggestion ID

        Returns:
            True if rejected
        """
        await execute_query(
            """
            UPDATE ai_suggestion SET
                status = 'rejected',
                resolved_at = time::now()
            WHERE id = $id;
            """,
            {"id": suggestion_id},
        )

        return True

    async def search_notes(
        self,
        vault_id: str,
        query_text: str,
        limit: int = 20,
    ) -> list[NoteMeta]:
        """Search notes by title or content.

        Args:
            vault_id: Vault ID
            query_text: Search query
            limit: Max results

        Returns:
            Matching notes
        """
        # Simple text search - can be enhanced with embeddings later
        # vault_id stored as record reference
        query = """
        SELECT id, vault_id, path, title, preview, word_count, created_at, updated_at
        FROM note
        WHERE vault_id = type::thing($vault_id)
        AND (
            string::lowercase(title) CONTAINS string::lowercase($query)
            OR string::lowercase(content) CONTAINS string::lowercase($query)
        )
        ORDER BY updated_at DESC
        LIMIT $limit;
        """

        results = await execute_query(query, {
            "vault_id": f"vault:{vault_id}",
            "query": query_text,
            "limit": limit,
        })

        return [_record_to_meta(r) for r in results]


# Singleton service instance
_note_service: Optional[NoteService] = None


def get_note_service() -> NoteService:
    """Get note service singleton."""
    global _note_service
    if _note_service is None:
        _note_service = NoteService()
    return _note_service
