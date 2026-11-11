# VideoBot – trending ideas → original script → finished video

VideoBot searches the internet for fresh video ideas in your niche, writes an **original
script** for the best one, and renders a finished video with voice-over, stock footage,
captions and a thumbnail. Everything it makes is saved in the [`videos/`](videos/) folder of
this repository.

```
 web research (Claude + web search)
        │  trending topics, facts, sources
        ▼
 idea ranking ──► original script (scenes, hook, CTA, title, tags)
                         │
        ┌────────────────┼──────────────────┐
        ▼                ▼                  ▼
  voice-over        stock footage      on-screen text
  (edge-tts)        (Pexels)           + word captions
        └────────────────┼──────────────────┘
                         ▼
               ffmpeg ──► videos/<date>_<title>/video.mp4
```

## Setup

1. Install **Python 3.10+** and **ffmpeg** (`sudo apt install ffmpeg`, `brew install ffmpeg`, or `winget install ffmpeg`).
2. Install the Python packages:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in your keys:
   - `ANTHROPIC_API_KEY` – required (research + scriptwriting with Claude).
   - `PEXELS_API_KEY` – optional, free at <https://www.pexels.com/api/>. Without it, scenes use animated text cards instead of real footage.

## Usage

Make one YouTube Short / TikTok / Reel about the most promising trending idea:

```bash
python -m videobot make --niche "space facts"
```

Only look for ideas (no video):

```bash
python -m videobot ideas --niche "personal finance for students" --count 8
```

More options:

```bash
python -m videobot make --niche "AI news" --videos 3 --format long --language de --music music.mp3
```

| Option | Meaning |
|---|---|
| `--format short` / `long` | 9:16 vertical under 60 s (default) or 16:9, 5–8 minutes |
| `--language` | Script and voice language (`en`, `de`, `it`, `es`, `fr`, `pt`, …) |
| `--videos N` | Make N videos from the N best ideas |
| `--idea "..."` | Research and make a video about your own idea |
| `--voice` | Any edge-tts voice (`edge-tts --list-voices`) |
| `--music file.mp3` | Quiet background music |
| `--script-only` | Write the script but don't render it |

### Edit a script and re-render

Every video folder contains `script.json`. Change the narration, on-screen text or the
`visual_query` (stock-footage search words) and render again:

```bash
python -m videobot render videos/2026-11-11_1243_why-the-moon-is-drifting-away
```

## Output: the `videos/` folder

```
videos/
├── history.json                  # every video made (used to avoid repeating topics)
├── _ideas/                       # every idea list the research step produced
└── 2026-11-11_1243_<title>/
    ├── video.mp4                 # the finished video
    ├── thumbnail.jpg
    ├── captions.srt              # upload these as subtitles
    ├── script.md / script.json   # the script (readable / editable)
    ├── idea.json                 # chosen idea, facts and source links
    ├── research.md               # full web research notes
    ├── meta.json
    └── assets/                   # intermediate files (ignored by git)
```

Videos can be large. If you commit many of them, consider [Git LFS](https://git-lfs.com/)
(`git lfs track "videos/**/*.mp4"`), or add `videos/*/video.mp4` to `.gitignore`.

## Run it automatically

Add a cron job (Linux/macOS) to make a new video every day at 09:00:

```bash
0 9 * * * cd /path/to/repo && python -m videobot make --niche "space facts" >> videobot.log 2>&1
```

## Notes

- The model is `claude-opus-5-5` (change with `VIDEOBOT_MODEL` in `.env`). Each video costs a few research and writing calls.
- Scripts are written in the bot's own words and only use facts found during research, but check facts before publishing.
- Pexels footage is free to use; music you add must be licensed for your platform.
