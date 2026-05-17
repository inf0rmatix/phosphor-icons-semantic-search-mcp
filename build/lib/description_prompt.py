"""Vision LLM prompt helpers for search-optimized icon descriptions."""

from __future__ import annotations

from typing import Any

STATIC_INSTRUCTIONS = """Describe one Phosphor icon for semantic search.

Return JSON:
{"icons":[{"name":"<kebab-name>","description":"<one paragraph>"}]}

Each description must include these labels:
Visual: (one sentence)
Concept: (one sentence; say "not for X" if a similar icon could be confused)
Primary use: (one short phrase, verb + object)
Search phrases: (8-10 comma-separated terms and full queries)
Avoid matching: (queries this icon should rank below others for, or "none")

Hints: plus → add/create; check → done; gear → settings; user+gear → account settings; user+switch → change account; sign-in/out → auth; object glyphs → browse/open section; trash → delete."""


def build_static_instruction_block(*, use_cache: bool) -> dict[str, Any]:
    block: dict[str, Any] = {
        "type": "text",
        "text": STATIC_INSTRUCTIONS,
    }

    if use_cache:
        block["cache_control"] = {"type": "ephemeral"}

    return block


def build_icon_instruction(icon: dict[str, Any]) -> str:
    categories = ", ".join(icon.get("categories", [])) or "none"
    tags = ", ".join(icon.get("tags", [])[:8]) or "none"

    return (
        f"Icon: {icon['name']}\n"
        f"tags={tags}; categories={categories}\n"
        f"The next image is this icon."
    )


def build_system_message(*, use_cache: bool) -> dict[str, Any]:
    text = (
        "Return JSON only. Keep every label: Visual, Concept, Primary use, "
        "Search phrases, Avoid matching."
    )

    if not use_cache:
        return {"role": "system", "content": text}

    return {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": text,
                "cache_control": {"type": "ephemeral"},
            }
        ],
    }


def description_has_search_format(description: str) -> bool:
    normalized = description.lower()
    return (
        "search phrases:" in normalized
        and "primary use:" in normalized
        and "avoid matching:" in normalized
        and "visual:" in normalized
        and "concept:" in normalized
    )
