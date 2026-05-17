#!/usr/bin/env python3
"""Generate hybrid icon descriptions via OpenRouter vision (resume-safe, parallel)."""

from __future__ import annotations

import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BUILD_DIR = Path(__file__).resolve().parent
ROOT_DIR = BUILD_DIR.parent
sys.path.insert(0, str(BUILD_DIR))

from lib.description_prompt import (
    build_icon_instruction,
    build_static_instruction_block,
    build_system_message,
    description_has_search_format,
)
from lib.prompt_caching import prompt_caching_enabled
from lib.description_quality import (
    description_degeneration_reason,
    is_repeated_token_degeneration,
)
from lib.openrouter_client import (
    DEFAULT_BASE_URL,
    OpenRouterApiError,
    OpenRouterClient,
)
from lib.openrouter_schema import icons_response_format, response_healing_plugins
from lib.svg_to_image import svg_path_to_png_data_url

CACHE_DIR = BUILD_DIR / "cache"
CATALOG_PATH = CACHE_DIR / "catalog.json"
DESCRIPTIONS_PATH = CACHE_DIR / "descriptions.json"
CORE_ASSETS = ROOT_DIR / "node_modules" / "@phosphor-icons" / "core" / "assets" / "regular"
DEFAULT_MODEL = "google/gemini-2.5-flash-lite"
DEFAULT_BATCH_SIZE = 1
DEFAULT_CONCURRENCY = 8
DEFAULT_MAX_TOKENS_PER_ICON = 1800
DESCRIPTION_MODE = "vision"
CACHE_VERSION = 11


def load_catalog() -> list[dict[str, Any]]:
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(
            f"Missing {CATALOG_PATH}. Run: npm run export-catalog"
        )

    with CATALOG_PATH.open(encoding="utf-8") as file:
        catalog = json.load(file)

    if not isinstance(catalog, list):
        raise ValueError("catalog.json must be a JSON array.")

    return catalog


def load_descriptions_cache() -> dict[str, Any]:
    if not DESCRIPTIONS_PATH.exists():
        return {
            "meta": {
                "model": os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL),
                "version": CACHE_VERSION,
                "descriptionMode": DESCRIPTION_MODE,
            },
            "icons": {},
        }

    with DESCRIPTIONS_PATH.open(encoding="utf-8") as file:
        data = json.load(file)

    if "icons" not in data:
        data = {
            "meta": {
                "model": DEFAULT_MODEL,
                "version": CACHE_VERSION,
                "descriptionMode": DESCRIPTION_MODE,
            },
            "icons": data,
        }

    data.setdefault("meta", {})
    data.setdefault("icons", {})
    return data


