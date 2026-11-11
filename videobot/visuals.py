"""Step 4: find footage for each scene (Pexels) or render a fallback card."""

from __future__ import annotations

import random
import textwrap
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .config import settings

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]

_used_ids: set[int] = set()


def font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def pexels_video(query: str, size: tuple[int, int], orientation: str, out: Path) -> Path | None:
    """Download a matching stock clip, or return None if unavailable."""
    if not settings.pexels_api_key:
        return None
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            params={"query": query, "orientation": orientation, "per_page": 15, "size": "medium"},
            headers={"Authorization": settings.pexels_api_key},
            timeout=30,
        )
        r.raise_for_status()
        videos = [v for v in r.json().get("videos", []) if v["id"] not in _used_ids]
        if not videos:
            return None
        video = random.choice(videos[:5])
        _used_ids.add(video["id"])
        target_w = min(size)
        files = [f for f in video["video_files"] if f.get("file_type") == "video/mp4" and f.get("width")]
        # smallest file that is still at least the target resolution, else the largest
        files.sort(key=lambda f: min(f["width"], f["height"]))
        best = next((f for f in files if min(f["width"], f["height"]) >= target_w), files[-1])
        with requests.get(best["link"], stream=True, timeout=120) as dl:
            dl.raise_for_status()
            with out.open("wb") as f:
                for part in dl.iter_content(1 << 20):
                    f.write(part)
        return out
    except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
        print(f"    ! Pexels failed for '{query}': {exc}")
        return None


def text_card(text: str, size: tuple[int, int], out: Path, seed: int = 0) -> Path:
    """Gradient background with big centered text (used when no footage is found)."""
    w, h = size
    rnd = random.Random(seed)
    c1 = tuple(rnd.randint(10, 80) for _ in range(3))
    c2 = tuple(rnd.randint(60, 180) for _ in range(3))
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        draw.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(c1, c2)))
    for _ in range(12):  # soft bokeh blobs
        r = rnd.randint(w // 12, w // 4)
        x, y = rnd.randint(0, w), rnd.randint(0, h)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=tuple(min(255, c + 40) for c in c2))
    img = img.filter(ImageFilter.GaussianBlur(w // 25))
    if text:
        draw = ImageDraw.Draw(img)
        f = font(w // 11)
        lines = textwrap.wrap(text.upper(), width=14 if w < h else 24)
        line_h = int(f.size * 1.2)
        y = (h - line_h * len(lines)) // 2
        for line in lines:
            tw = draw.textlength(line, font=f)
            draw.text(((w - tw) / 2, y), line, font=f, fill="white",
                      stroke_width=max(2, f.size // 14), stroke_fill="black")
            y += line_h
    img.save(out)
    return out


def text_overlay(text: str, size: tuple[int, int], out: Path) -> Path:
    """Transparent PNG with a headline box near the top of the frame."""
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if text:
        draw = ImageDraw.Draw(img)
        f = font(w // 14 if w < h else w // 28)
        lines = textwrap.wrap(text.upper(), width=18 if w < h else 36)
        line_h = int(f.size * 1.25)
        box_w = max(draw.textlength(l, font=f) for l in lines) + f.size
        box_h = line_h * len(lines) + f.size // 2
        x0, y0 = (w - box_w) / 2, h * (0.12 if w < h else 0.08)
        draw.rounded_rectangle([x0, y0, x0 + box_w, y0 + box_h], radius=f.size // 3, fill=(0, 0, 0, 170))
        y = y0 + f.size // 4
        for line in lines:
            tw = draw.textlength(line, font=f)
            draw.text(((w - tw) / 2, y), line, font=f, fill=(255, 221, 0, 255))
            y += line_h
    img.save(out)
    return out
