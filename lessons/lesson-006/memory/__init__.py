"""
Memory module for AI agent memory management with Mem0.

This module provides a simplified interface to Mem0 for:
- User preference tracking
- Conversation history
- Agent experience accumulation

Example:
    ```python
    from memory import MemoryClient

    client = MemoryClient()

    # Add memory
    client.add(
        messages=[{"role": "user", "content": "I love tech content"}],
        user_id="alice"
    )

    # Search memory
    memories = client.search("content preferences", user_id="alice")
    print(memories)
    ```
"""

from .client import MemoryClient
from .config import ensure_api_key

__all__ = ["MemoryClient", "ensure_api_key"]
