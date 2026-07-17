"""Audio transcription module using OpenAI Whisper API.

Extracts audio from video files via FFmpeg, then transcribes
using Whisper API to produce timestamped text segments.
"""

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI

from youtube_clipper.download import VideoMetadata


@dataclass
class TranscriptionSegment:
    """A single segment of transcribed text with timestamps."""

    start: float  # seconds
    end: float  # seconds
    text: str

    @property
    def duration(self) -> float:
        """Duration of this segment in seconds."""
        return self.end - self.start

    def __repr__(self) -> str:
        return (
            f"TranscriptionSegment(start={self.start:.1f}, "
            f"end={self.end:.1f}, text={self.text[:40]!r}...)"
            if len(self.text) > 40
            else f"TranscriptionSegment(start={self.start:.1f}, "
            f"end={self.end:.1f}, text={self.text!r})"
        )


def extract_audio(video_path: str, output_path: str | None = None) -> str:
    """Extract audio track from video as MP3 using FFmpeg.

    Args:
        video_path: Path to the input video file.
        output_path: Optional output path. Defaults to temp file.

    Returns:
        Path to the extracted audio file (.mp3).

    Raises:
        FileNotFoundError: If video_path does not exist.
        RuntimeError: If FFmpeg fails.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if output_path is None:
        base = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(tempfile.gettempdir(), f"{base}_audio.mp3")

    cmd = [
        "ffmpeg",
        "-y",  # overwrite output
        "-i", video_path,
        "-vn",  # no video
        "-acodec", "libmp3lame",
        "-q:a", "2",  # high quality
        output_path,
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg audio extraction failed: {e.stderr.decode()}") from e
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg audio extraction timed out (120s)")

    return output_path


def transcribe_video(
    metadata: VideoMetadata,
    language: str | None = None,
    api_key: str | None = None,
) -> list[TranscriptionSegment]:
    """Transcribe a video using OpenAI Whisper API.

    Extracts audio from the video, then sends it to Whisper for
    transcription with word-level timestamps.

    Args:
        metadata: VideoMetadata from download module.
        language: Optional language code (e.g., 'pt', 'en').
                  If None, Whisper auto-detects.
        api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.

    Returns:
        List of TranscriptionSegment with timestamps and text.

    Raises:
        RuntimeError: If transcription fails.
    """
    # Extract audio
    audio_path = extract_audio(metadata.file_path)

    try:
        client = OpenAI(api_key=api_key) if api_key else OpenAI()

        with open(audio_path, "rb") as audio_file:
            kwargs: dict = {
                "model": "whisper-1",
                "file": audio_file,
                "response_format": "verbose_json",
                "timestamp_granularities": ["segment"],
            }
            if language:
                kwargs["language"] = language

            transcription = client.audio.transcriptions.create(**kwargs)

        # Convert to our dataclass
        segments = [
            TranscriptionSegment(
                start=seg.start,
                end=seg.end,
                text=seg.text.strip(),
            )
            for seg in transcription.segments
        ]

        return segments

    except Exception as e:
        raise RuntimeError(f"Transcription failed for {metadata.video_id}: {e}") from e
    finally:
        # Clean up temporary audio file
        if os.path.exists(audio_path):
            os.remove(audio_path)