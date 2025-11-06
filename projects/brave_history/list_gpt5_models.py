#!/usr/bin/env python3
"""
List available OpenAI GPT-5 models.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Find and load .env from git root
def find_env_file() -> Path | None:
    """Search up the directory tree for .git directory, then look for .env in that directory."""
    current = Path(__file__).parent.absolute()

    while current != current.parent:
        git_dir = current / ".git"
        if git_dir.exists():
            env_file = current / ".env"
            if env_file.exists():
                return env_file
            return None

        current = current.parent

    return None


def main():
    """List available GPT-5 models."""
    # Load .env file
    env_path = find_env_file()
    if env_path:
        load_dotenv(env_path)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in .env file")
        return

    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)

    # List all available models
    print("Fetching available models from OpenAI...\n")
    models = client.models.list()

    # Filter for GPT-5 models
    gpt5_models = [m for m in models.data if "gpt-5" in m.id.lower()]

    if gpt5_models:
        print(f"Found {len(gpt5_models)} GPT-5 model(s):\n")
        for model in gpt5_models:
            print(f"  • {model.id}")
            print(f"    Owner: {model.owned_by}")
            print()
    else:
        print("No GPT-5 models found in your account.")
        print("\nAvailable models containing 'gpt':")
        gpt_models = [m for m in models.data if "gpt" in m.id.lower()]
        for model in gpt_models[:10]:  # Show first 10
            print(f"  • {model.id}")


if __name__ == "__main__":
    main()
