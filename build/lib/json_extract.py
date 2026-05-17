"""Extract and parse icon-batch JSON from model text."""

from __future__ import annotations

import json
import re


def parse_icons_payload(text: str) -> dict | None:
    """Parse {\"icons\": [...]} from raw assistant content."""
    candidates = [text.strip()]

    fence_match = re.search(r"```(?:json)?\s*(\{.*)", text, re.DOTALL)
    if fence_match:
        candidates.append(fence_match.group(1).strip())

    for start_needle in ('{"icons"', '{\n  "icons"', '{\n    "icons"'):
        start = text.find(start_needle)
        if start >= 0:
            candidates.append(text[start:].strip())

    for candidate in candidates:
        if not candidate:
            continue

        for variant in (candidate, _close_truncated_json(candidate)):
            if not variant:
                continue

            extracted = _extract_balanced_object(variant, variant.find("{"))
            if extracted:
                try:
                    decoded = json.loads(extracted)
                except json.JSONDecodeError:
                    continue

                if isinstance(decoded, dict) and isinstance(decoded.get("icons"), list):
                    return decoded

    return None


def _close_truncated_json(text: str) -> str:
    start = text.find("{")
    if start < 0:
        return ""

    fragment = text[start:]
    in_string = False
    escape = False
    brace_depth = 0
    bracket_depth = 0

    for character in fragment:
        if in_string:
            if escape:
                escape = False
            elif character == "\\":
                escape = True
            elif character == '"':
                in_string = False
            continue

        if character == '"':
            in_string = True
        elif character == "{":
            brace_depth += 1
        elif character == "}":
            brace_depth -= 1
        elif character == "[":
            bracket_depth += 1
        elif character == "]":
            bracket_depth -= 1

    if not in_string and brace_depth == 0 and bracket_depth == 0:
        return fragment

    closed = fragment
    if in_string:
        closed += '"'

    closed += "]" * max(0, bracket_depth)
    closed += "}" * max(0, brace_depth)

    return closed


def _extract_balanced_object(text: str, start: int) -> str:
    if start < 0:
        return ""

    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(text)):
        character = text[index]

        if in_string:
            if escape:
                escape = False
            elif character == "\\":
                escape = True
            elif character == '"':
                in_string = False

            continue

        if character == '"':
            in_string = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1

            if depth == 0:
                return text[start : index + 1]

    return ""
