"""Video clipping module using FFmpeg.

Cuts highlight segments from source videos using FFmpeg
with stream copy for speed (falls back to re-encode).
"""

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from youtube_clipper.highlights import Highlight


@dataclass
class ClipResult:
    """Result of a single clip operation."""

    highlight: Highlight
    output_path: str
    success: bool
    error: str = ""

    def __repr__(self) -> str:
        status = "OK" if self.success else f"FAIL: {self.error}"
        return f"ClipResult({self.highlight.title!r} → {status})"


def _sanitize_filename(name: str) -> str:
    """Convert a title into a safe filename slug."""
    # Remove special chars, keep alphanumeric + hyphens + underscores
    slug = re.sub(r"[^\w\s-]", "", name)
    slug = re.sub(r"\s+", "-", slug)
    slug = slug.strip("-").lower()
    return slug or "clip"


def clip_video(
    video_path: str,
    highlights: list[Highlight],
    output_dir: str = "/tmp/youtube-clipper/clips",
    video_id: str = "",
) -> list[ClipResult]:
    """Cut highlight segments from a video.

    Uses FFmpeg stream copy for speed; re-encodes if copy fails.

    Args:
        video_path: Path to source video.
        highlights: List of highlights to extract.
        output_dir: Directory for output clips.
        video_id: Optional video ID for filename prefix.

    Returns:
        List of ClipResult, one per highlight attempt.
    """
    if not highlights:
        return []

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Check source exists
    if not os.path.exists(video_path):
        return [
            ClipResult(
                highlight=h,
                output_path="",
                success=False,
                error=f"Source video not found: {video_path}",
            )
            for h in highlights
        ]

    results = []
    prefix = f"{video_id}_" if video_id else ""

    for i, hl in enumerate(highlights):
        slug = _sanitize_filename(hl.title)
        out_file = output_path / f"{prefix}clip_{i + 1:02d}_{slug}.mp4"

        start = hl.start
        duration = hl.duration

        # Strategy 1: stream copy (fast)
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(start),
            "-i", video_path,
            "-t", str(duration),
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            str(out_file),
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=60)
            success = True
            error = ""
        except subprocess.CalledProcessError as e:
            # Strategy 2: re-encode
            cmd_reencode = [
                "ffmpeg",
                "-y",
                "-ss", str(start),
                "-i", video_path,
                "-t", str(duration),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-preset", "ultrafast",
                str(out_file),
            ]
            try:
                subprocess.run(cmd_reencode, check=True, capture_output=True, timeout=120)
                success = True
                error = ""
            except subprocess.CalledProcessError as e2:
                success = False
                error = f"FFmpeg failed: {e2.stderr.decode() if e2.stderr else str(e2)}"
            except subprocess.TimeoutExpired:
                success = False
                error = "FFmpeg re-encode timed out (120s)"
        except subprocess.TimeoutExpired:
            success = False
            error = "FFmpeg stream copy timed out (60s)"

        results.append(
            ClipResult(
                highlight=hl,
                output_path=str(out_file) if success else "",
                success=success,
                error=error,
            )
        )

    return results