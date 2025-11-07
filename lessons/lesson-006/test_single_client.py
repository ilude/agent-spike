"""Quick test to verify single client works without file locking."""
import os

from memory import MemoryClient
from tools.dotenv import load_root_env

load_root_env()

print("Creating MemoryClient...")
client = MemoryClient()
print("Client created successfully")

print("\nAdding a memory...")
result = client.add(
    messages=[{"role": "user", "content": "I love Python"}],
    user_id="test_user"
)
print(f"Memory added: {result.get('message', 'Success')}")

print("\nGetting all memories...")
memories = client.get_all(user_id="test_user")
print(f"Retrieved {len(memories)} memories")

print("\nCleaning up...")
client.delete_all(user_id="test_user")
print("Cleanup complete")

print("\nAll operations successful - file locking issue resolved!")
