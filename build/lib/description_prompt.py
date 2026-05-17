"""Vision LLM prompt helpers for search-optimized icon descriptions."""

from __future__ import annotations

from typing import Any


def build_description_instructions(batch: list[dict[str, Any]]) -> str:
    icon_names = [icon["name"] for icon in batch]
    metadata_lines: list[str] = []

    for icon in batch:
        categories = ", ".join(icon.get("categories", [])) or "none"
        tags = ", ".join(icon.get("tags", [])[:10]) or "none"
        metadata_lines.append(
            f"- {icon['name']} (pascal: {icon['pascalName']}): "
            f"categories=[{categories}]; tags=[{tags}]"
        )

    return f"""You write icon metadata for semantic search (vector retrieval). AI agents will search with natural language (e.g. "add new task to list", "account settings button").

You will receive {len(batch)} icon images in order, each after its label line.
Icons in this batch: {", ".join(icon_names)}

Catalog metadata:
{chr(10).join(metadata_lines)}

IMPORTANT — this batch may contain similar-looking icons. For each icon, write Search phrases and Avoid matching so it wins the right queries and loses the wrong ones vs other icons in this batch.

For EACH icon, return one "description" string with exactly these labeled parts (one paragraph):

Visual: Brief glyph description from the image (1 sentence).

Concept: Action + domain in 1-2 sentences. State what this icon is NOT for when a neighbor icon could be confused (e.g. "for marking tasks done, not for adding new tasks").

Primary use: One specific UI role phrase with an action verb when clickable. Write how a developer describes the button (e.g. "add item to task list", "open account settings", "log in", "browse recipes section") — not generic labels like "task icon" or "recipe action".

Search phrases: 10-16 comma-separated phrases developers actually type. Include full intent phrases (e.g. "add new task to list", "create recipe button", "account management settings"), not only single words. Include: verbs, UI patterns (icon button, fab, toolbar, nav), synonyms, and relevant catalog tags.

Avoid matching: 3-8 comma-separated full query phrases this icon must lose to sibling icons (same batch or common confusions). Examples: list-checks → "add task, create new item, plus button"; cooking-pot → "create new recipe, add recipe button"; sign-in → "account settings, profile settings". Use "none" only if truly unique.

Quality rules:
- Differentiate icons that share words (list, user, plus, check) by action and query phrases.
- Plus/list-plus icons: search phrases must include add/create/new/plus; avoid matching completed/done checklist queries.
- Checkmark list icons: search phrases emphasize completed/done; avoid matching add/create/new task queries.
- Food icons: domain/browse intent; avoid matching create/add recipe button queries.
- user-gear / user-circle-gear: account/profile settings; avoid login/logout/switch account queries.
- sign-in / sign-out: auth only; avoid account settings / profile management queries.
- Do not repeat the icon name as the only search phrase.

Return JSON:
{{
  "icons": [
    {{
      "name": "kebab-case-name",
      "description": "Visual: ... Concept: ... Primary use: ... Search phrases: ... Avoid matching: ..."
    }}
  ]
}}

Same order as images. Do not skip icons."""


def description_has_search_format(description: str) -> bool:
    normalized = description.lower()
    return (
        "search phrases:" in normalized
        and "primary use:" in normalized
        and "avoid matching:" in normalized
        and "visual:" in normalized
        and "concept:" in normalized
    )
