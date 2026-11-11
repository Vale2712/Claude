"""Glue: ideas -> script -> voice -> visuals -> video, saved under videos/."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from . import editor, visuals, voice
from .config import DEFAULT_VOICES, FORMATS, settings
from .research import find_ideas
from .scriptwriter import script_to_markdown, write_script


def slugify(text: str, max_len: int = 50) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()[:max_len] or "video"


def _history_file() -> Path:
    return settings.output_dir / "history.json"


def load_history() -> list[dict]:
    try:
        return json.loads(_history_file().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _add_history(entry: dict) -> None:
    hist = load_history()
    hist.append(entry)
    _history_file().parent.mkdir(parents=True, exist_ok=True)
    _history_file().write_text(json.dumps(hist, indent=2, ensure_ascii=False), encoding="utf-8")


def _dump(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def ideas(niche: str, count: int, video_format: str, language: str) -> tuple[list[dict], str, Path]:
    avoid = [h["title"] for h in load_history()]
    found, notes = find_ideas(niche, count, video_format, language, avoid)
    folder = settings.output_dir / "_ideas"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{datetime.now():%Y-%m-%d_%H%M%S}_{slugify(niche, 30)}.json"
    _dump(path, {"niche": niche, "format": video_format, "language": language, "ideas": found})
    return found, notes, path


def render(folder: Path, voice_name: str | None = None, music: Path | None = None) -> Path:
    """(Re-)render a video from folder/script.json. Edit the script and re-run to tweak."""
    editor.require_ffmpeg()
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    script = json.loads((folder / "script.json").read_text(encoding="utf-8"))
    fmt = FORMATS[meta["format"]]
    size = tuple(fmt["size"])
    voice_name = voice_name or meta.get("voice") or DEFAULT_VOICES.get(meta["language"], DEFAULT_VOICES["en"])
    assets = folder / "assets"
    assets.mkdir(exist_ok=True)

    clips, scene_words, offsets, t, first_visual = [], [], [], 0.0, None
    for i, scene in enumerate(script["scenes"], 1):
        print(f"  scene {i}/{len(script['scenes'])}: {scene['visual_query']}")
        audio = assets / f"s{i:02d}.mp3"
        words = voice.synthesize(scene["narration"], voice_name, audio)
        visual = visuals.pexels_video(scene["visual_query"], size, fmt["orientation"], assets / f"s{i:02d}_clip.mp4")
        if visual is None:
            # headline already comes from the overlay; only show text if there is none
            visual = visuals.text_card("" if scene["on_screen_text"] else script["title"], size,
                                       assets / f"s{i:02d}_card.png", seed=i)
        overlay = visuals.text_overlay(scene["on_screen_text"], size, assets / f"s{i:02d}_text.png")
        ass = editor.write_ass(words, size, assets / f"s{i:02d}.ass")
        clip = assets / f"s{i:02d}_scene.mp4"
        dur = editor.render_scene(visual, overlay, audio, ass, size, clip)
        clips.append(clip)
        first_visual = first_visual if i > 1 else visual
        scene_words.append(words)
        offsets.append(t)
        t += dur

    out = folder / "video.mp4"
    editor.concat(clips, out, music)
    editor.write_srt(scene_words, offsets, folder / "captions.srt")
    editor.thumbnail(first_visual, script.get("thumbnail_text") or script["title"], size, folder / "thumbnail.jpg")
    meta.update(voice=voice_name, duration_seconds=round(t, 1), rendered_at=datetime.now().isoformat(timespec="seconds"))
    _dump(folder / "meta.json", meta)
    return out


def make(niche: str, videos: int = 1, video_format: str = "short", language: str = "en",
         voice_name: str | None = None, idea: str | None = None, music: Path | None = None,
         script_only: bool = False) -> list[Path]:
    topic = f"{niche} - specifically this idea: {idea}" if idea else niche
    print(f"> Researching ideas on the internet for: {topic}")
    found, notes, ideas_path = ideas(topic, max(videos, 3) if not idea else 1, video_format, language)
    print(f"  saved {len(found)} ideas -> {ideas_path.relative_to(settings.output_dir.parent)}")

    made = []
    for chosen in found[:videos]:
        print(f"> Writing script: {chosen['title']}")
        script = write_script(chosen, video_format, language, notes)
        folder = settings.output_dir / f"{datetime.now():%Y-%m-%d_%H%M}_{slugify(script['title'])}"
        folder.mkdir(parents=True, exist_ok=True)
        _dump(folder / "idea.json", chosen)
        (folder / "research.md").write_text(notes, encoding="utf-8")
        _dump(folder / "script.json", script)
        (folder / "script.md").write_text(script_to_markdown(script), encoding="utf-8")
        _dump(folder / "meta.json", {"niche": niche, "format": video_format, "language": language,
                                     "voice": voice_name, "created_at": datetime.now().isoformat(timespec="seconds")})
        if not script_only:
            print("> Rendering video")
            render(folder, voice_name, music)
        _add_history({"title": script["title"], "idea": chosen["title"], "folder": folder.name,
                      "date": datetime.now().isoformat(timespec="seconds")})
        print(f"  done -> {folder.relative_to(settings.output_dir.parent)}")
        made.append(folder)
    return made
