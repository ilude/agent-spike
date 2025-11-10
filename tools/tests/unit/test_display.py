"""Test video display formatter."""

from tools.services.display.video_formatter import format_video_display


def test_format_video_new_format():
    """Test formatting video with new structured metadata."""
    video = {
        "video_id": "test123",
        "url": "https://youtube.com/watch?v=test123",
        "transcript_length": 5000,
        "metadata": {
            "title": "Test Video",
            "subject_matter": ["AI", "Python", "Testing"],
            "content_style": "tutorial"
        }
    }

    result = format_video_display(video, index=1)

    assert "1. test123" in result
    assert "URL: https://youtube.com/watch?v=test123" in result
    assert "Title: Test Video" in result
    assert "Subject: AI, Python, Testing" in result
    assert "Style: tutorial" in result
    assert "Transcript: 5,000 characters" in result


def test_format_video_old_format():
    """Test formatting video with old tags format."""
    video = {
        "video_id": "old456",
        "url": "https://youtube.com/watch?v=old456",
        "transcript_length": 3000,
        "tags": "AI, machine learning, tutorial"
    }

    result = format_video_display(video, index=2)

    assert "2. old456" in result
    assert "URL: https://youtube.com/watch?v=old456" in result
    assert "Title: N/A" in result
    assert "Subject: AI, machine learning, tutorial" in result
    assert "Transcript: 3,000 characters" in result


def test_format_video_with_score():
    """Test formatting video with relevance score."""
    video = {
        "video_id": "scored789",
        "url": "https://youtube.com/watch?v=scored789",
        "transcript_length": 8000,
        "metadata": {
            "title": "Relevant Video",
            "subject_matter": ["relevance"],
            "content_style": "demo"
        },
        "_score": 0.875
    }

    result = format_video_display(video, index=3, show_score=True)

    assert "3. scored789" in result
    assert "Relevance: 0.875" in result
    assert "Title: Relevant Video" in result


def test_format_video_minimal():
    """Test formatting video with minimal data."""
    video = {
        "video_id": "minimal",
    }

    result = format_video_display(video, index=5)

    assert "5. minimal" in result
    assert "URL: N/A" in result
    assert "Title: N/A" in result
    assert "Subject: N/A" in result
    assert "Transcript: 0 characters" in result


def test_format_video_truncate_subject():
    """Test that subject matter is truncated to 3 items."""
    video = {
        "video_id": "many_subjects",
        "url": "https://youtube.com/watch?v=many_subjects",
        "metadata": {
            "title": "Many Topics",
            "subject_matter": ["AI", "ML", "DL", "NLP", "CV"],
        }
    }

    result = format_video_display(video, index=1)

    # Should only show first 3
    assert "Subject: AI, ML, DL" in result
    assert "NLP" not in result
    assert "CV" not in result
