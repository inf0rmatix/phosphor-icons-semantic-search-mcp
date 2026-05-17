"""OpenRouter structured output schemas (see openrouter.ai/docs/guides/features/structured-outputs)."""

from __future__ import annotations

from typing import Any


def icons_response_format(batch_size: int) -> dict[str, Any]:
    """Strict json_schema so the model returns exactly batch_size icon entries."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "icon_descriptions",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "icons": {
                        "type": "array",
                        "description": f"Exactly {batch_size} icons in image order.",
                        "minItems": batch_size,
                        "maxItems": batch_size,
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Kebab-case icon id from the prompt.",
                                },
                                "description": {
                                    "type": "string",
                                    "description": (
                                        "One paragraph with labels Visual:, Concept:, "
                                        "Primary use:, Search phrases:, Avoid matching:"
                                    ),
                                },
                            },
                            "required": ["name", "description"],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["icons"],
                "additionalProperties": False,
            },
        },
    }


def response_healing_plugins() -> list[dict[str, str]]:
    """Repairs markdown-wrapped or slightly malformed JSON (OpenRouter plugin)."""
    return [{"id": "response-healing"}]
