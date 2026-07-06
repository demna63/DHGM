#!/usr/bin/env python3
"""ATAK preference XML-დან <Preference android:key="..."/> ჩანაწერების მოჭრა —
DHGM-ის მარტივი LAN/GCS ნაკადისთვის ზედმეტი პარამეტრები (TAK server streaming,
TADIL-J, Bluetooth, TAK Accounts). იდემპოტენტური: უკვე მოჭრილ/არარსებულ
key-ზე უბრალოდ ✓-ს გამოაქვს, არაფერს არ წერს.

გამოძახება:
    python3 tools/hide-preferences.py <xml-file> <key> [key ...]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# self-closing <Preference .../> და ღია/დახურული <Preference ...>...</Preference> ორივე ვარიანტი
PATTERNS = (
    r'[ \t]*<Preference\b[^>]*android:key="{key}"[^>]*/>[ \t]*\n?',
    r'[ \t]*<Preference\b[^>]*android:key="{key}"[^>]*>.*?</Preference>[ \t]*\n?',
)


def strip_key(text: str, key: str) -> tuple[str, bool]:
    for pattern in PATTERNS:
        new_text, n = re.subn(pattern.format(key=re.escape(key)), "", text, count=1, flags=re.DOTALL)
        if n:
            return new_text, True
    return text, False


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: hide-preferences.py <xml-file> <key> [key ...]", file=sys.stderr)
        return 1
    path = Path(sys.argv[1])
    keys = sys.argv[2:]
    if not path.is_file():
        print(f"  ⚠ {path} ვერ მოიძებნა — გამოტოვებულია")
        return 0
    text = path.read_text(encoding="utf-8")
    changed = False
    for key in keys:
        if f'android:key="{key}"' not in text:
            print(f"  ✓ {key} უკვე არ არის {path.name}-ში")
            continue
        text, ok = strip_key(text, key)
        if ok:
            print(f"  ✓ {key} მოიჭრა: {path.name}")
            changed = True
        else:
            print(f"  ⚠ {key} ვერ მოიჭრა (pattern არ ემთხვევა) — upstream შეიცვალა, გადაამოწმე ხელით: {path}")
    if changed:
        path.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
