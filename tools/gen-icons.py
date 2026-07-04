#!/usr/bin/env python3
"""DHGM brand assets: launcher icons + splash screens → overlay drawable-*dpi.

    python3 tools/gen-icons.py

საჭიროა: pip install cairosvg pillow
"""
from __future__ import annotations

import io
from pathlib import Path

import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
LOGO_SVG = ROOT / "custom/brand/dhgm-logo.svg"
SPLASH_SVG = ROOT / "custom/brand/dhgm-splash.svg"
OUT = ROOT / "custom/overlay/atak/ATAK/app/src/main/res"

# Android density → launcher icon px (legacy drawable sizes)
ICON_DENSITIES = {
    "ldpi": 36,
    "mdpi": 48,
    "hdpi": 72,
    "xhdpi": 96,
    "xxhdpi": 144,
    "xxxhdpi": 192,
}

# Splash landscape (width x height) — centerCrop-ზე ოპტიმიზებული
SPLASH_LANDSCAPE = {
    "ldpi": (800, 480),
    "mdpi": (1024, 600),
    "hdpi": (1280, 720),
    "xhdpi": (1920, 1080),
    "xxhdpi": (2560, 1440),
    "xxxhdpi": (3840, 2160),
}

ICON_NAMES = ("ic_atak_launcher.png", "ic_mil_atak_launcher.png")
SPLASH_NAMES = ("atak_splash.png",)
SPLASH_PORTRAIT_NAMES = ("atak_splash_portrait.png",)

BG = "#0B0E14"


def _png_bytes(svg: Path, width: int, height: int) -> bytes:
    return cairosvg.svg2png(url=str(svg), output_width=width, output_height=height)


def _write_png(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(io.BytesIO(data))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    path.write_bytes(buf.getvalue())


def gen_launcher_icons() -> None:
    if not LOGO_SVG.is_file():
        raise FileNotFoundError(LOGO_SVG)
    for density, size in ICON_DENSITIES.items():
        data = _png_bytes(LOGO_SVG, size, size)
        outdir = OUT / f"drawable-{density}"
        for name in ICON_NAMES:
            _write_png(outdir / name, data)
            print(f"  + {outdir.name}/{name} ({size}px)")


def gen_splash() -> None:
    if not SPLASH_SVG.is_file():
        raise FileNotFoundError(SPLASH_SVG)
    for density, (w, h) in SPLASH_LANDSCAPE.items():
        data = _png_bytes(SPLASH_SVG, w, h)
        outdir = OUT / f"drawable-{density}"
        for name in SPLASH_NAMES:
            _write_png(outdir / name, data)
            print(f"  + {outdir.name}/{name} ({w}x{h})")
        # portrait — იგივე SVG, ვერტიკალური ზომები
        pw, ph = h, w
        pdata = _png_bytes(SPLASH_SVG, pw, ph)
        for name in SPLASH_PORTRAIT_NAMES:
            _write_png(outdir / name, pdata)
            print(f"  + {outdir.name}/{name} ({pw}x{ph})")


def gen_brand512() -> None:
    brand512 = ROOT / "custom/brand/dhgm-logo-512.png"
    cairosvg.svg2png(url=str(LOGO_SVG), write_to=str(brand512), output_width=512, output_height=512)
    print(f"  + {brand512.relative_to(ROOT)}")


def main() -> int:
    print("== launcher icons ==")
    gen_launcher_icons()
    print("== splash screens ==")
    gen_splash()
    print("== brand 512 ==")
    gen_brand512()
    print("✓ brand assets გენერირებულია")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
