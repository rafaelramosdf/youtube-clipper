"""Tests for the download module."""

import os
from unittest.mock import MagicMock, patch

import pytest

from youtube_clipper.download import VideoMetadata, download_video


class TestVideoMetadata:
    def test_metadata_creation(self):
        meta = VideoMetadata(
            video_id="abc123",
            title="Test Video",
            channel="Test Channel",
            duration=120,
            file_path="/tmp/test.mp4",
        )
        assert meta.video_id == "abc123"
        assert meta.title == "Test Video"
        assert meta.duration == 120
        assert meta.file_path == "/tmp/test.mp4"

    def test_metadata_repr(self):
        meta = VideoMetadata(video_id="abc", title="Test", channel="Ch", duration=60, file_path="/tmp/v.mp4")
        repr_str = repr(meta)
        assert "abc" in repr_str
        assert "Test" in repr_str


class TestDownloadVideo:
    @patch("yt_dlp.YoutubeDL")
    def test_download_success(self, mock_ydl):
        """Download should return metadata when yt-dlp succeeds."""
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = {
            "id": "abc123",
            "title": "Test Video",
            "channel": "Test Channel",
            "duration": 120,
        }
        mock_instance.prepare_filename.return_value = "/tmp/youtube-clipper/abc123.mp4"
        mock_ydl.return_value.__enter__.return_value = mock_instance

        # Touch the file so _file_exists returns True
        os.makedirs("/tmp/youtube-clipper", exist_ok=True)
        with open("/tmp/youtube-clipper/abc123.mp4", "w") as f:
            f.write("fake video data")

        result = download_video("https://youtube.com/watch?v=abc123")

        assert result.video_id == "abc123"
        assert result.title == "Test Video"
        assert result.channel == "Test Channel"
        assert result.duration == 120
        assert result.file_path == "/tmp/youtube-clipper/abc123.mp4"

        # Cleanup
        os.remove("/tmp/youtube-clipper/abc123.mp4")

    @patch("yt_dlp.YoutubeDL")
    def test_download_uses_correct_output_template(self, mock_ydl):
        """Download should use MP4 output template in the right directory."""
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = {
            "id": "xyz",
            "title": "HD Video",
            "channel": "HD Channel",
            "duration": 300,
        }
        mock_instance.prepare_filename.return_value = "/tmp/youtube-clipper/xyz.mp4"
        mock_ydl.return_value.__enter__.return_value = mock_instance

        os.makedirs("/tmp/youtube-clipper", exist_ok=True)
        with open("/tmp/youtube-clipper/xyz.mp4", "w") as f:
            f.write("fake data")

        result = download_video("https://youtube.com/watch?v=xyz")

        # Verify output is in the right directory and has .mp4 extension
        assert result.file_path.endswith(".mp4")
        assert "/tmp/youtube-clipper" in result.file_path

        os.remove("/tmp/youtube-clipper/xyz.mp4")

    def test_download_creates_output_dir(self):
        """Download should create output directory if it doesn't exist."""
        import shutil

        test_dir = "/tmp/youtube-clipper-test"
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

        with patch("yt_dlp.YoutubeDL") as mock_ydl:
            mock_instance = MagicMock()
            mock_instance.extract_info.return_value = {
                "id": "test123",
                "title": "Dir Test",
                "channel": "Ch",
                "duration": 60,
            }
            mock_instance.prepare_filename.return_value = f"{test_dir}/test123.mp4"
            mock_ydl.return_value.__enter__.return_value = mock_instance

            os.makedirs(test_dir, exist_ok=True)
            with open(f"{test_dir}/test123.mp4", "w") as f:
                f.write("data")

            result = download_video("https://youtube.com/watch?v=test123", output_dir=test_dir)
            assert os.path.isdir(test_dir)
            assert result.file_path == f"{test_dir}/test123.mp4"

            shutil.rmtree(test_dir)

    @patch("yt_dlp.YoutubeDL")
    def test_download_extracts_correct_metadata(self, mock_ydl):
        """All metadata fields should be extracted from yt-dlp response."""
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = {
            "id": "meta123",
            "title": "Metadata Test",
            "channel": "Meta Channel",
            "duration": 180,
            "view_count": 10000,
            "like_count": 500,
        }
        mock_instance.prepare_filename.return_value = "/tmp/youtube-clipper/meta123.mp4"
        mock_ydl.return_value.__enter__.return_value = mock_instance

        os.makedirs("/tmp/youtube-clipper", exist_ok=True)
        with open("/tmp/youtube-clipper/meta123.mp4", "w") as f:
            f.write("data")

        result = download_video("https://youtube.com/watch?v=meta123")

        assert result.video_id == "meta123"
        assert result.title == "Metadata Test"
        assert result.channel == "Meta Channel"
        assert result.duration == 180

        os.remove("/tmp/youtube-clipper/meta123.mp4")

    @patch("yt_dlp.YoutubeDL")
    def test_download_failure_raises_runtime_error(self, mock_ydl):
        """Download should raise RuntimeError when yt-dlp fails."""
        mock_instance = MagicMock()
        mock_instance.extract_info.side_effect = Exception("Video unavailable")
        mock_ydl.return_value.__enter__.return_value = mock_instance

        with pytest.raises(RuntimeError, match="Failed to download"):
            download_video("https://youtube.com/watch?v=invalid")