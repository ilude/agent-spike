"""
Minimal orchestrator test - just test if it can make one tool call
"""
print("SCRIPT STARTED")

import sys
import os
from pathlib import Path

print("Imports done")

# Bootstrap to import lesson_base
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Setup lesson environment
from lessons.lesson_base import setup_lesson_environment
setup_lesson_environment(lessons=["lesson-001", "lesson-002"])

print("Environment setup done")
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
