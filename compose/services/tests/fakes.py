"""Fake implementations for testing SurrealDB-based services.

These fakes provide in-memory implementations of external dependencies,
allowing unit tests to run without connecting to real databases or storage.

Usage:
    from compose.services.tests.fakes import FakeDatabaseExecutor, FakeMinIOClient
    from compose.services.projects import ProjectService

    fake_db = FakeDatabaseExecutor()
    fake_minio = FakeMinIOClient()
    service = ProjectService(db=fake_db, minio=fake_minio)
"""

from io import BytesIO
from typing import Any
from unittest.mock import MagicMock


class FakeDatabaseExecutor:
    """In-memory database executor for testing.

    Stores data in Python dicts and supports basic SurrealQL operations.
    Tracks all queries for test assertions.

    Attributes:
        tables: Dict mapping table names to lists of records
        query_log: List of (query, params) tuples for assertion
    """

    def __init__(self):
        """Initialize with empty tables."""
        self.tables: dict[str, list[dict[str, Any]]] = {}
        self.query_log: list[tuple[str, dict[str, Any] | None]] = []
        self._next_responses: list[list[dict[str, Any]]] = []

    def set_next_response(self, response: list[dict[str, Any]]) -> None:
        """Set the response for the next query.

        Useful for testing specific scenarios without implementing
        full query parsing.

        Args:
            response: The response to return for the next query
        """
        self._next_responses.append(response)

    async def execute(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a query and return results.

        Basic SurrealQL parsing for common patterns:
        - CREATE table CONTENT {...} -> adds to table
        - SELECT * FROM table -> returns all records
        - SELECT * FROM table WHERE id = $id -> returns matching record
        - DELETE FROM table WHERE ... -> removes records
        - UPDATE table SET ... WHERE id = $id -> updates record

        Args:
            query: SurrealQL query string
            params: Query parameters

        Returns:
            List of result records
        """
        self.query_log.append((query, params))
        params = params or {}

        # If we have a preset response, use it
        if self._next_responses:
            return self._next_responses.pop(0)

        query_upper = query.upper().strip()

        # Handle CREATE
        if query_upper.startswith("CREATE"):
            return self._handle_create(query, params)

        # Handle SELECT with COUNT (only pure count queries, not subqueries)
        # Check if this is "SELECT count()" or "SELECT COUNT()" at the start
        if query_upper.startswith("SELECT COUNT(") or query_upper.startswith("SELECT COUNT ("):
            return self._handle_count(query, params)

        # Handle SELECT (including queries with count subqueries)
        if query_upper.startswith("SELECT"):
            return self._handle_select(query, params)

        # Handle DELETE
        if query_upper.startswith("DELETE"):
            return self._handle_delete(query, params)

        # Handle UPDATE
        if query_upper.startswith("UPDATE"):
            return self._handle_update(query, params)

        return []

    def _extract_table_name(self, query: str) -> str:
        """Extract table name from query.

        Handles SurrealDB record ID syntax like:
        - SELECT * FROM conversation:`test-id`  -> conversation
        - UPDATE conversation:`test-id` SET ...  -> conversation
        - DELETE conversation:`test-id`         -> conversation

        For SELECT queries with subqueries, finds the outer FROM clause.
        """
        # Normalize whitespace (handle multi-line queries)
        normalized = " ".join(query.split())

        # For complex SELECT queries, strip out subqueries first
        # by removing content inside parentheses
        query_upper = normalized.upper()
        if query_upper.startswith("SELECT"):
            # Remove subqueries (content in parentheses) to find outer FROM
            cleaned = self._remove_parenthesized(normalized)
            words = cleaned.split()
        else:
            words = normalized.split()

        for i, word in enumerate(words):
            if word.upper() in ("FROM", "INTO"):
                if i + 1 < len(words):
                    table = words[i + 1].lower().rstrip(";")
                    # Strip record ID syntax (table:`id` or table:id)
                    if ":" in table:
                        table = table.split(":")[0]
                    # Remove backticks if present
                    table = table.strip("`")
                    return table
            if word.upper() == "CREATE":
                if i + 1 < len(words):
                    table = words[i + 1].lower().rstrip(";")
                    if ":" in table:
                        table = table.split(":")[0]
                    return table.strip("`")
            if word.upper() == "UPDATE":
                if i + 1 < len(words):
                    table = words[i + 1].lower().rstrip(";")
                    if ":" in table:
                        table = table.split(":")[0]
                    return table.strip("`")
            if word.upper() == "DELETE":
                if i + 1 < len(words):
                    table = words[i + 1].lower().rstrip(";")
                    if ":" in table:
                        table = table.split(":")[0]
                    return table.strip("`")
        return ""

    def _remove_parenthesized(self, query: str) -> str:
        """Remove content inside parentheses to find outer clauses."""
        result = []
        depth = 0
        for char in query:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif depth == 0:
                result.append(char)
        return "".join(result)

    def _handle_create(
        self, query: str, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Handle CREATE query."""
        table = self._extract_table_name(query)
        if not table:
            return []

        if table not in self.tables:
            self.tables[table] = []

        # Create record from params
        record = dict(params)
        self.tables[table].append(record)
        return [record]

    def _handle_count(
        self, query: str, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Handle COUNT query."""
        table = self._extract_table_name(query)
        if not table or table not in self.tables:
            return [{"count": 0}]

        # Check for WHERE clause
        if "WHERE" in query.upper():
            count = self._count_matching(table, params)
        else:
            count = len(self.tables[table])

        return [{"count": count}]

    def _count_matching(self, table: str, params: dict[str, Any]) -> int:
        """Count records matching params."""
        count = 0
        for record in self.tables.get(table, []):
            match = True
            for key, value in params.items():
                if record.get(key) != value:
                    match = False
                    break
            if match:
                count += 1
        return count

    def _extract_record_id(self, query: str) -> str | None:
        """Extract record ID from SurrealDB record ID syntax.

        Examples:
        - SELECT * FROM conversation:`test-id`  -> test-id
        - UPDATE conversation:`abc-123` SET ... -> abc-123
        - DELETE conversation:`xyz`             -> xyz
        """
        import re

        # Look for patterns like table:`id` or table:`id`
        match = re.search(r":\s*`([^`]+)`", query)
        if match:
            return match.group(1)

        # Also handle table:id without backticks
        words = query.split()
        for word in words:
            if ":" in word and not word.upper() in ("WHERE:", "SET:"):
                parts = word.rstrip(";").split(":", 1)
                if len(parts) == 2 and parts[1]:
                    return parts[1].strip("`")

        return None

    def _handle_select(
        self, query: str, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Handle SELECT query."""
        table = self._extract_table_name(query)
        if not table or table not in self.tables:
            return []

        # Check for record ID syntax (e.g., FROM table:`id`)
        record_id = self._extract_record_id(query)
        if record_id:
            # Filter by the specific record ID
            for record in self.tables[table]:
                if record.get("id") == record_id:
                    return [record]
            return []

        # Check for WHERE clause
        if "WHERE" in query.upper():
            return self._filter_records(table, params)
        return list(self.tables[table])

    def _filter_records(
        self, table: str, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Filter records by params."""
        results = []
        for record in self.tables.get(table, []):
            match = True
            for key, value in params.items():
                if record.get(key) != value:
                    match = False
                    break
            if match:
                results.append(record)
        return results

    def _handle_delete(
        self, query: str, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Handle DELETE query."""
        table = self._extract_table_name(query)
        if not table or table not in self.tables:
            return []

        # Remove matching records
        original = self.tables[table]
        if "WHERE" in query.upper():
            self.tables[table] = [
                r for r in original if not self._record_matches(r, params)
            ]
        else:
            self.tables[table] = []

        deleted_count = len(original) - len(self.tables[table])
        return [{"deleted": deleted_count}]

    def _record_matches(self, record: dict, params: dict) -> bool:
        """Check if record matches all params."""
        for key, value in params.items():
            if record.get(key) != value:
                return False
        return True

    def _handle_update(
        self, query: str, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Handle UPDATE query.

        Supports both:
        - UPDATE table SET ... WHERE id = $id (using params)
        - UPDATE table:`id` SET ... (using record ID syntax)
        """
        table = self._extract_table_name(query)
        if not table or table not in self.tables:
            return []

        # Check for record ID syntax (e.g., UPDATE table:`id`)
        record_id = self._extract_record_id(query)

        updated = []
        for record in self.tables[table]:
            # Match by record ID from query syntax or from params
            target_id = record_id or params.get("id")
            if target_id and record.get("id") == target_id:
                # Update fields from params (except 'id')
                for key, value in params.items():
                    if key != "id":
                        record[key] = value
                updated.append(record)

        return updated


class FakeMinIOClient:
    """In-memory MinIO client for testing.

    Stores objects in a Python dict, allowing tests to verify
    file operations without a real MinIO server.

    Attributes:
        objects: Dict mapping object paths to bytes content
        bucket: Bucket name (for compatibility with real client)
    """

    def __init__(self, bucket: str = "test-bucket"):
        """Initialize with empty storage.

        Args:
            bucket: Bucket name for this client
        """
        self.objects: dict[str, bytes] = {}
        self.bucket = bucket
        # Mock the underlying client for operations that access it directly
        self.client = MagicMock()
        self._setup_client_mocks()

    def _setup_client_mocks(self) -> None:
        """Setup mock methods on the client attribute."""
        def put_object(bucket_name, object_name, data, length, content_type=None):
            if hasattr(data, 'read'):
                self.objects[object_name] = data.read()
            else:
                self.objects[object_name] = data
            return MagicMock()

        def get_object(bucket_name, object_name):
            if object_name not in self.objects:
                raise Exception(f"Object not found: {object_name}")
            response = MagicMock()
            response.read.return_value = self.objects[object_name]
            return response

        self.client.put_object = MagicMock(side_effect=put_object)
        self.client.get_object = MagicMock(side_effect=get_object)

    def put_json(self, path: str, data: dict) -> str:
        """Store JSON data."""
        import json
        self.objects[path] = json.dumps(data).encode()
        return path

    def get_json(self, path: str) -> dict:
        """Retrieve JSON data."""
        import json
        if path not in self.objects:
            raise Exception(f"Object not found: {path}")
        return json.loads(self.objects[path].decode())

    def put_text(self, path: str, text: str) -> str:
        """Store text data."""
        self.objects[path] = text.encode()
        return path

    def get_text(self, path: str) -> str:
        """Retrieve text data."""
        if path not in self.objects:
            raise Exception(f"Object not found: {path}")
        return self.objects[path].decode()

    def exists(self, path: str) -> bool:
        """Check if object exists."""
        return path in self.objects

    def delete(self, path: str) -> None:
        """Delete object."""
        self.objects.pop(path, None)

    def list_objects(self, prefix: str = "") -> list:
        """List objects with prefix."""
        results = []
        for key in self.objects:
            if key.startswith(prefix):
                obj = MagicMock()
                obj.object_name = key
                results.append(obj)
        return results

    def ensure_bucket(self) -> None:
        """No-op for testing."""
        pass
