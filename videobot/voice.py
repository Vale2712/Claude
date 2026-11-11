"""Step 3: text-to-speech narration with word timings (free Microsoft Edge voices)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts

TICKS = 10_000_000  # edge-tts offsets are in 100-ns units


async def _synth(text: str, voice: str, rate: str, out: Path) -> list[tuple[float, float, str]]:
    words: list[tuple[float, float, str]] = []
    com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    with out.open("wb") as f:
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / TICKS
                words.append((start, start + chunk["duration"] / TICKS, chunk["text"]))
    return words


def synthesize(text: str, voice: str, out: Path, rate: str = "+5%") -> list[tuple[float, float, str]]:
    """Write narration MP3 to `out`; return [(start_s, end_s, word), ...]."""
    return asyncio.run(_synth(text, voice, rate, out))
