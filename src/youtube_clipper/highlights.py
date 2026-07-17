"""AI-powered highlight detection from video transcripts.

Analyzes transcribed video content using an LLM to identify
the most engaging, viral-worthy moments for clipping.
"""

import json
import re
from dataclasses import dataclass, field

from openai import OpenAI

from youtube_clipper.transcribe import TranscriptionSegment


@dataclass
class Highlight:
    """A detected highlight moment in a video."""

    start: float  # seconds
    end: float  # seconds
    title: str
    reason: str = ""

    @property
    def duration(self) -> float:
        """Duration of this highlight in seconds."""
        return self.end - self.start

    def __repr__(self) -> str:
        return (
            f"Highlight({self.start:.1f}s–{self.end:.1f}s, "
            f"title={self.title!r})"
        )


@dataclass
class PromptConfig:
    """Configuration for the highlight detection LLM prompt."""

    model: str = "gpt-4o-mini"
    max_tokens: int = 1000
    temperature: float = 0.7
    system_prompt: str = field(default_factory=lambda: (
        "You are an expert video editor specializing in viral content. "
        "Your job is to analyze video transcripts and identify the most "
        "engaging, shareable moments that would work well as short clips. "
        "Look for: climax moments, surprising reveals, funny exchanges, "
        "emotional peaks, action highlights, quotable lines, and key insights. "
        "Return ONLY valid JSON array of highlights with start/end timestamps."
    ))


DEFAULT_MAX_CLIPS = 3
DEFAULT_MAX_DURATION = 60  # seconds per clip


def _build_transcript_text(segments: list[TranscriptionSegment]) -> str:
    """Build a formatted transcript string for the LLM prompt."""
    lines = []
    for seg in segments:
        timestamp = f"[{int(seg.start // 60):02d}:{int(seg.start % 60):02d}]"
        lines.append(f"{timestamp} {seg.text}")
    return "\n".join(lines)


def _build_user_prompt(
    transcript_text: str,
    video_title: str,
    video_duration: float,
    max_clips: int,
    max_duration: int,
) -> str:
    """Build the user prompt for highlight detection."""
    return (
        f"Analyze this video transcript and find the {max_clips} best moments "
        f"for short clips (max {max_duration}s each).\n\n"
        f"Video: {video_title}\n"
        f"Duration: {int(video_duration)}s\n\n"
        f"Transcript:\n{transcript_text}\n\n"
        "Return ONLY a JSON array of highlights:\n"
        '```json\n[{"start": <seconds>, "end": <seconds>, '
        '"title": "<short title>", "reason": "<why this moment works>"}]\n```'
    )


def _parse_llm_response(content: str) -> list[dict]:
    """Extract JSON array from LLM response."""
    # Try to find JSON in code blocks or raw
    json_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", content, re.DOTALL)
    if json_match:
        content = json_match.group(1)

    # Try direct JSON parse
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    return []


def detect_highlights(
    segments: list[TranscriptionSegment],
    video_duration: float,
    video_title: str = "Video",
    max_clips: int = DEFAULT_MAX_CLIPS,
    max_clip_duration: int = DEFAULT_MAX_DURATION,
    config: PromptConfig | None = None,
    api_key: str | None = None,
) -> list[Highlight]:
    """Detect highlight moments from a transcript using AI.

    Args:
        segments: Transcribed segments with timestamps.
        video_duration: Total video duration in seconds.
        video_title: Title of the video (for context).
        max_clips: Maximum number of highlights to return.
        max_clip_duration: Maximum duration per clip in seconds.
        config: Optional prompt/model configuration.
        api_key: OpenAI API key.

    Returns:
        List of Highlight objects with start/end times and titles.

    Raises:
        RuntimeError: If LLM API call fails.
    """
    if not segments:
        return []

    cfg = config or PromptConfig()
    client = OpenAI(api_key=api_key) if api_key else OpenAI()

    transcript_text = _build_transcript_text(segments)
    user_prompt = _build_user_prompt(
        transcript_text, video_title, video_duration, max_clips, max_clip_duration
    )

    try:
        response = client.chat.completions.create(
            model=cfg.model,
            messages=[
                {"role": "system", "content": cfg.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
        )
        content = response.choices[0].message.content or ""
    except Exception as e:
        raise RuntimeError(f"Highlight detection failed: {e}") from e

    raw_highlights = _parse_llm_response(content)

    # Convert to Highlight objects with validation
    highlights = []
    for h in raw_highlights[:max_clips]:
        try:
            start = max(0.0, float(h.get("start", 0)))
            end = min(float(video_duration), float(h.get("end", start + max_clip_duration)))
            title = str(h.get("title", "Highlight"))
            reason = str(h.get("reason", ""))

            # Clamp duration
            if end - start > max_clip_duration:
                end = start + max_clip_duration

            highlights.append(
                Highlight(start=start, end=end, title=title, reason=reason)
            )
        except (ValueError, TypeError):
            continue

    return highlights