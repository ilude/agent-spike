"""Integration tests that hit real datastores.

These tests use isolated namespaces/databases that are cleaned up after each test.
Run with: pytest -m integration

Requires running infrastructure:
- SurrealDB (compose/docker-compose.yml)
- MinIO (compose/docker-compose.yml)
"""
