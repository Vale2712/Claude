"""Step 2: write an original, scene-by-scene script for one idea."""

from __future__ import annotations

from . import llm
from .config import FORMATS

SCRIPT_SYSTEM = (
    "You are a professional scriptwriter for viral faceless videos. You write ORIGINAL "
    "scripts in your own words (never copy sentences from sources), with a strong hook in "
    "the first 3 seconds, short spoken sentences, curiosity loops and a clear payoff. "
    "Only state facts that are supported by the research provided."
)

SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "thumbnail_text": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "narration": {"type": "string"},
                    "on_screen_text": {"type": "string"},
                    "visual_query": {"type": "string"},
                },
                "required": ["narration", "on_screen_text", "visual_query"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "description", "tags", "thumbnail_text", "scenes"],
    "additionalProperties": False,
}


def write_script(idea: dict, video_format: str = "short", language: str = "en",
                 notes: str = "") -> dict:
    fmt = FORMATS[video_format]
    facts = "\n".join(f"- {f}" for f in idea.get("key_facts", []))
    sources = "\n".join(f"- {s}" for s in idea.get("sources", []))
    return llm.structured(
        SCRIPT_SYSTEM,
        f"Write a {video_format} video script in language '{language}'.\n\n"
        f"Idea: {idea['title']}\nAngle: {idea.get('angle', '')}\n"
        f"Audience: {idea.get('target_audience', '')}\nWhy now: {idea.get('why_now', '')}\n"
        f"Key facts:\n{facts}\nSources:\n{sources}\n\n"
        f"Extra research notes (for fact checking only):\n<notes>\n{notes[:20000]}\n</notes>\n\n"
        f"Requirements:\n"
        f"- Total narration about {fmt['words']} words, split into {fmt['scenes']} scenes.\n"
        f"- Scene 1 is the hook. The last scene ends with a short call to action (follow/subscribe).\n"
        f"- narration: exactly what the voice says; plain text, no stage directions, no emojis.\n"
        f"- on_screen_text: max 6 punchy words shown on screen (may be empty).\n"
        f"- visual_query: 2-4 ENGLISH words to search stock footage for this scene "
        f"(concrete, filmable things, e.g. 'rocket launch night').\n"
        f"- description: 2-4 sentences for the upload, then the source links.\n"
        f"- tags: 8-15 tags. thumbnail_text: max 4 words.",
        SCRIPT_SCHEMA,
        effort="high",
    )


def script_to_markdown(script: dict) -> str:
    lines = [f"# {script['title']}", "", script["description"], "",
             "**Tags:** " + ", ".join(script["tags"]), "",
             f"**Thumbnail text:** {script['thumbnail_text']}", ""]
    for i, s in enumerate(script["scenes"], 1):
        lines += [f"## Scene {i}", f"*Visual:* {s['visual_query']}  ",
                  f"*On screen:* {s['on_screen_text']}", "", s["narration"], ""]
    return "\n".join(lines)
