"""Tests for YouTube search module."""

from unittest.mock import MagicMock, patch

import pytest

from youtube_clipper.search import SearchResult, search_youtube, _parse_duration


class TestSearchResult:
    def test_creation(self):
        sr = SearchResult(
            video_id="abc123",
            title="Test Video",
            channel="Test Channel",
            url="https://youtube.com/watch?v=abc123",
            duration="5:30",
            views=1000,
            published_at="2024-01-01",
            thumbnail="https://img.example.com/thumb.jpg",
        )
        assert sr.video_id == "abc123"
        assert sr.duration == "5:30"
        assert sr.url == "https://youtube.com/watch?v=abc123"

    def test_repr(self):
        sr = SearchResult("id", "A" * 50, "ch", "url", "1:00", 0, "2024", "thumb")
        r = repr(sr)
        assert "id" in r
        assert "ch" in r


class TestParseDuration:
    def test_minutes_seconds(self):
        assert _parse_duration("PT5M30S") == "5:30"

    def test_hours_minutes_seconds(self):
        assert _parse_duration("PT1H2M3S") == "1:02:03"

    def test_seconds_only(self):
        assert _parse_duration("PT45S") == "0:45"

    def test_minutes_only(self):
        assert _parse_duration("PT10M") == "10:00"


class TestSearchYouTube:
    @patch("youtube_clipper.search.build")
    def test_no_api_key_raises(self, mock_build):
        """Should raise ValueError without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="API key"):
                search_youtube("test", api_key=None)

    @patch("youtube_clipper.search.build")
    def test_search_returns_results(self, mock_build):
        """Should return list of SearchResult from API response."""
        mock_youtube = MagicMock()
        mock_search = MagicMock()
        mock_videos = MagicMock()

        # Mock search.list
        mock_search.list.return_value.execute.return_value = {
            "items": [
                {
                    "id": {"videoId": "vid001"},
                    "snippet": {
                        "title": "Amazing Video",
                        "channelTitle": "Cool Channel",
                        "publishedAt": "2024-06-15T10:00:00Z",
                        "thumbnails": {
                            "medium": {"url": "https://img.example.com/1.jpg"}
                        },
                    },
                },
                {
                    "id": {"videoId": "vid002"},
                    "snippet": {
                        "title": "Second Video",
                        "channelTitle": "Another Channel",
                        "publishedAt": "2024-06-14T08:00:00Z",
                        "thumbnails": {
                            "medium": {"url": "https://img.example.com/2.jpg"}
                        },
                    },
                },
            ]
        }

        # Mock videos.list for durations
        mock_videos.list.return_value.execute.return_value = {
            "items": [
                {"id": "vid001", "contentDetails": {"duration": "PT10M30S"}},
                {"id": "vid002", "contentDetails": {"duration": "PT5M0S"}},
            ]
        }

        mock_youtube.search.return_value = mock_search
        mock_youtube.videos.return_value = mock_videos
        mock_build.return_value = mock_youtube

        results = search_youtube("amazing", api_key="fake_key")

        assert len(results) == 2
        assert results[0].video_id == "vid001"
        assert results[0].title == "Amazing Video"
        assert results[0].channel == "Cool Channel"
        assert results[0].duration == "10:30"
        assert results[0].url == "https://youtube.com/watch?v=vid001"
        assert results[1].duration == "5:00"

    @patch("youtube_clipper.search.build")
    def test_search_respects_max_results(self, mock_build):
        """Should limit to requested max_results."""
        mock_youtube = MagicMock()
        mock_search = MagicMock()
        mock_videos = MagicMock()

        mock_search.list.return_value.execute.return_value = {"items": []}
        mock_videos.list.return_value.execute.return_value = {"items": []}
        mock_youtube.search.return_value = mock_search
        mock_youtube.videos.return_value = mock_videos
        mock_build.return_value = mock_youtube

        search_youtube("test", max_results=3, api_key="key")

        # Verify search.list was called with correct maxResults
        call_kwargs = mock_search.list.call_args[1]
        assert call_kwargs["maxResults"] == 3