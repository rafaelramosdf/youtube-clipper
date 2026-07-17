"""Tests for the transcribe module."""

import os
from unittest.mock import MagicMock, patch

import pytest

from youtube_clipper.download import VideoMetadata
from youtube_clipper.transcribe import TranscriptionSegment, extract_audio, transcribe_video


class TestTranscriptionSegment:
    def test_segment_creation(self):
        seg = TranscriptionSegment(start=0.0, end=5.2, text="Hello world")
        assert seg.start == 0.0
        assert seg.end == 5.2
        assert seg.text == "Hello world"
        assert seg.duration == 5.2

    def test_segment_repr(self):
        seg = TranscriptionSegment(start=10.0, end=25.5, text="Testing")
        r = repr(seg)
        assert "10.0" in r
        assert "25.5" in r
        assert "Testing" in r


class TestExtractAudio:
    def test_extract_audio_returns_path(self):
        """extract_audio should produce an mp3 file."""
        # Create a tiny valid mp4 (1 frame black video)
        video_path = "/tmp/test_extract.mp4"
        os.system(
            f"ffmpeg -y -f lavfi -i color=c=black:s=64x64:d=1 "
            f"-f lavfi -i anullsrc=r=44100:cl=mono -shortest {video_path} 2>/dev/null"
        )

        audio_path = extract_audio(video_path)

        assert audio_path.endswith(".mp3")
        assert os.path.exists(audio_path)

        # Cleanup
        os.remove(video_path)
        os.remove(audio_path)

    def test_extract_audio_invalid_video(self):
        """extract_audio should raise on non-existent file."""
        with pytest.raises(FileNotFoundError):
            extract_audio("/tmp/nonexistent_video.mp4")


class TestTranscribeVideo:
    @patch("youtube_clipper.transcribe.extract_audio")
    @patch("builtins.open")
    @patch("youtube_clipper.transcribe.OpenAI")
    def test_transcribe_returns_segments(self, mock_openai, mock_builtin_open, mock_extract):
        """transcribe_video should return list of TranscriptionSegment."""
        mock_extract.return_value = "/tmp/test_audio.mp3"

        # Mock OpenAI client
        mock_client = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.segments = [
            MagicMock(start=0.0, end=5.0, text="First segment"),
            MagicMock(start=5.0, end=10.0, text="Second segment"),
        ]
        mock_client.audio.transcriptions.create.return_value = mock_transcription
        mock_openai.return_value = mock_client

        metadata = VideoMetadata(
            video_id="test123",
            title="Test",
            channel="Ch",
            duration=60,
            file_path="/tmp/test.mp4",
        )

        result = transcribe_video(metadata)

        assert len(result) == 2
        assert result[0].start == 0.0
        assert result[0].end == 5.0
        assert result[0].text == "First segment"
        assert result[1].text == "Second segment"

    @patch("youtube_clipper.transcribe.extract_audio")
    @patch("builtins.open")
    @patch("youtube_clipper.transcribe.OpenAI")
    def test_transcribe_uses_whisper_model(self, mock_openai, mock_builtin_open, mock_extract):
        """Should use whisper-1 model by default."""
        mock_extract.return_value = "/tmp/test_audio.mp3"

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = MagicMock(segments=[])
        mock_openai.return_value = mock_client

        metadata = VideoMetadata("id", "t", "c", 60, "/tmp/v.mp4")
        transcribe_video(metadata)

        # Verify whisper-1 model was used
        call_kwargs = mock_client.audio.transcriptions.create.call_args[1]
        assert call_kwargs["model"] == "whisper-1"

    @patch("youtube_clipper.transcribe.extract_audio")
    @patch("builtins.open")
    @patch("youtube_clipper.transcribe.OpenAI")
    def test_transcribe_requests_verbose_json(self, mock_openai, mock_builtin_open, mock_extract):
        """Should request verbose_json for timestamped segments."""
        mock_extract.return_value = "/tmp/test_audio.mp3"

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = MagicMock(segments=[])
        mock_openai.return_value = mock_client

        metadata = VideoMetadata("id", "t", "c", 60, "/tmp/v.mp4")
        transcribe_video(metadata)

        call_kwargs = mock_client.audio.transcriptions.create.call_args[1]
        assert "verbose_json" in call_kwargs.get("response_format", "")

    @patch("youtube_clipper.transcribe.extract_audio")
    @patch("builtins.open")
    @patch("youtube_clipper.transcribe.OpenAI")
    def test_transcribe_with_language(self, mock_openai, mock_builtin_open, mock_extract):
        """Should accept optional language parameter."""
        mock_extract.return_value = "/tmp/test_audio.mp3"

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = MagicMock(segments=[])
        mock_openai.return_value = mock_client

        metadata = VideoMetadata("id", "t", "c", 60, "/tmp/v.mp4")
        transcribe_video(metadata, language="pt")

        call_kwargs = mock_client.audio.transcriptions.create.call_args[1]
        assert call_kwargs["language"] == "pt"

    @patch("youtube_clipper.transcribe.extract_audio")
    @patch("youtube_clipper.transcribe.OpenAI")
    def test_transcribe_api_error(self, mock_openai, mock_extract):
        """Should raise RuntimeError on API failure."""
        mock_extract.return_value = "/tmp/test_audio.mp3"

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.side_effect = Exception("API error")
        mock_openai.return_value = mock_client

        metadata = VideoMetadata("id", "t", "c", 60, "/tmp/v.mp4")

        with pytest.raises(RuntimeError, match="Transcription failed"):
            transcribe_video(metadata)