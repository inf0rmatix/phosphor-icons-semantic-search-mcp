#!/usr/bin/env python3
"""Embed descriptions and write data/vector_index.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from sentence_transformers import SentenceTransformer

BUILD_DIR = Path(__file__).resolve().parent
ROOT_DIR = BUILD_DIR.parent
sys.path.insert(0, str(BUILD_DIR))

from lib.search_text import compose_embed_text

DESCRIPTIONS_PATH = BUILD_DIR / "cache" / "descriptions.json"
OUTPUT_PATH = ROOT_DIR / "data" / "vector_index.json"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def main() -> None:
    if not DESCRIPTIONS_PATH.exists():
        print(
            f"Missing {DESCRIPTIONS_PATH}. Run: npm run build:descriptions",
            file=sys.stderr,
        )
        sys.exit(1)

    with DESCRIPTIONS_PATH.open(encoding="utf-8") as file:
        cache = json.load(file)

    icons_map: dict[str, Any] = cache.get("icons", cache)

    if not icons_map:
        print("No icons in descriptions cache.", file=sys.stderr)
        sys.exit(1)

    names = sorted(icons_map.keys())
    print(f"Embedding {len(names)} icons with {MODEL_NAME}...", file=sys.stderr)

    model = SentenceTransformer(MODEL_NAME)
    entries: list[dict[str, Any]] = []

    embed_inputs = [compose_embed_text(icons_map[name]) for name in names]
    vectors = model.encode(
        embed_inputs,
        normalize_embeddings=True,
        show_progress_bar=True,
        batch_size=64,
    )

    for index, name in enumerate(names):
        icon = icons_map[name]
        vector = vectors[index].tolist()
        search_text = embed_inputs[index]
        entries.append(
            {
                "name": name,
                "pascalName": icon.get("pascalName", ""),
                "description": icon["description"],
                "searchText": search_text,
                "vector": vector,
                "svg": icon["svg"],
                "categories": icon.get("categories", []),
                "tags": icon.get("tags", []),
            }
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(entries, file, ensure_ascii=False)

    print(f"Wrote {OUTPUT_PATH} ({len(entries)} icons)", file=sys.stderr)


if __name__ == "__main__":
    main()
