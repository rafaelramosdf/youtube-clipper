"""Pipeline orchestrator for the YouTube Clipper workflow.

Coordinates search → download → transcribe → highlights → clip
as a single integrated pipeline.
"""

import os
from collections.abc import Callable
from dataclasses import dataclass, field

from youtube_clipper.clip import ClipResult, clip_video
from youtube_clipper.download import VideoMetadata, download_video
from youtube_clipper.highlights import Highlight, PromptConfig, detect_highlights
from youtube_clipper.search import SearchResult, search_youtube
from youtube_clipper.transcribe import TranscriptionSegment, transcribe_video


@dataclass
class PipelineResult:
    """Complete result of a pipeline run."""

    search_results: list[SearchResult] = field(default_factory=list)
    selected_videos: list[SearchResult] = field(default_factory=list)
    downloads: list[VideoMetadata] = field(default_factory=list)
    transcriptions: dict[str, list[TranscriptionSegment]] = field(default_factory=dict)
    highlights: dict[str, list[Highlight]] = field(default_factory=dict)
    clips: list[ClipResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def run_pipeline(
    query: str,
    video_urls: list[str] | None = None,
    max_search_results: int = 5,
    max_clips_per_video: int = 3,
    max_clip_duration: int = 60,
    language: str | None = None,
    output_dir: str = "/tmp/youtube-clipper/clips",
    api_keys: dict | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> PipelineResult:
    """Run the complete YouTube clipper pipeline.

    Args:
        query: Search query for YouTube.
        video_urls: Optional specific video URLs to process (skips search).
        max_search_results: Max results from YouTube search.
        max_clips_per_video: Max clips per video.
        max_clip_duration: Max duration per clip in seconds.
        language: Language hint for transcription.
        output_dir: Directory for output clips.
        api_keys: Dict with 'youtube' and 'openai' keys.
        progress_callback: Optional callback(step: str).

    Returns:
        PipelineResult with all intermediate data and final clips.
    """
    result = PipelineResult()
    keys = api_keys or {}

    def progress(step: str):
        if progress_callback:
            progress_callback(step)

    # Step 1: Search or use provided URLs
    if video_urls:
        progress("Using provided video URLs...")
        for url in video_urls:
            result.selected_videos.append(
                SearchResult(
                    video_id=url.split("v=")[-1].split("&")[0],
                    title="User-selected video",
                    channel="?",
                    url=url,
                    duration="?",
                    views=0,
                    published_at="?",
                    thumbnail="",
                )
            )
    else:
        progress(f"Searching YouTube for: {query}")
        try:
            result.search_results = search_youtube(
                query,
                max_results=max_search_results,
                api_key=keys.get("youtube"),
            )
            result.selected_videos = result.search_results
            progress(f"Found {len(result.search_results)} videos")
        except Exception as e:
            result.errors.append(f"Search failed: {e}")
            return result

    # Step 2: Download each video
    for video in result.selected_videos:
        progress(f"Downloading: {video.title[:50]}")
        try:
            metadata = download_video(video.url)
            result.downloads.append(metadata)
        except Exception as e:
            result.errors.append(f"Download failed for {video.video_id}: {e}")

    if not result.downloads:
        result.errors.append("No videos were downloaded successfully")
        return result

    # Step 3: Transcribe each video
    for metadata in result.downloads:
        progress(f"Transcribing: {metadata.title[:50]}")
        try:
            segments = transcribe_video(
                metadata,
                language=language,
                api_key=keys.get("openai"),
            )
            result.transcriptions[metadata.video_id] = segments
            progress(f"  → {len(segments)} segments transcribed")
        except Exception as e:
            result.errors.append(f"Transcription failed for {metadata.video_id}: {e}")

    # Step 4: Detect highlights
    for metadata in result.downloads:
        segments = result.transcriptions.get(metadata.video_id, [])
        if not segments:
            continue

        progress(f"Detecting highlights in: {metadata.title[:50]}")
        try:
            hl = detect_highlights(
                segments,
                video_duration=metadata.duration,
                video_title=metadata.title,
                max_clips=max_clips_per_video,
                max_clip_duration=max_clip_duration,
                api_key=keys.get("openai"),
            )
            result.highlights[metadata.video_id] = hl
            progress(f"  → {len(hl)} highlights found")
        except Exception as e:
            result.errors.append(f"Highlight detection failed for {metadata.video_id}: {e}")

    # Step 5: Clip videos
    for metadata in result.downloads:
        highlights = result.highlights.get(metadata.video_id, [])
        if not highlights:
            continue

        progress(f"Clipping {len(highlights)} segments from: {metadata.title[:50]}")
        clip_results = clip_video(
            metadata.file_path,
            highlights,
            output_dir=output_dir,
            video_id=metadata.video_id,
        )
        result.clips.extend(clip_results)
        successful = sum(1 for c in clip_results if c.success)
        progress(f"  → {successful}/{len(clip_results)} clips created")

    return result