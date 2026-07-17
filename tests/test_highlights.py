"""Tests for the highlights detection module."""

from unittest.mock import MagicMock, patch

import pytest

from youtube_clipper.highlights import (
    Highlight,
    PromptConfig,
    detect_highlights,
)
from youtube_clipper.transcribe import TranscriptionSegment


class TestHighlight:
    def test_highlight_creation(self):
        h = Highlight(start=10.0, end=45.0, title="Best moment", reason="High energy")
        assert h.start == 10.0
        assert h.end == 45.0
        assert h.duration == 35.0
        assert h.title == "Best moment"
        assert h.reason == "High energy"

    def test_highlight_repr(self):
        h = Highlight(start=0.0, end=30.0, title="Intro", reason="Engaging start")
        r = repr(h)
        assert "0.0" in r
        assert "30.0" in r
        assert "Intro" in r


class TestPromptConfig:
    def test_default_prompt_config(self):
        cfg = PromptConfig()
        assert cfg.model == "gpt-4o-mini"
        assert cfg.max_tokens == 1000
        assert cfg.temperature == 0.7

    def test_custom_prompt_config(self):
        cfg = PromptConfig(model="gpt-4o", max_tokens=500, temperature=0.3)
        assert cfg.model == "gpt-4o"
        assert cfg.max_tokens == 500


class TestDetectHighlights:
    def _make_segments(self, texts: list[str]) -> list[TranscriptionSegment]:
        """Helper to create segments with 10s duration each."""
        segments = []
        for i, text in enumerate(texts):
            segments.append(
                TranscriptionSegment(start=i * 10.0, end=(i + 1) * 10.0, text=text)
            )
        return segments

    @patch("youtube_clipper.highlights.OpenAI")
    def test_detect_highlights_from_transcript(self, mock_openai):
        """Should analyze transcript and return highlights."""
        segments = self._make_segments(
            [
                "Welcome to the show today we have something amazing.",
                "We're going to reveal the secret right now.",
                "The secret is... wait for it... FIVE MILLION DOLLARS!",
                "The crowd goes wild with excitement and applause.",
                "Thank you all for watching, see you next time.",
            ]
        )

        # Mock LLM response with JSON
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='```json\n[{"start": 10, "end": 30, "title": "The Big Reveal", "reason": "Climax moment"}, {"start": 30, "end": 40, "title": "Crowd Reaction", "reason": "High energy"}]\n```'
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = detect_highlights(segments, video_duration=50)

        assert len(result) == 2
        assert result[0].title == "The Big Reveal"
        assert result[0].start == 10.0
        assert result[0].end == 30.0
        assert result[1].title == "Crowd Reaction"

    @patch("youtube_clipper.highlights.OpenAI")
    def test_detect_highlights_respects_max_clips(self, mock_openai):
        """Should limit to requested number of clips."""
        segments = self._make_segments([f"Segment {i}" for i in range(10)])

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='```json\n[{"start":0,"end":10,"title":"A","reason":"r"},{"start":10,"end":20,"title":"B","reason":"r"},{"start":20,"end":30,"title":"C","reason":"r"},{"start":30,"end":40,"title":"D","reason":"r"}]\n```'
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = detect_highlights(segments, video_duration=100, max_clips=2)

        assert len(result) == 2

    @patch("youtube_clipper.highlights.OpenAI")
    def test_detect_highlights_clamps_to_video_duration(self, mock_openai):
        """Should clamp highlight times to video duration."""
        segments = self._make_segments(["Short video"])

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='```json\n[{"start":0,"end":999,"title":"Too long","reason":"r"}]\n```'
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = detect_highlights(segments, video_duration=30)

        assert result[0].end == 30.0  # clamped to video duration

    @patch("youtube_clipper.highlights.OpenAI")
    def test_detect_highlights_empty_response(self, mock_openai):
        """Should return empty list if LLM finds no highlights."""
        segments = self._make_segments(["Just silence..."])

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="```json\n[]\n```"))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = detect_highlights(segments, video_duration=10)
        assert result == []

    @patch("youtube_clipper.highlights.OpenAI")
    def test_detect_highlights_custom_prompt(self, mock_openai):
        """Should use custom prompt config when provided."""
        segments = self._make_segments(["Test"])

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="```json\n[]\n```"))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        cfg = PromptConfig(model="gpt-4o", temperature=0.3)
        detect_highlights(segments, video_duration=10, config=cfg)

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o"
        assert call_kwargs["temperature"] == 0.3

    @patch("youtube_clipper.highlights.OpenAI")
    def test_detect_highlights_invalid_json(self, mock_openai):
        """Should handle malformed LLM JSON gracefully."""
        segments = self._make_segments(["Test"])

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="not valid json at all {{{"))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = detect_highlights(segments, video_duration=10)
        assert result == []