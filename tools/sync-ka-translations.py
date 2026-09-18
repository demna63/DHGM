#!/usr/bin/env python3
"""ქართულ თარგმანის სინქრონი ATAK-ის upstream ვერსიასთან.

ATAK-ის ვერსიის აწევისას (`ATAK_REF`) upstream-ის სტრინგებ იცვლება: ჩნდება ახლები,
ქრება ძველებ, ინგლისურ ტექსტ იცვლება (ჩვენ თარგმანი ჩუმად ძველდება), ან იცვლება
format-არგუმენტებ (`%1$s`) — ეს უკვე runtime crash-ია.

lock ფაილი (`custom/translations/ka-upstream.lock.json`) იმახსოვრებს, **რომელ** ინგლისურ
ტექსტს ითარგმნა თითო სტრინგი (sha + format-ხელმოწერა). შედარება 4 კატეგორიას იძლევა:

    removed   — upstream-ში აღარ არის, values-ka-ში კი წევს  (blocking: aapt/lint)
    fmt       — format-არგუმენტებ ka↔en არ ემთხვევა          (blocking: crash)
    stale     — ინგლისურ ტექსტ შეიცვალა თარგმნის მერე        (გადასათარგმნი)
    new       — ახალ upstream სტრინგი, თარგმანის გარეშე      (გადასათარგმნი)

გამოყენება:
    python3 tools/sync-ka-translations.py                 # ანგარიში (exit 1 blocking-ზე)
    python3 tools/sync-ka-translations.py --check         # იგივე, CI-სთვის ::warning-ებით
    python3 tools/sync-ka-translations.py --prune         # removed-ის მოცილება values-ka-დან
    python3 tools/sync-ka-translations.py --todo out.xml  # stale+new → გადასათარგმნი XML
    python3 tools/sync-ka-translations.py --update        # lock-ის განახლება (თარგმნის შემდეგ)

იხ. `docs/atak-upgrade.md`.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPSTREAM_GLOB = os.path.join(ROOT, "atak/atak/ATAK/app/src/main/res/values/strings.xml")
KA = os.path.join(ROOT, "custom/overlay/atak/ATAK/app/src/main/res/values-ka/strings.xml")
LOCK = os.path.join(ROOT, "custom/translations/ka-upstream.lock.json")
WORKFLOW = os.path.join(ROOT, ".github/workflows/build-dhgm.yml")

_FMT = re.compile(r"%(?:(\d+)\$)?[-#+ 0,(]*\d*(?:\.\d+)?([a-zA-Z%])")


def fmt_sig(text: str) -> str:
    """format-არგუმენტების ხელმოწერა: '1s,2d' (რიგისგან დამოუკიდებელ, უნიკალურ)."""
    out, i = [], 0
    for m in _FMT.finditer(text.replace("%%", "")):
        i += 1
        out.append("%d%s" % (int(m.group(1)) if m.group(1) else i, m.group(2).lower()))
    return ",".join(sorted(set(out)))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def strings_of(path: str, translatable_only: bool = False) -> dict[str, str]:
    out: dict[str, str] = {}
    for el in ET.parse(path).getroot().iter("string"):
        if translatable_only and el.get("translatable") == "false":
            continue
        name = el.get("name")
        if name:
            out[name] = "".join(el.itertext())
    return out


def atak_ref() -> str:
    try:
        m = re.search(r'ATAK_REF:\s*"([^"]+)"', open(WORKFLOW, encoding="utf-8").read())
        return m.group(1) if m else "unknown"
    except OSError:
        return "unknown"


def load_lock() -> dict:
    if not os.path.isfile(LOCK):
        return {"atak_ref": None, "strings": {}}
    with open(LOCK, encoding="utf-8") as fh:
        return json.load(fh)


def save_lock(upstream: dict[str, str], ref: str) -> None:
    data = {
        "_comment": "ქართულ თარგმანის სინქრონი — tools/sync-ka-translations.py",
        "atak_ref": ref,
        "strings": {n: "%s|%s" % (sha(t), fmt_sig(t)) for n, t in sorted(upstream.items())},
    }
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    with open(LOCK, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1, sort_keys=False)
        fh.write("\n")


def classify(upstream: dict[str, str], ka: dict[str, str], lock: dict) -> dict[str, list]:
    locked = lock.get("strings", {})
    res: dict[str, list] = {"removed": [], "fmt": [], "stale": [], "new": []}
    for name in sorted(ka):
        if name not in upstream:
            res["removed"].append(name)
            continue
        if fmt_sig(upstream[name]) != fmt_sig(ka[name]):
            res["fmt"].append((name, fmt_sig(upstream[name]), fmt_sig(ka[name])))
            continue
        entry = locked.get(name)
        if entry and entry.split("|", 1)[0] != sha(upstream[name]):
            res["stale"].append(name)
    for name in sorted(upstream):
        if name not in ka:
            res["new"].append(name)
    return res


def prune(names: list[str]) -> int:
    if not names:
        return 0
    text = open(KA, encoding="utf-8").read()
    removed = 0
    for name in names:
        pat = re.compile(r"[ \t]*<string name=\"%s\"[^>]*>.*?</string>\s*\n" % re.escape(name),
                         re.S)
        text, n = pat.subn("", text, count=1)
        removed += n
    open(KA, "w", encoding="utf-8").write(text)
    return removed


def write_todo(path: str, upstream: dict[str, str], ka: dict[str, str],
               report: dict[str, list]) -> int:
    rows = []
    for name in report["new"]:
        rows.append((name, upstream[name], None))
    for name in report["stale"]:
        rows.append((name, upstream[name], ka.get(name)))
    if not rows:
        return 0
    with open(path, "w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0" encoding="utf-8"?>\n')
        fh.write("<!-- გადასათარგმნი: ახალ (new) + დაძველებულ (stale) სტრინგებ.\n")
        fh.write("     თარგმნე value-ებ და ჩააგდე custom/translations/ka-parts/chunk_*.xml-ად,\n")
        fh.write("     მერე: tools/merge-ka-parts.py && tools/sync-ka-translations.py --update -->\n")
        fh.write("<resources>\n")
        for name, en, old_ka in rows:
            if old_ka is not None:
                fh.write("    <!-- ძველ ka: %s -->\n" % old_ka.replace("--", "—"))
            fh.write('    <string name="%s">%s</string>\n'
                     % (name, en.replace("&", "&amp;").replace("<", "&lt;")))
        fh.write("</resources>\n")
    return len(rows)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true", help="CI რეჟიმი (::warning ანოტაციებ)")
    p.add_argument("--prune", action="store_true", help="upstream-იდან წაშლილ სტრინგებ მოაცილე")
    p.add_argument("--todo", metavar="FILE", help="გადასათარგმნი სტრინგებ XML-ად")
    p.add_argument("--update", action="store_true", help="lock-ის განახლება მიმდინარე upstream-ზე")
    args = p.parse_args()

    if not os.path.isfile(UPSTREAM_GLOB):
        print("✗ upstream strings.xml ვერ ვიპოვე — ჯერ tools/bootstrap-atak.sh", file=sys.stderr)
        return 1

    upstream = strings_of(UPSTREAM_GLOB, translatable_only=True)
    ka = strings_of(KA)
    lock = load_lock()
    ref = atak_ref()

    if args.update:
        save_lock(upstream, ref)
        print("✓ lock განახლდა: %d სტრინგი, ATAK_REF=%s" % (len(upstream), ref))
        return 0

    report = classify(upstream, ka, lock)

    if args.prune and report["removed"]:
        n = prune(report["removed"])
        print("✓ მოცილდა %d სტრინგი, რომელიც upstream-ში აღარ არის" % n)
        report["removed"] = []

    todo_count = 0
    if args.todo:
        todo_count = write_todo(args.todo, upstream, ka, report)

    translated = len(ka) - len(report["removed"])
    print("ATAK_REF=%s (lock: %s) · upstream translatable=%d · ka=%d (%.1f%%)"
          % (ref, lock.get("atak_ref"), len(upstream), translated,
             100.0 * translated / max(1, len(upstream))))
    print("  new=%d  stale=%d  removed=%d  fmt-mismatch=%d"
          % (len(report["new"]), len(report["stale"]), len(report["removed"]), len(report["fmt"])))

    warn = "::warning::" if args.check else "  ⚠ "
    if report["new"]:
        print("%sუთარგმნელ ახალ სტრინგი: %d (%s%s)"
              % (warn, len(report["new"]), ", ".join(report["new"][:5]),
                 " …" if len(report["new"]) > 5 else ""))
    if report["stale"]:
        print("%sინგლისურ ტექსტ შეიცვალა, თარგმან ძველია: %d (%s%s)"
              % (warn, len(report["stale"]), ", ".join(report["stale"][:5]),
                 " …" if len(report["stale"]) > 5 else ""))
    if args.todo:
        print("  → გადასათარგმნი XML: %s (%d სტრინგი)" % (args.todo, todo_count))

    blocking = False
    for name, up_sig, ka_sig in report["fmt"]:
        print("::error::" if args.check else "✗ ",
              "format-არგუმენტებ არ ემთხვევა: %s (en=%s, ka=%s)" % (name, up_sig, ka_sig),
              file=sys.stderr)
        blocking = True
    if report["removed"]:
        print(("::error::" if args.check else "✗ ")
              + "values-ka-ში სტრინგებ, რომლებ upstream-ში აღარ არის: %s%s (--prune)"
              % (", ".join(report["removed"][:10]), " …" if len(report["removed"]) > 10 else ""),
              file=sys.stderr)
        blocking = True

    if blocking:
        return 1
    print("✓ თარგმან upstream-თან თავსებადია")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
