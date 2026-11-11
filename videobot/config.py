"""Settings, loaded from environment variables and an optional .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (KEY=VALUE lines); real env vars take precedence."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value:
            os.environ.setdefault(key.strip(), value)


_load_dotenv(REPO_ROOT / ".env")

# Default narrator voice per language (Microsoft Edge neural voices, free).
DEFAULT_VOICES = {
    "en": "en-US-AndrewMultilingualNeural",
    "de": "de-DE-ConradNeural",
    "it": "it-IT-DiegoNeural",
    "es": "es-ES-AlvaroNeural",
    "fr": "fr-FR-HenriNeural",
    "pt": "pt-BR-AntonioNeural",
}

# Video formats: (width, height, target spoken length, scene count hint)
FORMATS = {
    "short": {"size": (1080, 1920), "words": "120-150", "scenes": "6-9", "orientation": "portrait"},
    "long": {"size": (1920, 1080), "words": "900-1200", "scenes": "18-30", "orientation": "landscape"},
}


@dataclass
class Settings:
    model: str = os.environ.get("VIDEOBOT_MODEL", "claude-opus-5-5")
    pexels_api_key: str | None = os.environ.get("PEXELS_API_KEY") or None
    output_dir: Path = REPO_ROOT / os.environ.get("VIDEOBOT_OUTPUT_DIR", "videos")


settings = Settings()
