#!/usr/bin/env python3
"""Single-call smoke test (no retries). Exit 0 on success."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from dotenv import load_dotenv

BUILD_DIR = Path(__file__).resolve().parent
ROOT_DIR = BUILD_DIR.parent
sys.path.insert(0, str(BUILD_DIR))

load_dotenv(ROOT_DIR / ".env")

spec = importlib.util.spec_from_file_location(
    "generate_descriptions",
    BUILD_DIR / "01_generate_descriptions.py",
)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def main() -> None:
    batch_size = int(__import__("os").environ.get("OPENROUTER_BATCH_SIZE", "1"))
    render_size = int(__import__("os").environ.get("ICON_RENDER_SIZE", "512"))

    base_url, api_key, model, timeout_seconds = generator.resolve_openrouter_settings()
    catalog = generator.load_catalog()
    batch = catalog[:batch_size]

    client = generator.OpenRouterClient(
        api_key=api_key,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
    )

    try:
        result = generator._request_batch_once(client, model, batch, render_size)
    finally:
        client.close()

    names = [icon["name"] for icon in batch]
    print(f"OK: {len(result)} icons ({', '.join(names)}) with {model} @ {render_size}px")
    print()

    for name in names:
        description = result[name]
        print(f"--- {name} ---")
        print(description)
        print()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
