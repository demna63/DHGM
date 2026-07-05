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
SPLASH_PORTRAIT_SVG = ROOT / "custom/brand/dhgm-splash-portrait.svg"
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

# Adaptive icon foreground (108dp canvas; logo ~62% — Android safe zone ⌀66dp/108dp)
FOREGROUND_DENSITIES = {
    "mdpi": 108,
    "hdpi": 162,
    "xhdpi": 216,
    "xxhdpi": 324,
    "xxxhdpi": 432,
}
FOREGROUND_NAME = "ic_atak_launcher_foreground.png"
MIPMAP_ICON_NAMES = ("ic_atak_launcher.png", "ic_mil_atak_launcher.png")
ADAPTIVE_XML_NAMES = ("ic_atak_launcher.xml", "ic_mil_atak_launcher.xml")


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
        # mipmap fallback (pre-API 26 და non-adaptive launchers)
        mipdir = OUT / f"mipmap-{density}"
        for name in MIPMAP_ICON_NAMES:
            _write_png(mipdir / name, data)
            print(f"  + {mipdir.name}/{name} ({size}px)")


def gen_adaptive_foreground() -> None:
    """Adaptive icon foreground — ლოგო safe zone-ში (~62%; ⌀66/108 masking guard)."""
    if not LOGO_SVG.is_file():
        raise FileNotFoundError(LOGO_SVG)
    for density, canvas in FOREGROUND_DENSITIES.items():
        logo = int(canvas * 0.62)
        data = _png_bytes(LOGO_SVG, logo, logo)
        outdir = OUT / f"drawable-{density}"
        _write_png(outdir / FOREGROUND_NAME, data)
        print(f"  + {outdir.name}/{FOREGROUND_NAME} ({logo}px in {canvas}dp canvas)")


def gen_adaptive_xml() -> None:
    """mipmap-anydpi-v26 adaptive-icon XML."""
    v26 = OUT / "mipmap-anydpi-v26"
    v26.mkdir(parents=True, exist_ok=True)
    body = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/dhgm_launcher_bg"/>
    <foreground android:drawable="@drawable/ic_atak_launcher_foreground"/>
</adaptive-icon>
"""
    for name in ADAPTIVE_XML_NAMES:
        (v26 / name).write_text(body, encoding="utf-8")
        print(f"  + mipmap-anydpi-v26/{name}")


def gen_splash() -> None:
    if not SPLASH_SVG.is_file():
        raise FileNotFoundError(SPLASH_SVG)
    if not SPLASH_PORTRAIT_SVG.is_file():
        raise FileNotFoundError(SPLASH_PORTRAIT_SVG)
    for density, (w, h) in SPLASH_LANDSCAPE.items():
        data = _png_bytes(SPLASH_SVG, w, h)
        outdir = OUT / f"drawable-{density}"
        for name in SPLASH_NAMES:
            _write_png(outdir / name, data)
            print(f"  + {outdir.name}/{name} ({w}x{h})")
        pw, ph = h, w
        pdata = _png_bytes(SPLASH_PORTRAIT_SVG, pw, ph)
        for name in SPLASH_PORTRAIT_NAMES:
            _write_png(outdir / name, pdata)
            print(f"  + {outdir.name}/{name} ({pw}x{ph}, portrait SVG)")


def gen_brand512() -> None:
    brand512 = ROOT / "custom/brand/dhgm-logo-512.png"
    cairosvg.svg2png(url=str(LOGO_SVG), write_to=str(brand512), output_width=512, output_height=512)
    print(f"  + {brand512.relative_to(ROOT)}")


def main() -> int:
    print("== launcher icons ==")
    gen_launcher_icons()
    print("== adaptive icon foreground ==")
    gen_adaptive_foreground()
    print("== adaptive icon XML (API 26+) ==")
    gen_adaptive_xml()
    print("== splash screens ==")
    gen_splash()
    print("== brand 512 ==")
    gen_brand512()
    print("✓ brand assets გენერირებულია")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