def save_descriptions_cache(data: dict[str, Any]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with DESCRIPTIONS_PATH.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def svg_path_for_icon(icon_name: str) -> Path:
    svg_path = CORE_ASSETS / f"{icon_name}.svg"

    if not svg_path.exists():
        raise FileNotFoundError(f"Missing SVG: {svg_path}")

    return svg_path


def read_svg(icon_name: str) -> str:
    return svg_path_for_icon(icon_name).read_text(encoding="utf-8")


def icon_is_cached(cache: dict[str, Any], icon_name: str, model: str) -> bool:
    if icon_name not in cache["icons"]:
        return False

    icon = cache["icons"][icon_name]
    description = icon.get("description", "")

    if not isinstance(description, str) or not description_has_search_format(description):
        return False

    return icon.get("descriptionVersion") == CACHE_VERSION and icon.get("model") == model


def build_vision_messages(
    batch: list[dict[str, Any]],
    render_size: int,
) -> list[dict[str, Any]]:
    if len(batch) != 1:
        raise ValueError(
            f"Expected one icon per request (got {len(batch)}). Set OPENROUTER_BATCH_SIZE=1."
        )

    icon = batch[0]
    name = icon["name"]
    use_cache = prompt_caching_enabled()

    content: list[dict[str, Any]] = [
        build_static_instruction_block(use_cache=use_cache),
        {"type": "text", "text": build_icon_instruction(icon)},
        {"type": "text", "text": f"Icon image for: {name}"},
        {
            "type": "image_url",
            "image_url": {
                "url": svg_path_to_png_data_url(
                    svg_path_for_icon(name),
                    size=render_size,
                ),
                "detail": "low",
            },
        },
    ]

    return [
        build_system_message(use_cache=use_cache),
        {"role": "user", "content": content},
    ]


def validation_error_is_repeated_token(error: Exception) -> bool:
    return isinstance(error, ValueError) and "repeated token" in str(error).lower()


def validate_batch_response(
    response: dict[str, Any],
    expected_names: set[str],
    *,
    skip_degeneration: bool = False,
) -> dict[str, str]:
    icons = response.get("icons")

    if not isinstance(icons, list):
        raise ValueError("Response must contain an 'icons' array.")

    descriptions: dict[str, str] = {}

    for entry in icons:
        if not isinstance(entry, dict):
            continue

        name = entry.get("name")
        description = entry.get("description")

        if not isinstance(name, str) or not isinstance(description, str):
            continue

        description = description.strip()
        invalid: list[str] = []

        if not description_has_search_format(description):
            invalid.append("missing required sections")

        degenerate_reason = description_degeneration_reason(description)

        if degenerate_reason and not (
            skip_degeneration and is_repeated_token_degeneration(degenerate_reason)
        ):
            invalid.append(degenerate_reason)

        descriptions[name] = description

        if invalid:
            raise ValueError(f"Invalid description for {name}: {', '.join(invalid)}")

    missing = expected_names - set(descriptions.keys())

    if missing:
        raise ValueError(f"Response missing icons: {sorted(missing)[:5]}...")

    return descriptions


def request_batch_with_retry(
    client: OpenRouterClient,
    model: str,
    batch: list[dict[str, Any]],
    render_size: int,
) -> dict[str, str]:
    try:
        return _request_batch_once(client, model, batch, render_size)
    except (OpenRouterApiError, ValueError) as error:
        if len(batch) <= 1:
            raise

        midpoint = len(batch) // 2
        print(
            f"  Splitting batch of {len(batch)} after error: {error}",
            file=sys.stderr,
        )

        first_half = _request_batch_once(client, model, batch[:midpoint], render_size)
        second_half = _request_batch_once(client, model, batch[midpoint:], render_size)

        return {**first_half, **second_half}


def resolve_max_tokens(batch_size: int) -> int:
    override = os.environ.get("OPENROUTER_MAX_TOKENS", "").strip()

    if override:
        return max(256, int(override))

    return DEFAULT_MAX_TOKENS_PER_ICON * batch_size


def resolve_response_format(batch_size: int) -> dict[str, Any] | None:
    structured_enabled = os.environ.get("OPENROUTER_STRUCTURED_OUTPUT", "1").strip().lower() not in {
        "0",
        "false",
        "no",
    }

    if not structured_enabled:
        return None

    use_schema = os.environ.get("OPENROUTER_JSON_SCHEMA", "1").strip().lower() not in {
        "0",
        "false",
        "no",
    }

    if use_schema:
        return icons_response_format(batch_size)

    return {"type": "json_object"}


def resolve_plugins() -> list[dict[str, str]] | None:
    healing_enabled = os.environ.get("OPENROUTER_RESPONSE_HEALING", "1").strip().lower() not in {
        "0",
        "false",
        "no",
    }

    if not healing_enabled:
        return None

    return response_healing_plugins()


def _request_batch_once(
    client: OpenRouterClient,
    model: str,
    batch: list[dict[str, Any]],
    render_size: int,
) -> dict[str, str]:
    expected_names = {icon["name"] for icon in batch}
    messages = build_vision_messages(batch, render_size)
    max_tokens = resolve_max_tokens(len(batch))
    plugins = resolve_plugins()

    format_attempts: list[dict[str, Any] | None] = [resolve_response_format(len(batch))]

    if format_attempts[0] is not None and format_attempts[0].get("type") == "json_schema":
        format_attempts.append({"type": "json_object"})

    last_error: Exception | None = None

    for accept_repeated_tokens in (False, True):
        for response_format in format_attempts:
            try:
                response = client.create_chat_completion_json(
                    model=model,
                    messages=messages,
                    response_format=response_format,
                    temperature=0.0,
                    max_tokens=max_tokens,
                    plugins=plugins,
                )
                return validate_batch_response(
                    response,
                    expected_names,
                    skip_degeneration=accept_repeated_tokens,
                )
            except (OpenRouterApiError, ValueError) as error:
                last_error = error

                if not accept_repeated_tokens and validation_error_is_repeated_token(error):
                    break

                if response_format is format_attempts[-1]:
                    break

                label = (
                    "none"
                    if response_format is None
                    else response_format.get("type", "custom")
                )
                print(
                    f"  Falling back from response_format={label} ({error})",
                    file=sys.stderr,
                )

        if accept_repeated_tokens:
            break

        if last_error is not None and validation_error_is_repeated_token(last_error):
            icon_names = ", ".join(icon["name"] for icon in batch)
            print(
                f"  Retrying once after repeated-token repetition ({icon_names})...",
                file=sys.stderr,
            )
            continue

        break

    if last_error is not None:
        raise last_error

    raise RuntimeError("Unreachable")


def generate_offline_description(icon: dict[str, Any]) -> str:
    name = icon["name"]
    tags_list = [tag for tag in icon.get("tags", []) if not str(tag).startswith("*")]
    tags = ", ".join(tags_list[:12]) or "interface, ui"
    categories = ", ".join(icon.get("categories", [])) or "interface"
    name_words = name.replace("-", " ")

    return (
        f"Visual: Phosphor icon glyph {name}. "
        f"Concept: {categories} icon for {name_words}. "
        f"Primary use: {name_words} control in the interface. "
        f"Search phrases: {name}, {name_words}, {tags}, {categories}, icon button. "
        f"Avoid matching: none."
    )


def generate_offline_batch(batch: list[dict[str, Any]]) -> dict[str, str]:
    return {icon["name"]: generate_offline_description(icon) for icon in batch}


def merge_batch_into_cache(
    cache: dict[str, Any],
    batch: list[dict[str, Any]],
    descriptions: dict[str, str],
    cache_lock: threading.Lock,
    model: str,
) -> None:
    with cache_lock:
        for icon in batch:
            name = icon["name"]
            cache["icons"][name] = {
                "name": name,
                "pascalName": icon["pascalName"],
                "description": descriptions[name],
                "svg": read_svg(name),
                "categories": icon.get("categories", []),
                "tags": icon.get("tags", []),
                "descriptionVersion": CACHE_VERSION,
                "model": model,
            }

        cache["meta"]["model"] = model
        cache["meta"]["descriptionMode"] = DESCRIPTION_MODE
        cache["meta"]["version"] = CACHE_VERSION
        save_descriptions_cache(cache)


def process_batch(
    *,
    client: OpenRouterClient | None,
    model: str,
    batch: list[dict[str, Any]],
    render_size: int,
    cache: dict[str, Any],
    cache_lock: threading.Lock,
    use_offline: bool,
) -> int:
    if use_offline:
        descriptions = generate_offline_batch(batch)
    elif client is None:
        raise RuntimeError("OpenRouter client is required when not in offline mode.")
    else:
        descriptions = request_batch_with_retry(client, model, batch, render_size)

    merge_batch_into_cache(cache, batch, descriptions, cache_lock, model)
    return len(batch)


def chunk_batches(
    pending: list[dict[str, Any]],
    batch_size: int,
) -> list[list[dict[str, Any]]]:
    return [
        pending[start : start + batch_size]
        for start in range(0, len(pending), batch_size)
    ]


def resolve_openrouter_settings() -> tuple[str, str, str, float]:
    """Return (base_url, api_key, model, timeout_seconds)."""
    base_url = os.environ.get("OPENROUTER_BASE_URL", "").strip() or DEFAULT_BASE_URL
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    model = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL).strip()
    timeout_seconds = float(os.environ.get("OPENROUTER_TIMEOUT_SECONDS", "120"))

    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is required.")

    return base_url, api_key, model, timeout_seconds


