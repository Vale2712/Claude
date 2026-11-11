"""Step 1: search the internet for fresh video ideas in a niche."""

from __future__ import annotations

from datetime import date

from . import llm

RESEARCH_SYSTEM = (
    "You are a trend researcher for a video channel. Use web search to find what is "
    "new, trending or widely discussed right now. Prefer recent sources (news, Reddit, "
    "YouTube/TikTok trends, Google Trends, niche blogs). Always note the source URLs."
)

IDEAS_SCHEMA = {
    "type": "object",
    "properties": {
        "ideas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "angle": {"type": "string"},
                    "why_now": {"type": "string"},
                    "target_audience": {"type": "string"},
                    "key_facts": {"type": "array", "items": {"type": "string"}},
                    "sources": {"type": "array", "items": {"type": "string"}},
                    "score": {"type": "integer"},
                },
                "required": ["title", "angle", "why_now", "target_audience", "key_facts", "sources", "score"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["ideas"],
    "additionalProperties": False,
}


def find_ideas(niche: str, count: int = 5, video_format: str = "short",
               language: str = "en", avoid: list[str] | None = None) -> tuple[list[dict], str]:
    """Return (ideas sorted best-first, raw research notes)."""
    avoid_txt = "\n".join(f"- {t}" for t in (avoid or [])[-50:]) or "(none yet)"
    notes = llm.research(
        RESEARCH_SYSTEM,
        f"Today is {date.today().isoformat()}.\n"
        f"Niche / channel topic: {niche}\n"
        f"Video format: {video_format} ({'vertical short, under 60 s' if video_format == 'short' else 'horizontal, 5-8 min'})\n\n"
        f"Research the internet for what is trending or newly relevant in this niche right now, "
        f"then propose {count + 3} concrete video ideas with real potential to get views. "
        f"For each: a catchy title, the unique angle, why it is timely, the audience, "
        f"3-6 verified key facts and the source URLs.\n\n"
        f"Do NOT repeat these topics we already made videos about:\n{avoid_txt}",
    )
    data = llm.structured(
        "You turn research notes into a clean list of video ideas.",
        f"Extract the {count} best video ideas from these research notes. Titles in language "
        f"'{language}'. Score each 1-10 for view potential (novelty, curiosity, timeliness). "
        f"Keep only facts and URLs that appear in the notes.\n\n<notes>\n{notes}\n</notes>",
        IDEAS_SCHEMA,
        effort="medium",
    )
    ideas = sorted(data["ideas"], key=lambda i: i["score"], reverse=True)[:count]
    return ideas, notes
