"""OpenRouter / Gemini prompt caching helpers."""

from __future__ import annotations

import os


def prompt_caching_enabled() -> bool:
    return os.environ.get("OPENROUTER_PROMPT_CACHING", "1").strip().lower() not in {
        "0",
        "false",
        "no",
    }