def main() -> None:
    load_dotenv(ROOT_DIR / ".env")

    use_offline = os.environ.get("USE_OFFLINE_DESCRIPTIONS", "").strip() in {
        "1",
        "true",
        "yes",
    }

    try:
        base_url, api_key, model, timeout_seconds = resolve_openrouter_settings()
    except ValueError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)

    batch_size = int(os.environ.get("OPENROUTER_BATCH_SIZE", DEFAULT_BATCH_SIZE))
    concurrency = int(os.environ.get("OPENROUTER_CONCURRENCY", DEFAULT_CONCURRENCY))
    render_size = int(os.environ.get("ICON_RENDER_SIZE", "512"))

    catalog = load_catalog()
    cache = load_descriptions_cache()

    pending = [
        icon for icon in catalog if not icon_is_cached(cache, icon["name"], model)
    ]

    if not pending:
        print(f"All {len(catalog)} icons already described.", file=sys.stderr)
        return

    batches = chunk_batches(pending, batch_size)
    mode_label = "offline" if use_offline else "vision"
    workers = 1 if use_offline else max(1, concurrency)

    if batch_size != 1:
        print(
            f"Warning: OPENROUTER_BATCH_SIZE={batch_size}; one icon per request is recommended.",
            file=sys.stderr,
        )

    caching_label = "on" if prompt_caching_enabled() else "off"

    print(
        f"Generating descriptions ({mode_label}) for {len(pending)} / {len(catalog)} icons "
        f"(model={model}, icons_per_request={batch_size}, concurrency={workers}, "
        f"prompt_cache={caching_label})...",
        file=sys.stderr,
    )

    cache_lock = threading.Lock()
    client = (
        OpenRouterClient(
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )
        if not use_offline
        else None
    )
    completed = 0
    failures = 0

    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(
                    process_batch,
                    client=client,
                    model=model,
                    batch=batch,
                    render_size=render_size,
                    cache=cache,
                    cache_lock=cache_lock,
                    use_offline=use_offline,
                )
                for batch in batches
            ]

            for future in as_completed(futures):
                try:
                    batch_count = future.result()
                    completed += batch_count
                    print(f"  {completed}/{len(pending)}", file=sys.stderr)
                except Exception as error:
                    failures += 1
                    print(f"Batch failed: {error}", file=sys.stderr)
    finally:
        if client is not None:
            client.close()

    if failures > 0:
        print(
            f"Finished with {failures} failed batch(es). Re-run to retry pending icons.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Wrote {DESCRIPTIONS_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
