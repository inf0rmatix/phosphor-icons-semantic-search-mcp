"""Text composed for embedding (semantic search), separate from display descriptions."""

from __future__ import annotations

from typing import Any

from lib.embed_format import format_passage_text, format_query_text

SECTION_LABELS: tuple[tuple[str, str], ...] = (
    ("visual", "Visual:"),
    ("concept", "Concept:"),
    ("primary_use", "Primary use:"),
    ("search_phrases", "Search phrases:"),
    ("avoid_matching", "Avoid matching:"),
)


def parse_description_sections(description: str) -> dict[str, str]:
    """Extract labeled sections from a hybrid description string."""
    if not description or not description.strip():
        return {}

    normalized = description.strip()
    lower = normalized.lower()
    sections: dict[str, str] = {}
    markers: list[tuple[int, str, str]] = []

    for key, label in SECTION_LABELS:
        index = lower.find(label.lower())

        if index >= 0:
            markers.append((index, key, label))

    markers.sort(key=lambda item: item[0])

    for marker_index, (start, key, label) in enumerate(markers):
        content_start = start + len(label)
        content_end = markers[marker_index + 1][0] if marker_index + 1 < len(markers) else len(normalized)
        value = normalized[content_start:content_end].strip()

        if value:
            sections[key] = value

    return sections


def _clean_phrase(phrase: str) -> str:
    return phrase.strip().rstrip(".").strip()


def _clean_tag_list(tags: list[Any]) -> list[str]:
    clean: list[str] = []

    for tag in tags:
        text = str(tag).strip()

        if not text or text.startswith("*"):
            continue

        clean.append(text)

    return clean[:15]


def compose_embed_text(icon: dict[str, Any]) -> str:
    """
    Retrieval-focused passage for the vector index.

    Uses only fields that match how developers search (role + phrases + catalog).
    Visual/Concept stay in `description` for tool output but are omitted here
    so they do not drown out action/domain signal in the embedding.
    """
    name = icon["name"]
    pascal_name = icon.get("pascalName", "")
    categories = icon.get("categories", [])
    tags = icon.get("tags", [])
    description = icon.get("description", "")
    sections = parse_description_sections(description)

    body_parts: list[str] = [f"Phosphor icon {name}."]

    if pascal_name:
        body_parts.append(f"React component {pascal_name}.")

    primary_use = sections.get("primary_use", "")

    if primary_use:
        body_parts.append(f"UI role: {_clean_phrase(primary_use)}.")

    search_phrases = sections.get("search_phrases", "")

    if search_phrases:
        body_parts.append(f"Search terms: {search_phrases}.")

    avoid_matching = sections.get("avoid_matching", "")

    if avoid_matching and avoid_matching.strip().lower() not in {"none", "n/a"}:
        body_parts.append(f"Does not match: {avoid_matching}.")

    clean_tags = _clean_tag_list(list(tags or []))

    if clean_tags:
        body_parts.append(f"Tags: {', '.join(clean_tags)}.")

    if categories:
        body_parts.append(f"Categories: {', '.join(categories)}.")

    concept = sections.get("concept", "")

    if concept and not primary_use and not search_phrases:
        body_parts.append(f"Meaning: {_clean_phrase(concept)}.")

    if len(body_parts) == 1 and description:
        body_parts.append(description.strip())

    return format_passage_text(" ".join(body_parts))


def format_query_for_embedding(query: str) -> str:
    return format_query_text(query)
