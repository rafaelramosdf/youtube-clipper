"""Video download module using yt-dlp.

Downloads YouTube videos in MP4 format up to 1080p quality
and returns structured metadata about the downloaded file.
"""

import os
from dataclasses import dataclass
from pathlib import Path

import yt_dlp


@dataclass
class VideoMetadata:
    """Metadata for a downloaded video."""

    video_id: str
    title: str
    channel: str
    duration: int  # seconds
    file_path: str

    def __repr__(self) -> str:
        return (
            f"VideoMetadata(id={self.video_id!r}, title={self.title!r}, "
            f"channel={self.channel!r}, duration={self.duration}s, "
            f"file={self.file_path!r})"
        )


def download_video(url: str, output_dir: str | None = None) -> VideoMetadata:
    """Download a YouTube video and return its metadata.

    Args:
        url: YouTube video URL or watch ID.
        output_dir: Directory to save the video. Defaults to /tmp/youtube-clipper/.

    Returns:
        VideoMetadata with video info and local file path.

    Raises:
        RuntimeError: If download fails for any reason.
    """
    if output_dir is None:
        output_dir = "/tmp/youtube-clipper"

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "merge_output_format": "mp4",
        "outtmpl": str(output_path / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

            # yt-dlp may add extra extensions; ensure we have the .mp4
            if not os.path.exists(file_path):
                # Try with .mp4 extension
                base = os.path.splitext(file_path)[0]
                file_path = f"{base}.mp4"

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Downloaded file not found: {file_path}")

            return VideoMetadata(
                video_id=info.get("id", ""),
                title=info.get("title", "Unknown"),
                channel=info.get("channel", info.get("uploader", "Unknown")),
                duration=info.get("duration", 0) or 0,
                file_path=file_path,
            )
    except Exception as e:
        raise RuntimeError(f"Failed to download video from {url}: {e}") from e