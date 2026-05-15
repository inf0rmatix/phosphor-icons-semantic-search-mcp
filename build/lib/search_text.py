"""Text composed for embedding (semantic search), separate from display descriptions."""

from __future__ import annotations

from typing import Any


def compose_embed_text(icon: dict[str, Any]) -> str:
    """Combine name, catalog metadata, and description for the vector index."""
    name = icon["name"]
    pascal_name = icon.get("pascalName", "")
    categories = icon.get("categories", [])
    tags = icon.get("tags", [])
    description = icon.get("description", "")

    parts: list[str] = [f"Icon: {name}."]

    if pascal_name:
        parts.append(f"Component: {pascal_name}.")

    if categories:
        parts.append(f"Categories: {', '.join(categories)}.")

    if tags:
        clean_tags = [tag for tag in tags if not tag.startswith("*")]
        if clean_tags:
            parts.append(f"Tags: {', '.join(clean_tags[:15])}.")

    if description:
        parts.append(description.strip())

    return " ".join(parts)
