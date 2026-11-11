"""Step 5: assemble scenes into the final video with ffmpeg."""

from __future__ import annotations

import shutil
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from .visuals import font

FPS = 30
TAIL = 0.35  # seconds of silence after each scene


def require_ffmpeg() -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("ffmpeg/ffprobe not found. Install ffmpeg first (see README).")


def _run(cmd: list[str], cwd: Path) -> None:
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{' '.join(cmd)}\n{res.stderr[-3000:]}")


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


# ---------- captions ----------

def _chunks(words, size):
    for i in range(0, len(words), size):
        group = words[i:i + size]
        yield group[0][0], group[-1][1], " ".join(w[2] for w in group)


def _ass_time(t: float) -> str:
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_ass(words, size: tuple[int, int], out: Path) -> Path:
    w, h = size
    portrait = h > w
    fs = int(w / 13) if portrait else int(h / 15)
    margin = int(h * (0.22 if portrait else 0.08))
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {w}", f"PlayResY: {h}", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Cap,DejaVu Sans,{fs},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,"
        f"-1,0,0,0,100,100,0,0,1,{max(3, fs // 12)},2,2,60,60,{margin},1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for start, end, text in _chunks(words, 3 if portrait else 7):
        text = text.replace("{", "(").replace("}", ")")
        lines.append(f"Dialogue: 0,{_ass_time(start)},{_ass_time(end + 0.05)},Cap,,0,0,0,,{text}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_srt(scene_words: list[list], scene_offsets: list[float], out: Path) -> Path:
    entries, n = [], 1
    for words, offset in zip(scene_words, scene_offsets):
        for start, end, text in _chunks(words, 8):
            entries.append(f"{n}\n{_srt_time(start + offset)} --> {_srt_time(end + offset)}\n{text}\n")
            n += 1
    out.write_text("\n".join(entries), encoding="utf-8")
    return out


# ---------- rendering ----------

def render_scene(visual: Path, overlay: Path, audio: Path, ass: Path,
                 size: tuple[int, int], out: Path) -> float:
    """Render one scene clip; returns its duration in seconds."""
    w, h = size
    dur = duration(audio) + TAIL
    is_video = visual.suffix.lower() in {".mp4", ".mov", ".webm", ".mkv"}
    if is_video:
        src = ["-stream_loop", "-1", "-i", visual.name]
        bg = f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps={FPS}[bg]"
    else:  # still image -> slow Ken Burns zoom
        src = ["-loop", "1", "-framerate", str(FPS), "-i", visual.name]
        bg = (f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
              f"zoompan=z='min(1+0.0008*on,1.3)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d=1:s={w}x{h}:fps={FPS},setsar=1[bg]")
    graph = f"{bg};[bg][1:v]overlay=0:0[ov];[ov]ass={ass.name}[v];[2:a]apad=pad_dur={TAIL}[a]"
    _run(["ffmpeg", "-y", *src, "-loop", "1", "-i", overlay.name, "-i", audio.name,
          "-filter_complex", graph, "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}",
          "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
          "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k",
          out.name], cwd=out.parent)
    return dur


def concat(clips: list[Path], out: Path, music: Path | None = None) -> Path:
    work = clips[0].parent
    listfile = work / "concat.txt"
    listfile.write_text("".join(f"file '{c.name}'\n" for c in clips), encoding="utf-8")
    joined = work / "joined.mp4"
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile.name, "-c", "copy",
          joined.name], cwd=work)
    if music:
        _run(["ffmpeg", "-y", "-i", str(joined), "-stream_loop", "-1", "-i", str(music.resolve()),
              "-filter_complex",
              "[1:a]volume=0.12[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]",
              "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
              "-movflags", "+faststart", str(out.resolve())], cwd=work)
    else:
        _run(["ffmpeg", "-y", "-i", str(joined), "-c", "copy", "-movflags", "+faststart",
              str(out.resolve())], cwd=work)
    return out


def thumbnail(visual: Path, text: str, size: tuple[int, int], out: Path) -> Path:
    """Thumbnail from the first scene's footage with big, auto-fitted text."""
    frame = out.with_suffix(".frame.png")
    _run(["ffmpeg", "-y", "-ss", "1" if visual.suffix != ".png" else "0", "-i", str(visual.resolve()),
          "-frames:v", "1", str(frame.resolve())], cwd=out.parent)
    img = ImageOps.fit(Image.open(frame).convert("RGB"), size)
    img = ImageEnhance.Brightness(img).enhance(0.6)
    w, h = img.size
    draw = ImageDraw.Draw(img)
    words = text.upper()
    size_px = int(min(w, h) / 5)
    while True:  # shrink until every line fits in 90% of the width
        f = font(size_px)
        lines = textwrap.wrap(words, width=max(4, int(w * 0.9 / (size_px * 0.62))))
        if max(draw.textlength(l, font=f) for l in lines) <= w * 0.9 or size_px < 30:
            break
        size_px = int(size_px * 0.9)
    line_h = int(f.size * 1.15)
    y = (h - line_h * len(lines)) / 2
    for line in lines:
        tw = draw.textlength(line, font=f)
        draw.text(((w - tw) / 2, y), line, font=f, fill=(255, 221, 0),
                  stroke_width=max(3, f.size // 12), stroke_fill="black")
        y += line_h
    img.save(out, quality=92)
    frame.unlink(missing_ok=True)
    return out
