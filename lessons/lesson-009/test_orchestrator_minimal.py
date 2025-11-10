"""
Minimal orchestrator test - just test if it can make one tool call
"""
print("SCRIPT STARTED")

import sys
import os
from pathlib import Path

print("Imports done")

# Add project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

print("Path setup done")

# Load env
from tools.env_loader import load_root_env
load_root_env()

print("Env loaded")

# Add lessons
lessons_dir = Path(__file__).parent.parent
sys.path.insert(0, str(lessons_dir))
sys.path.insert(0, str(lessons_dir / "lesson-001"))
sys.path.insert(0, str(lessons_dir / "lesson-002"))

print("About to import orchestrator...")

from orchestrator_agent import orchestrator

print("Orchestrator imported!")
print("Testing orchestrator with simple prompt...\n")

result = orchestrator.run_sync(
    user_prompt="Tag this single YouTube URL: https://www.youtube.com/watch?v=i5kwX7jeWL8",
    message_history=[]
)

print(f"\n===RESULT===")
print(f"Type: {type(result)}")
print(f"Output: {result.output}")
print("\nDONE")
