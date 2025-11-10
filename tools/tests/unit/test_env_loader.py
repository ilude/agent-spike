"""Test environment loader utilities."""

import pytest
from pathlib import Path
from tools.env_loader import find_git_root, load_root_env


def test_find_git_root_from_cwd():
    """Test finding git root from current directory."""
    git_root = find_git_root()

    # Should find the git root
    assert git_root.exists()
    assert (git_root / ".git").exists()
    assert git_root.name == "agent-spike"


def test_find_git_root_from_specific_path():
    """Test finding git root from a specific path."""
    # Start from tools directory
    tools_path = Path(__file__).parent.parent.parent
    git_root = find_git_root(tools_path)

    assert git_root.exists()
    assert (git_root / ".git").exists()


def test_find_git_root_not_found():
    """Test behavior when git root not found."""
    # Use root path where .git won't exist
    with pytest.raises(FileNotFoundError, match="No .git directory found"):
        find_git_root(Path("/"))


def test_load_root_env():
    """Test loading .env from git root."""
    # This should not raise an error
    load_root_env()

    # We can't test if env vars are actually loaded without
    # knowing what's in .env, but we can verify it runs
