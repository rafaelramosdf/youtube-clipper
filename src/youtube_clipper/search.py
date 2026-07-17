"""YouTube search module using YouTube Data API v3.

Searches for videos by keyword and returns structured results.
"""

import os
from dataclasses import dataclass

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


@dataclass
class SearchResult:
    """A single YouTube search result."""

    video_id: str
    title: str
    channel: str
    url: str
    duration: str  # ISO 8601 or human-readable
    views: int
    published_at: str
    thumbnail: str

    def __repr__(self) -> str:
        return (
            f"SearchResult(id={self.video_id!r}, title={self.title[:40]!r}..., "
            f"channel={self.channel!r})"
        )


def search_youtube(
    query: str,
    max_results: int = 5,
    api_key: str | None = None,
) -> list[SearchResult]:
    """Search YouTube for videos matching a query.

    Args:
        query: Search keywords.
        max_results: Maximum results (1–50).
        api_key: YouTube Data API v3 key. Falls back to YOUTUBE_API_KEY env var.

    Returns:
        List of SearchResult with video metadata.

    Raises:
        ValueError: If no API key is available.
        RuntimeError: If API call fails.
    """
    api_key = api_key or os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise ValueError(
            "YouTube API key not configured. "
            "Set YOUTUBE_API_KEY environment variable or pass api_key parameter."
        )

    try:
        youtube = build("youtube", "v3", developerKey=api_key)

        request = youtube.search().list(
            part="snippet",
            q=query,
            maxResults=min(max_results, 50),
            type="video",
            order="relevance",
        )
        response = request.execute()

        # Get video IDs for duration lookup
        video_ids = [item["id"]["videoId"] for item in response.get("items", [])]
        durations = _get_video_durations(youtube, video_ids)

        results = []
        for item in response.get("items", []):
            vid = item["id"]["videoId"]
            snippet = item["snippet"]

            results.append(
                SearchResult(
                    video_id=vid,
                    title=snippet.get("title", "Untitled"),
                    channel=snippet.get("channelTitle", "Unknown"),
                    url=f"https://youtube.com/watch?v={vid}",
                    duration=durations.get(vid, "?"),
                    views=0,  # Not available in search.list
                    published_at=snippet.get("publishedAt", "")[:10],
                    thumbnail=(
                        snippet.get("thumbnails", {})
                        .get("medium", {})
                        .get("url", "")
                    ),
                )
            )

        return results

    except HttpError as e:
        raise RuntimeError(f"YouTube API error: {e}") from e


def _get_video_durations(youtube, video_ids: list[str]) -> dict[str, str]:
    """Fetch video durations in bulk."""
    if not video_ids:
        return {}

    try:
        request = youtube.videos().list(
            part="contentDetails",
            id=",".join(video_ids),
        )
        response = request.execute()

        durations = {}
        for item in response.get("items", []):
            vid = item["id"]
            raw = item["contentDetails"]["duration"]  # ISO 8601: PT1H2M3S
            durations[vid] = _parse_duration(raw)

        return durations
    except HttpError:
        return {}


def _parse_duration(iso_duration: str) -> str:
    """Convert ISO 8601 duration to human-readable format."""
    import re

    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration)
    if not match:
        return iso_duration

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"