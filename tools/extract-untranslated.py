#!/usr/bin/env python3
"""უთარგმნელი სტრინგების ამოღება — values/strings.xml vs values-ka/strings.xml.

გამოაქვს XML ფრაგმენტი, რომელშიც მხოლოდ ჯერ-უთარგმნელი string-ებია (ინგლისური
ტექსტით), მზად თარგმნისთვის და values-ka/strings.xml-ში ჩასამატებლად.

    python3 tools/extract-untranslated.py            # ყველა უთარგმნელი
    python3 tools/extract-untranslated.py --limit 100
"""

import argparse
import os
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPSTREAM = os.path.join(ROOT, "atak/atak/ATAK/app/src/main/res/values/strings.xml")
UPSTREAM_FALLBACK = "/tmp/atak_strings.xml"  # CI/აგენტის გარემოში bootstrap-ის გარეშე
KA = os.path.join(ROOT, "custom/overlay/atak/ATAK/app/src/main/res/values-ka/strings.xml")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=0, help="მაქს. რაოდენობა (0 = ყველა)")
    args = p.parse_args()

    if not os.path.exists(UPSTREAM):
        if os.path.exists(UPSTREAM_FALLBACK):
            upstream = UPSTREAM_FALLBACK
        else:
            print("✗ upstream strings.xml არ არის — ჯერ tools/bootstrap-atak.sh", file=sys.stderr)
            return 1
    else:
        upstream = UPSTREAM

    done = set()
    if os.path.exists(KA):
        for el in ET.parse(KA).getroot().iter("string"):
            done.add(el.get("name"))

    todo = []
    for el in ET.parse(upstream).getroot().iter("string"):
        if el.get("translatable") == "false":
            continue
        if el.get("name") not in done:
            todo.append(el)

    total = len(todo)
    if args.limit:
        todo = todo[: args.limit]
    for el in todo:
        text = (el.text or "").replace("\n", "\\n")
        print('    <string name="%s">%s</string>' % (el.get("name"), text))
    print("<!-- უთარგმნელი: %d / ნაჩვენებია: %d / თარგმნილია: %d -->"
          % (total, len(todo), len(done)), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
