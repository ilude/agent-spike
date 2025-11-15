#!/usr/bin/env python3
"""Analyze history.jsonl for bash commands and skill invocations."""
import json
from pathlib import Path

history = Path.home() / '.claude/history.jsonl'

# Sample different entry types
user_msgs = []
assistant_msgs = []
bash_cmds = []
skill_invokes = []

with open(history, encoding='utf-8', errors='ignore') as f:
    for line in f:
        try:
            entry = json.loads(line)

            # User messages
            if 'display' in entry:
                text = entry.get('display', '')
                if 'git' in text.lower():
                    user_msgs.append(text[:100])
                if 'commit' in text.lower() or 'push' in text.lower():
                    user_msgs.append(text[:100])

            # Assistant messages with tool use
            if entry.get('role') == 'assistant' and 'content' in entry:
                content = entry['content']
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict):
                            # Check for Bash tool
                            if item.get('name') == 'Bash':
                                cmd = item.get('input', {}).get('command', '')
                                if cmd and 'git' in cmd:
                                    bash_cmds.append(cmd[:100])
                            # Check for Skill tool
                            if item.get('name') == 'Skill':
                                skill = item.get('input', {}).get('skill', '')
                                if skill:
                                    skill_invokes.append(skill)

        except:
            pass

print("=== User Messages (git-related) ===")
for msg in user_msgs[:5]:
    print(f"  {msg}")

print("\n=== Bash Commands (git) ===")
for cmd in bash_cmds[:5]:
    print(f"  {cmd}")

print("\n=== Skill Invocations ===")
for skill in skill_invokes[:5]:
    print(f"  {skill}")

print(f"\nTotal: {len(user_msgs)} user git msgs, {len(bash_cmds)} git bash commands, {len(skill_invokes)} skill invocations")