"""Tests for the pipeline orchestrator."""

from unittest.mock import MagicMock, patch

from youtube_clipper.clip import ClipResult
from youtube_clipper.download import VideoMetadata
from youtube_clipper.highlights import Highlight
from youtube_clipper.pipeline import PipelineResult, run_pipeline


class TestPipelineResult:
    def test_default_creation(self):
        pr = PipelineResult()
        assert pr.search_results == []
        assert pr.clips == []
        assert pr.errors == []


class TestRunPipeline:
    @patch("youtube_clipper.pipeline.clip_video")
    @patch("youtube_clipper.pipeline.detect_highlights")
    @patch("youtube_clipper.pipeline.transcribe_video")
    @patch("youtube_clipper.pipeline.download_video")
    @patch("youtube_clipper.pipeline.search_youtube")
    def test_pipeline_with_search(
        self, mock_search, mock_dl, mock_trans, mock_hl, mock_clip
    ):
        """Full pipeline should run all steps with mocked dependencies."""
        # Mock search results
        from youtube_clipper.search import SearchResult

        mock_search.return_value = [
            SearchResult("vid1", "Video 1", "Ch1", "https://youtube.com/watch?v=vid1", "5:00", 1000, "2024", "img1"),
            SearchResult("vid2", "Video 2", "Ch2", "https://youtube.com/watch?v=vid2", "3:00", 500, "2024", "img2"),
        ]

        # Mock download
        meta1 = VideoMetadata("vid1", "Video 1", "Ch1", 300, "/tmp/vid1.mp4")
        meta2 = VideoMetadata("vid2", "Video 2", "Ch2", 180, "/tmp/vid2.mp4")
        mock_dl.side_effect = [meta1, meta2]

        # Mock transcription
        from youtube_clipper.transcribe import TranscriptionSegment

        segs = [TranscriptionSegment(0, 10, "Hello world")]
        mock_trans.return_value = segs

        # Mock highlights
        hl = [Highlight(0, 30, "Best", "reason")]
        mock_hl.return_value = hl

        # Mock clip
        mock_clip.return_value = [
            ClipResult(hl[0], "/tmp/clip1.mp4", success=True)
        ]

        result = run_pipeline(
            query="test query",
            api_keys={"youtube": "fake_yt", "openai": "fake_oai"},
        )

        assert len(result.search_results) == 2
        assert len(result.downloads) == 2
        assert len(result.clips) == 2  # one per video
        assert result.errors == []

    @patch("youtube_clipper.pipeline.clip_video")
    @patch("youtube_clipper.pipeline.detect_highlights")
    @patch("youtube_clipper.pipeline.transcribe_video")
    @patch("youtube_clipper.pipeline.download_video")
    def test_pipeline_with_urls(self, mock_dl, mock_trans, mock_hl, mock_clip):
        """Pipeline with direct URLs should skip search."""
        meta = VideoMetadata("vid", "V", "C", 120, "/tmp/v.mp4")

        from youtube_clipper.transcribe import TranscriptionSegment

        mock_dl.return_value = meta
        mock_trans.return_value = [TranscriptionSegment(0, 10, "test")]
        mock_hl.return_value = [Highlight(0, 30, "H", "r")]
        mock_clip.return_value = [ClipResult(Highlight(0, 30, "H", "r"), "/tmp/c.mp4", True)]

        result = run_pipeline(
            query="ignored",
            video_urls=["https://youtube.com/watch?v=abc123"],
        )

        # search_youtube should NOT be called (we're using URLs directly)
        assert len(result.selected_videos) == 1
        assert result.selected_videos[0].video_id == "abc123"

    @patch("youtube_clipper.pipeline.search_youtube")
    def test_pipeline_search_failure(self, mock_search):
        """Pipeline should handle search failures gracefully."""
        mock_search.side_effect = Exception("API quota exceeded")

        result = run_pipeline(query="fail test")

        assert len(result.errors) > 0
        assert "Search failed" in result.errors[0]

    @patch("youtube_clipper.pipeline.clip_video")
    @patch("youtube_clipper.pipeline.detect_highlights")
    @patch("youtube_clipper.pipeline.transcribe_video")
    @patch("youtube_clipper.pipeline.download_video")
    @patch("youtube_clipper.pipeline.search_youtube")
    def test_pipeline_no_highlights_no_clips(
        self, mock_search, mock_dl, mock_trans, mock_hl, mock_clip
    ):
        """If no highlights found, should not attempt clipping."""
        from youtube_clipper.search import SearchResult

        mock_search.return_value = [
            SearchResult("v1", "V", "C", "url", "1:00", 0, "2024", "img")
        ]
        mock_dl.return_value = VideoMetadata("v1", "V", "C", 60, "/tmp/v.mp4")
        mock_trans.return_value = []
        # No highlights since no transcript

        result = run_pipeline(query="test")

        assert len(result.clips) == 0