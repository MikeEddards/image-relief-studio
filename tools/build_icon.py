from __future__ import annotations

from io import BytesIO
from pathlib import Path

import resvg_py
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "app_icon.svg"
OUTPUT_DIR = ROOT / "build_assets"
OUTPUT = OUTPUT_DIR / "app_icon.ico"


def main() -> None:
    svg = SOURCE.read_text(encoding="utf-8")
    png = resvg_py.svg_to_bytes(svg_string=svg, width=512, height=512)
    image = Image.open(BytesIO(png)).convert("RGBA")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    image.save(
        OUTPUT,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"Built icon: {OUTPUT}")


if __name__ == "__main__":
    main()
