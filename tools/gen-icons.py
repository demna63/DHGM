#!/usr/bin/env python3
"""DHGM launcher icon-ების გენერაცია brand SVG-დან → drawable-*dpi overlay.

ATAK upstream იყენებს drawable-{ldpi,mdpi,hdpi,xhdpi}/ic_atak_launcher.png.
xxhdpi/xxxhdpi დამატებითია თანამედროვე მოწყობილობებისთვის.

    python3 tools/gen-icons.py
"""
from __future__ import annotations

import io
from pathlib import Path

import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / "custom/brand/dhgm-logo.svg"
OUT = ROOT / "custom/overlay/atak/ATAK/app/src/main/res"

# Android density → launcher icon px (legacy drawable sizes)
DENSITIES = {
    "ldpi": 36,
    "mdpi": 48,
    "hdpi": 72,
    "xhdpi": 96,
    "xxhdpi": 144,
    "xxxhdpi": 192,
}

NAMES = ("ic_atak_launcher.png", "ic_mil_atak_launcher.png")


def main() -> int:
    if not SVG.is_file():
        print(f"✗ SVG არ არის: {SVG}")
        return 1

    for density, size in DENSITIES.items():
        png_bytes = cairosvg.svg2png(url=str(SVG), output_width=size, output_height=size)
        # ოპტიმიზაცია PNG-ად (cairosvg უკვე PNG-ს აბრუნებს; PIL ვალიდაცია)
        img = Image.open(io.BytesIO(png_bytes))
        outdir = OUT / f"drawable-{density}"
        outdir.mkdir(parents=True, exist_ok=True)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        data = buf.getvalue()
        for name in NAMES:
            path = outdir / name
            path.write_bytes(data)
            print(f"  + {path.relative_to(ROOT)} ({size}px)")

    # brand/ 512px — Play Store / about screen
    brand512 = ROOT / "custom/brand/dhgm-logo-512.png"
    cairosvg.svg2png(url=str(SVG), write_to=str(brand512), output_width=512, output_height=512)
    print(f"  + {brand512.relative_to(ROOT)}")

    print("✓ icon-ები გენერირებულია")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
