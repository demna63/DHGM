#!/usr/bin/env python3
"""ATAK preference XML-დან preference-ჩანაწერების მოჭრა — DHGM-ის მარტივი
LAN/GCS ნაკადისთვის ზედმეტი პარამეტრები (TAK server streaming/management,
TADIL-J, Bluetooth, TAK Accounts). იდემპოტენტური.

target-ები ორ ფორმაშია:
  * bare key         → <...Preference android:key="KEY" .../>
  * @string/NAME     → <...Preference android:title="@string/NAME" .../>

path შეიძლება იყოს ცალკე XML ან დირექტორია (მაშინ ყველა *.xml სკანირდება —
სასარგებლო, როცა ზუსტი ფაილის სახელი უცნობია).

გამოძახება:
    python3 tools/hide-preferences.py <xml-file|dir> <key|@string/NAME> ...
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# ნებისმიერი "*Preference" leaf (Preference, CheckBoxPreference, custom .MyPreference),
# მაგრამ არა <PreferenceScreen> (\b Preference-ის შემდეგ Screen-ზე არ ჩერდება).
_TAG = r"[\w.]*Preference"


def _patterns(attr: str, value: str) -> tuple[str, str]:
    v = re.escape(value)
    return (
        rf'[ \t]*<{_TAG}\b[^>]*android:{attr}="{v}"[^>]*/>[ \t]*\n?',
        rf'[ \t]*<(?P<t>{_TAG})\b[^>]*android:{attr}="{v}"[^>]*>.*?</(?P=t)>[ \t]*\n?',
    )


def _target(arg: str) -> tuple[str, str]:
    """arg → (attr, value). @string/... → title match; სხვა → key match."""
    if arg.startswith("@"):
        return "title", arg
    return "key", arg


def strip_one(text: str, attr: str, value: str) -> tuple[str, bool]:
    for pattern in _patterns(attr, value):
        new_text, n = re.subn(pattern, "", text, count=1, flags=re.DOTALL)
        if n:
            return new_text, True
    return text, False


def process_file(path: Path, targets: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    changed = False
    for arg in targets:
        attr, value = _target(arg)
        if f'android:{attr}="{value}"' not in text:
            continue  # ამ ფაილში არ არის — ჩუმად
        text, ok = strip_one(text, attr, value)
        if ok:
            print(f"  ✓ {arg} მოიჭრა: {path.name}")
            changed = True
        else:
            print(f"  ⚠ {arg} ({path.name}) — pattern არ ემთხვევა, upstream შეიცვალა, გადაამოწმე")
    if changed:
        path.write_text(text, encoding="utf-8")


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: hide-preferences.py <xml-file|dir> <key|@string/NAME> ...", file=sys.stderr)
        return 1
    path = Path(sys.argv[1])
    targets = sys.argv[2:]
    if path.is_dir():
        files = sorted(path.glob("*.xml"))
        if not files:
            print(f"  ⚠ {path}-ში *.xml ვერ მოიძებნა — გამოტოვებულია")
            return 0
        for f in files:
            process_file(f, targets)
    elif path.is_file():
        process_file(path, targets)
    else:
        print(f"  ⚠ {path} ვერ მოიძებნა — გამოტოვებულია")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
