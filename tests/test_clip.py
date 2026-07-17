"""Tests for the video clipping module."""

import os
from unittest.mock import patch

import pytest

from youtube_clipper.clip import ClipResult, clip_video
from youtube_clipper.highlights import Highlight


class TestClipResult:
    def test_clip_result_creation(self):
        cr = ClipResult(
            highlight=Highlight(10, 30, "Best", "reason"),
            output_path="/tmp/clip1.mp4",
            success=True,
        )
        assert cr.success is True
        assert cr.output_path == "/tmp/clip1.mp4"
        assert cr.highlight.title == "Best"


def _create_test_video(path: str, duration: float = 2.0) -> str:
    """Create a small test video file with FFmpeg."""
    os.makedirs(os.path.dirname(path) or "/tmp", exist_ok=True)
    cmd = (
        f"ffmpeg -y -f lavfi -i color=c=blue:s=320x240:d={duration} "
        f"-f lavfi -i anullsrc=r=44100:cl=mono "
        f"-shortest -c:v libx264 -c:a aac {path} 2>/dev/null"
    )
    os.system(cmd)
    return path


class TestClipVideo:
    def test_clip_single_highlight(self):
        """Should clip a single segment from a video."""
        video_path = _create_test_video("/tmp/test_clip_source.mp4", duration=3)
        output_dir = "/tmp/test_clips"
        os.makedirs(output_dir, exist_ok=True)

        highlight = Highlight(start=0.5, end=2.0, title="Test Clip", reason="test")
        results = clip_video(video_path, [highlight], output_dir=output_dir)

        assert len(results) == 1
        assert results[0].success is True
        assert os.path.exists(results[0].output_path)
        assert results[0].output_path.endswith(".mp4")

        # Cleanup
        os.remove(video_path)
        os.remove(results[0].output_path)

    def test_clip_multiple_highlights(self):
        """Should clip multiple segments."""
        video_path = _create_test_video("/tmp/test_clip_multi.mp4", duration=5)
        output_dir = "/tmp/test_clips_multi"
        os.makedirs(output_dir, exist_ok=True)

        highlights = [
            Highlight(start=0.5, end=1.5, title="First", reason="r1"),
            Highlight(start=2.0, end=3.5, title="Second", reason="r2"),
        ]
        results = clip_video(video_path, highlights, output_dir=output_dir)

        assert len(results) == 2
        assert all(r.success for r in results)
        for r in results:
            assert os.path.exists(r.output_path)

        # Cleanup
        os.remove(video_path)
        for r in results:
            os.remove(r.output_path)

    def test_clip_creates_output_dir(self):
        """Should create output directory if missing."""
        video_path = _create_test_video("/tmp/test_clip_dir.mp4", duration=2)
        output_dir = "/tmp/test_clips_auto"

        highlight = Highlight(start=0.3, end=1.5, title="Dir Test", reason="test")
        results = clip_video(video_path, [highlight], output_dir=output_dir)

        assert os.path.isdir(output_dir)
        assert results[0].success

        # Cleanup
        os.remove(video_path)
        os.remove(results[0].output_path)

    def test_clip_handles_missing_video(self):
        """Should return failed ClipResult for missing video."""
        results = clip_video("/tmp/does_not_exist.mp4", [Highlight(0, 10, "X", "")])

        assert len(results) == 1
        assert results[0].success is False
        assert "not found" in results[0].error.lower()

    def test_clip_empty_highlights(self):
        """Should return empty list for no highlights."""
        video_path = _create_test_video("/tmp/test_clip_empty.mp4", duration=2)
        results = clip_video(video_path, [])
        assert results == []
        os.remove(video_path)

    def test_clip_sanitizes_filename(self):
        """Clip filenames should be safe (no spaces, special chars)."""
        video_path = _create_test_video("/tmp/test_clip_safe.mp4", duration=3)
        output_dir = "/tmp/test_clips_safe"
        os.makedirs(output_dir, exist_ok=True)

        highlight = Highlight(
            start=0.5, end=2.0,
            title="Special: chars / test!",
            reason="whatever",
        )
        results = clip_video(video_path, [highlight], output_dir=output_dir)

        filename = os.path.basename(results[0].output_path)
        # No spaces, no special chars except - and _
        assert " " not in filename
        assert ":" not in filename
        assert "/" not in filename
        assert "!" not in filename

        os.remove(video_path)
        os.remove(results[0].output_path)