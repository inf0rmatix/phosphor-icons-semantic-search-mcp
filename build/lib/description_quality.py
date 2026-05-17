"""Validation helpers for generated icon descriptions."""

from __future__ import annotations

import re
from collections import Counter

MAX_DESCRIPTION_CHARACTERS = 2200


def description_degeneration_reason(description: str) -> str | None:
    if len(description) > MAX_DESCRIPTION_CHARACTERS:
        return f"description exceeds {MAX_DESCRIPTION_CHARACTERS} characters"

    lowered = description.lower()

    for needle in ("control-tower-icon", "browse/section pattern"):
        if lowered.count(needle) >= 4:
            return f"repeated fragment ({needle!r})"

    tokens = re.findall(r"[a-z0-9][a-z0-9-]{8,}", lowered)
    if tokens:
        phrase, count = Counter(tokens).most_common(1)[0]

        if count >= 5:
            return f"repeated token {phrase!r} ({count} times)"

    search_section = lowered.split("search phrases:", 1)
    if len(search_section) == 2:
        phrases = [part.strip() for part in search_section[1].split("avoid matching:")[0].split(",")]
        normalized_phrases = [phrase for phrase in phrases if len(phrase) > 6]

        if normalized_phrases:
            phrase, count = Counter(normalized_phrases).most_common(1)[0]

            if count >= 3:
                return f"repeated search phrase {phrase!r}"

    return None


def is_repeated_token_degeneration(reason: str) -> bool:
    return reason.startswith("repeated token ")
