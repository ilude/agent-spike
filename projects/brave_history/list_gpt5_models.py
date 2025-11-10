#!/usr/bin/env python3
"""
List available OpenAI GPT-5 models.
"""

import os
import sys
from pathlib import Path

from openai import OpenAI

# Add workspace root to Python path
workspace_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(workspace_root))

from tools.env_loader import load_root_env


def main():
    """List available GPT-5 models."""
    # Load .env file
    load_root_env()

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
