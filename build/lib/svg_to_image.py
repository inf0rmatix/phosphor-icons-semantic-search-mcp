"""Rasterize Phosphor SVG assets to PNG for vision LLM prompts."""

from __future__ import annotations

import base64
from pathlib import Path

import cairosvg

DEFAULT_RENDER_SIZE = 128


def svg_path_to_png_data_url(svg_path: Path, size: int = DEFAULT_RENDER_SIZE) -> str:
    png_bytes = cairosvg.svg2png(
        url=str(svg_path),
        output_width=size,
        output_height=size,
    )
    encoded = base64.standard_b64encode(png_bytes).decode("ascii")

    return f"data:image/png;base64,{encoded}"
