"""
Test calling subagent directly to isolate the hang
"""
print("TEST START", flush=True)

import sys
from lessons.lesson_base import setup_lesson_environment
setup_lesson_environment(lessons=["lesson-001"])

print("1. Paths set up", flush=True)
print("2. Env loaded", flush=True)

# Try importing the YouTube agent module
print("3. About to import youtube_agent.agent", flush=True)
from youtube_agent.agent import create_agent
print("4. Import successful", flush=True)

# Try creating the agent
print("5. Creating YouTube agent...", flush=True)
youtube_agent = create_agent(instrument=False)
print("6. Agent created", flush=True)

# Try running it
print("7. Running agent...", flush=True)
result = youtube_agent.run_sync(
    user_prompt="Tag this video: https://www.youtube.com/watch?v=i5kwX7jeWL8",
    message_history=[]
)
print("8. Agent run complete", flush=True)

print(f"Result: {result.output}", flush=True)
print("TEST COMPLETE", flush=True)