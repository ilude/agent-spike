"""Tests for archive service.

Run with: uv run python test_archive.py
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

from archive import (
    LocalArchiveWriter,
    LocalArchiveReader,
    YouTubeArchive,
)


def test_archive_writer_basic():
    """Test basic archive write and read."""
    print("\n[TEST] Archive writer basic operations...")

    with tempfile.TemporaryDirectory() as tmpdir:
        writer = LocalArchiveWriter(base_dir=Path(tmpdir))

        # Archive a video
        video_id = "test123"
        url = "https://www.youtube.com/watch?v=test123"
        transcript = "This is a test transcript about AI agents."
        metadata = {
            "title": "Test Video",
            "channel": "Test Channel",
            "upload_date": "2024-11-09",
        }

        archive_path = writer.archive_youtube_video(
            video_id=video_id,
            url=url,
            transcript=transcript,
            metadata=metadata,
        )

        assert archive_path.exists(), "Archive file not created"
        print(f"  [OK] Archive created: {archive_path}")

        # Check exists
        assert writer.exists(video_id), "exists() returned False"
        print(f"  [OK] exists() works")

        # Retrieve archive
        archive = writer.get(video_id)
        assert archive is not None, "get() returned None"
        assert archive.video_id == video_id, "video_id mismatch"
        assert archive.url == url, "url mismatch"
        assert archive.raw_transcript == transcript, "transcript mismatch"
        assert archive.youtube_metadata == metadata, "metadata mismatch"
        print(f"  [OK] Retrieved archive matches original")

        # Count
        count = writer.count()
        assert count == 1, f"Expected 1 archive, got {count}"
        print(f"  [OK] count() = {count}")


def test_llm_output_tracking():
    """Test LLM output tracking and cost calculation."""
    print("\n[TEST] LLM output tracking...")

    with tempfile.TemporaryDirectory() as tmpdir:
        writer = LocalArchiveWriter(base_dir=Path(tmpdir))

        # Archive a video
        video_id = "test456"
        writer.archive_youtube_video(
            video_id=video_id,
            url="https://www.youtube.com/watch?v=test456",
            transcript="AI agents are cool.",
        )

        # Add LLM output
        writer.add_llm_output(
            video_id=video_id,
            output_type="tags",
            output_value="ai, agents, tutorial",
            model="claude-3-5-haiku-20241022",
            cost_usd=0.0012,
            prompt_tokens=500,
            completion_tokens=50,
        )

        # Retrieve and check
        archive = writer.get(video_id)
        assert len(archive.llm_outputs) == 1, "LLM output not added"

        output = archive.llm_outputs[0]
        assert output.output_type == "tags"
        assert output.output_value == "ai, agents, tutorial"
        assert output.model == "claude-3-5-haiku-20241022"
        assert output.cost_usd == 0.0012
        print(f"  [OK] LLM output tracked: {output.output_type} = {output.output_value}")

        # Add another output
        writer.add_llm_output(
            video_id=video_id,
            output_type="summary",
            output_value="A tutorial about AI agents.",
            model="claude-3-5-haiku-20241022",
            cost_usd=0.0023,
        )

        # Check total cost
        archive = writer.get(video_id)
        total_cost = archive.total_llm_cost()
        assert abs(total_cost - 0.0035) < 0.0001, f"Expected $0.0035, got ${total_cost}"
        print(f"  [OK] Total LLM cost: ${total_cost:.4f}")

        # Get latest output by type
        latest_tags = archive.get_latest_output("tags")
        assert latest_tags is not None
        assert latest_tags.output_value == "ai, agents, tutorial"
        print(f"  [OK] get_latest_output() works")


def test_processing_history():
    """Test processing history tracking."""
    print("\n[TEST] Processing history tracking...")

    with tempfile.TemporaryDirectory() as tmpdir:
        writer = LocalArchiveWriter(base_dir=Path(tmpdir))

        # Archive a video
        video_id = "test789"
        writer.archive_youtube_video(
            video_id=video_id,
            url="https://www.youtube.com/watch?v=test789",
            transcript="Testing processing history.",
        )

        # Add processing record
        writer.add_processing_record(
            video_id=video_id,
            version="v1_full_embed",
            collection_name="cached_content",
            notes="Initial full-transcript embedding",
        )

        # Retrieve and check
        archive = writer.get(video_id)
        assert len(archive.processing_history) == 1

        record = archive.processing_history[0]
        assert record.version == "v1_full_embed"
        assert record.collection_name == "cached_content"
        print(f"  [OK] Processing record added: {record.version}")

        # Add another record (simulating reprocessing)
        writer.add_processing_record(
            video_id=video_id,
            version="v2_chunked",
            collection_name="cached_content_v2",
            notes="Chunked transcript with 500-word segments",
        )

        archive = writer.get(video_id)
        assert len(archive.processing_history) == 2
        print(f"  [OK] Multiple processing records tracked")


def test_archive_reader():
    """Test archive reader for reprocessing workflows."""
    print("\n[TEST] Archive reader...")

    with tempfile.TemporaryDirectory() as tmpdir:
        writer = LocalArchiveWriter(base_dir=Path(tmpdir))

        # Create multiple archives
        for i in range(5):
            writer.archive_youtube_video(
                video_id=f"video{i}",
                url=f"https://www.youtube.com/watch?v=video{i}",
                transcript=f"Transcript {i}",
            )

        # Create reader
        reader = LocalArchiveReader(base_dir=Path(tmpdir))

        # Count
        count = reader.count()
        assert count == 5, f"Expected 5 archives, got {count}"
        print(f"  [OK] Reader count: {count}")

        # Iterate
        videos = list(reader.iter_youtube_videos())
        assert len(videos) == 5, f"Expected 5 videos, got {len(videos)}"
        print(f"  [OK] Iterated through {len(videos)} videos")

        # Get specific video
        archive = reader.get("video2")
        assert archive is not None
        assert archive.video_id == "video2"
        assert archive.raw_transcript == "Transcript 2"
        print(f"  [OK] Retrieved specific video: {archive.video_id}")


def test_month_organization():
    """Test that archives are organized by month."""
    print("\n[TEST] Month organization...")

    with tempfile.TemporaryDirectory() as tmpdir:
        writer = LocalArchiveWriter(base_dir=Path(tmpdir))

        # Archive a video
        writer.archive_youtube_video(
            video_id="monthtest",
            url="https://www.youtube.com/watch?v=monthtest",
            transcript="Testing month organization",
        )

        # Check directory structure
        youtube_dir = Path(tmpdir) / "youtube"
        assert youtube_dir.exists()

        # Should have a month directory (YYYY-MM format)
        month_dirs = list(youtube_dir.iterdir())
        assert len(month_dirs) == 1

        month_dir = month_dirs[0]
        assert month_dir.is_dir()
        assert len(month_dir.name) == 7  # YYYY-MM format
        print(f"  [OK] Month directory created: {month_dir.name}")

        # Check file inside
        json_files = list(month_dir.glob("*.json"))
        assert len(json_files) == 1
        assert json_files[0].name == "monthtest.json"
        print(f"  [OK] Archive file in month directory: {json_files[0].name}")


def test_json_format():
    """Test that JSON format is readable and valid."""
    print("\n[TEST] JSON format validation...")

    with tempfile.TemporaryDirectory() as tmpdir:
        writer = LocalArchiveWriter(base_dir=Path(tmpdir))

        # Archive with all fields
        video_id = "jsontest"
        writer.archive_youtube_video(
            video_id=video_id,
            url="https://www.youtube.com/watch?v=jsontest",
            transcript="Testing JSON format",
            metadata={"title": "JSON Test", "upload_date": "2024-11-09"},
        )

        # Add LLM output
        writer.add_llm_output(
            video_id=video_id,
            output_type="tags",
            output_value="test, json",
            model="claude-3-5-haiku-20241022",
            cost_usd=0.001,
        )

        # Add processing record
        writer.add_processing_record(
            video_id=video_id,
            version="v1",
            collection_name="test_collection",
        )

        # Find the JSON file
        youtube_dir = Path(tmpdir) / "youtube"
        json_file = list(youtube_dir.glob("*/*.json"))[0]

        # Read and validate JSON
        with open(json_file, "r") as f:
            data = json.load(f)

        assert "video_id" in data
        assert "raw_transcript" in data
        assert "llm_outputs" in data
        assert "processing_history" in data
        assert len(data["llm_outputs"]) == 1
        assert len(data["processing_history"]) == 1
        print(f"  [OK] JSON structure valid")
        print(f"  [OK] File size: {json_file.stat().st_size} bytes")


def test_reader_month_counts():
    """Test month count aggregation."""
    print("\n[TEST] Month counts...")

    with tempfile.TemporaryDirectory() as tmpdir:
        writer = LocalArchiveWriter(base_dir=Path(tmpdir))

        # Archive some videos (all in same month)
        for i in range(3):
            writer.archive_youtube_video(
                video_id=f"month{i}",
                url=f"https://www.youtube.com/watch?v=month{i}",
                transcript=f"Month test {i}",
            )

        reader = LocalArchiveReader(base_dir=Path(tmpdir))
        counts = reader.get_month_counts()

        assert len(counts) == 1, f"Expected 1 month, got {len(counts)}"
        month = list(counts.keys())[0]
        assert counts[month] == 3, f"Expected 3 videos in {month}, got {counts[month]}"
        print(f"  [OK] Month counts: {counts}")


def test_total_llm_cost():
    """Test total LLM cost calculation across archives."""
    print("\n[TEST] Total LLM cost calculation...")

    with tempfile.TemporaryDirectory() as tmpdir:
        writer = LocalArchiveWriter(base_dir=Path(tmpdir))

        # Create archives with LLM outputs
        for i in range(3):
            video_id = f"cost{i}"
            writer.archive_youtube_video(
                video_id=video_id,
                url=f"https://www.youtube.com/watch?v={video_id}",
                transcript=f"Cost test {i}",
            )
            writer.add_llm_output(
                video_id=video_id,
                output_type="tags",
                output_value=f"tag{i}",
                model="claude-3-5-haiku-20241022",
                cost_usd=0.001 * (i + 1),  # 0.001, 0.002, 0.003
            )

        reader = LocalArchiveReader(base_dir=Path(tmpdir))
        total_cost = reader.get_total_llm_cost()

        expected = 0.001 + 0.002 + 0.003  # 0.006
        assert abs(total_cost - expected) < 0.0001, f"Expected ${expected}, got ${total_cost}"
        print(f"  [OK] Total LLM cost: ${total_cost:.4f}")


def run_all_tests():
    """Run all tests."""
    print("=" * 70)
    print("Archive Service Tests")
    print("=" * 70)

    tests = [
        test_archive_writer_basic,
        test_llm_output_tracking,
        test_processing_history,
        test_archive_reader,
        test_month_organization,
        test_json_format,
        test_reader_month_counts,
        test_total_llm_cost,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n  [FAIL] {e}")
            failed += 1
        except Exception as e:
            print(f"\n  [ERROR] {e}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
