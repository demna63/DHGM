#!/usr/bin/env python3
"""values-ka/parts/*.xml ფრაგმენტების შერწყმა strings.xml-ში."""
import glob
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KA = os.path.join(ROOT, "custom/overlay/atak/ATAK/app/src/main/res/values-ka/strings.xml")
# ⚠️ parts/ res/-ის გარეთაა: res/values-ka/-ში ქვესაქაღალდე aapt2-ის რესურს-ხეს ბინძურებს.
PARTS = os.path.join(ROOT, "custom/translations/ka-parts")


def main() -> int:
    parts = sorted(glob.glob(os.path.join(PARTS, "chunk_*.xml")))
    if not parts:
        print("✗ parts/ ცარიელია", file=sys.stderr)
        return 1

    new_els = []
    for pf in parts:
        for el in ET.parse(pf).getroot().iter("string"):
            new_els.append(el)

    tree = ET.parse(KA)
    root = tree.getroot()
    existing = {el.get("name") for el in root.iter("string")}
    added = 0
    for el in new_els:
        if el.get("name") not in existing:
            root.append(el)
            existing.add(el.get("name"))
            added += 1

    # pretty-ish write
    lines = ['<?xml version="1.0" encoding="utf-8"?>',
             '<!-- DHGM — ქართული ლოკალიზაცია (values-ka overlay).',
             '     სრული თარგმანი upstream values/strings.xml-დან. -->',
             '<resources>']
    for el in root:
        if el.tag is ET.Comment:
            lines.append("    <!--%s-->" % (el.text or ""))
            continue
        if el.tag != "string":
            continue
        text = el.text or ""
        text = text.replace("&", "&amp;").replace("<", "&lt;")
        # restore common entities we want literal
        text = text.replace("&amp;amp;", "&amp;")
        lines.append('    <string name="%s">%s</string>' % (el.get("name"), text))
    lines.append("</resources>")
    with open(KA, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("✓ დაემატა %d სტრინგი (სულ %d)" % (added, len(existing)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
