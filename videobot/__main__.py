"""Command line interface:  python -m videobot <command> ..."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import FORMATS


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="videobot", description="Find trending video ideas and turn them into finished videos.")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--niche", required=True, help='Channel topic, e.g. "space facts" or "personal finance tips"')
        sp.add_argument("--format", choices=list(FORMATS), default="short", help="short = 9:16 <60s, long = 16:9 5-8 min")
        sp.add_argument("--language", default="en", help="Script language code (en, de, it, es, fr, pt, ...)")

    sp = sub.add_parser("ideas", help="Only research and list new video ideas")
    common(sp)
    sp.add_argument("--count", type=int, default=5)

    sp = sub.add_parser("make", help="Research ideas, write scripts and render videos")
    common(sp)
    sp.add_argument("--videos", type=int, default=1, help="How many videos to make")
    sp.add_argument("--idea", help="Use your own idea instead of picking the top trending one")
    sp.add_argument("--voice", help="edge-tts voice, e.g. en-US-AndrewMultilingualNeural (list: edge-tts --list-voices)")
    sp.add_argument("--music", type=Path, help="Optional background music file (mp3)")
    sp.add_argument("--script-only", action="store_true", help="Write the script but do not render")

    sp = sub.add_parser("render", help="Re-render a video folder from its (edited) script.json")
    sp.add_argument("folder", type=Path)
    sp.add_argument("--voice")
    sp.add_argument("--music", type=Path)

    args = p.parse_args(argv)
    from . import pipeline  # imported late so --help works without dependencies

    if args.cmd == "ideas":
        found, _, path = pipeline.ideas(args.niche, args.count, args.format, args.language)
        for i, idea in enumerate(found, 1):
            print(f"\n{i}. [{idea['score']}/10] {idea['title']}\n   {idea['angle']}\n   Why now: {idea['why_now']}")
        print(f"\nSaved to {path}")
    elif args.cmd == "make":
        pipeline.make(args.niche, args.videos, args.format, args.language, args.voice,
                      args.idea, args.music, args.script_only)
    elif args.cmd == "render":
        print(f"Rendered: {pipeline.render(args.folder, args.voice, args.music)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
