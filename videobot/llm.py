"""Thin wrapper around the Claude API used by the research and script steps."""

from __future__ import annotations

import json
from typing import Any

import anthropic

from .config import settings

# Server-side refusal fallback: if the main model declines, the API retries on a
# suitable fallback model inside the same call.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

WEB_TOOLS = [
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 10},
    {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 6},
]

_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


class LLMError(RuntimeError):
    pass


def _run(messages: list[dict], **kwargs: Any):
    """Stream a request to completion, resuming server-tool turns that pause."""
    for _ in range(8):
        with client().beta.messages.stream(
            model=settings.model,
            max_tokens=64000,
            betas=[FALLBACK_BETA],
            fallbacks="default",
            messages=messages,
            **kwargs,
        ) as stream:
            msg = stream.get_final_message()
        if msg.stop_reason == "pause_turn":
            # Long web-search turn: send it back so the server continues.
            messages = messages + [{"role": "assistant", "content": msg.content}]
            continue
        break
    if msg.stop_reason == "refusal":
        details = getattr(msg, "stop_details", None)
        raise LLMError(f"Claude declined the request: {getattr(details, 'explanation', '')}")
    if msg.stop_reason == "max_tokens":
        raise LLMError("Response was cut off (max_tokens reached).")
    return msg


def _text(msg) -> str:
    return "".join(b.text for b in msg.content if b.type == "text").strip()


def research(system: str, prompt: str) -> str:
    """Free-form answer that may use web search / web fetch."""
    msg = _run(
        [{"role": "user", "content": prompt}],
        system=system,
        tools=WEB_TOOLS,
        output_config={"effort": "high"},
    )
    return _text(msg)


def structured(system: str, prompt: str, schema: dict, effort: str = "high") -> dict:
    """Answer constrained to a JSON schema, returned as a dict."""
    msg = _run(
        [{"role": "user", "content": prompt}],
        system=system,
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
    )
    try:
        return json.loads(_text(msg))
    except json.JSONDecodeError as exc:
        raise LLMError(f"Could not parse JSON from Claude: {exc}") from exc
