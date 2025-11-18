"""Shared pytest fixtures for tools/services tests."""

import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Temporary directory for tests.

    Automatically cleaned up after test completes.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_transcript():
    """Sample YouTube transcript for testing."""
    return (
        "This is a sample transcript about AI agents. "
        "We discuss composability, dependency injection, and clean architecture. "
        "The goal is to build reusable services that can be composed together."
    )


@pytest.fixture
def sample_video_id():
    """Sample YouTube video ID."""
    return "dQw4w9WgXcQ"


@pytest.fixture
def sample_video_url(sample_video_id):
    """Sample YouTube video URL."""
    return f"https://www.youtube.com/watch?v={sample_video_id}"


@pytest.fixture
def sample_youtube_metadata():
    """Sample YouTube video metadata."""
    return {
        "title": "Test Video",
        "channel": "Test Channel",
        "upload_date": "2024-11-09",
        "duration": 180,
    }
