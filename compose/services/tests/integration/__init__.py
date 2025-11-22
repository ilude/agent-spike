"""Integration tests for compose services.

These tests require external services:
- Remote Qdrant: http://192.168.16.241:6333
- Remote Infinity: http://192.168.16.241:7997
- Remote Ollama: http://192.168.16.241:11434

Run with: uv run pytest compose/services/tests/integration/ -v -s
"""
