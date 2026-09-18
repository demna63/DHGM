#!/usr/bin/env python3
"""DHGM overlay-ის ინვარიანტებ — CI-ის სწრაფ „predohrannik".

აქამდე ორჯერ გავიდა ჩავარდნა, რომელიც წუთებ დაგვიჯდა (ან საერთოდ არ გამოჩნდა):
  * settings-ის XML-იდან key-ის მოჭრა guard-ის სიის განახლების გარეშე → NPE runtime-ზე;
  * patch-ის ბილიკი არასწორ იყო → fix ჩუმად არ იდებოდა.

ორ რეჟიმი:
  --source-only   repo-ს ინვარიანტებ (atak/ არ სჭირდება) — CI-ში build-ამდე
  (default)       იგივე + atak/-ზე დადებულ patch-ების შემოწმება — overlay-ის შემდეგ

    python3 tools/check-overlay-invariants.py --source-only
    python3 tools/check-overlay-invariants.py
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

APPLY = os.path.join(ROOT, "tools", "apply-dhgm-overlay.sh")
GUARD = os.path.join(ROOT, "tools", "patch-pref-trim-guard.py")
LOCALE_CORE = os.path.join(
    ROOT, "custom/overlay/atak/ATAK/app/src/main/java/com/atakmap/app/DhgmLocale.java")
LOCALE_PLUGIN = os.path.join(
    ROOT, "plugin/dhgm-drones/app/src/main/java/ge/dronehub/dhgm/plugin/DhgmLanguageReceiver.java")
PLUGIN_RES = os.path.join(ROOT, "plugin/dhgm-drones/app/src/main/res")

ATAK_JAVA = os.path.join(ROOT, "atak/atak/ATAK/app/src/main/java")
PATCHED = {
    "com/atakmap/android/preference/AtakPreferenceFragment.java": "DHGM: trimmed-preference guard",
    "com/atakmap/android/metrics/activity/MetricFragmentActivity.java": "DHGM: locale override",
    "com/atakmap/android/metrics/activity/MetricPreferenceActivity.java": "DHGM: locale override",
    "com/atakmap/app/ATAKApplication.java": "DHGM: locale override",
}
FSU = os.path.join(ROOT,
                   "atak/takkernel/engine/src/main/java/com/atakmap/coremap/filesystem/FileSystemUtils.java")

_FMT = re.compile(r"%(?:(\d+)\$)?[-#+ 0,(]*\d*(?:\.\d+)?([a-zA-Z%])")

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def const(java_src: str, name: str) -> str | None:
    m = re.search(r'\b%s\s*=\s*"([^"]*)"' % re.escape(name), java_src)
    return m.group(1) if m else None


def check_trimmed_keys_in_guard() -> None:
    """hide-preferences.py-ით მოჭრილ ყოველ key guard-ის სიაშიც უნდა იყოს."""
    apply_src = read(APPLY)
    trimmed: set[str] = set()
    for line in apply_src.splitlines():
        line = line.strip()
        if line.startswith("python3 tools/hide-preferences.py"):
            parts = line.split()
            trimmed.update(p for p in parts[3:] if not p.startswith(("-", '"', "$")))
    if not trimmed:
        fail("apply-dhgm-overlay.sh-ში hide-preferences.py-ის გამოძახება ვერ ვიპოვე")
        return
    guard_src = read(GUARD)
    m = re.search(r"TRIMMED_KEYS\s*=\s*\((.*?)\)", guard_src, re.S)
    if not m:
        fail("patch-pref-trim-guard.py-ში TRIMMED_KEYS ვერ ვიპოვე")
        return
    guarded = set(re.findall(r'"([^"]+)"', m.group(1)))
    missing = sorted(trimmed - guarded)
    if missing:
        fail("settings-იდან მოჭრილ key-ებ guard-ის სიაში არ არიან (runtime NPE): %s"
             % ", ".join(missing))
    extra = sorted(guarded - trimmed)
    if extra:
        fail("guard-ის სიაში key-ებ, რომლებ აღარ იჭრება (მოაცილე): %s" % ", ".join(extra))


def check_locale_keys() -> None:
    """core-ის და plugin-ის ენის key/default ერთნაირ უნდა იყოს."""
    core, plug = read(LOCALE_CORE), read(LOCALE_PLUGIN)
    for name in ("PREF_KEY", "SYSTEM", "DEFAULT"):
        a, b = const(core, name), const(plug, name)
        if a is None or b is None:
            fail("ენის კონსტანტა %s ვერ ვიპოვე (core=%r, plugin=%r)" % (name, a, b))
        elif a != b:
            fail("ენის კონსტანტა %s არ ემთხვევა: core=%r, plugin=%r" % (name, a, b))


def _strings(path: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for el in ET.parse(path).getroot().iter("string"):
        out[el.get("name")] = "".join(el.itertext())
    return out


def _fmt_sig(text: str) -> list[tuple[int, str]]:
    sig, i = [], 0
    for m in _FMT.finditer(text.replace("%%", "")):
        i += 1
        sig.append((int(m.group(1)) if m.group(1) else i, m.group(2).lower()))
    return sorted(set(sig))


def check_plugin_strings() -> None:
    """plugin-ის ყოველ სტრინგს ქართულ თარგმანი და იგივე format-არგუმენტებ უნდა ჰქონდეს."""
    en = _strings(os.path.join(PLUGIN_RES, "values/strings.xml"))
    ka = _strings(os.path.join(PLUGIN_RES, "values-ka/strings.xml"))
    missing = sorted(set(en) - set(ka))
    if missing:
        fail("plugin-ის სტრინგებ უთარგმნელია (values-ka): %s" % ", ".join(missing))
    for name in sorted(set(en) & set(ka)):
        if _fmt_sig(en[name]) != _fmt_sig(ka[name]):
            fail("plugin-ის სტრინგ %s: format-არგუმენტებ არ ემთხვევა (en=%s, ka=%s)"
                 % (name, _fmt_sig(en[name]), _fmt_sig(ka[name])))
    orphan = sorted(set(ka) - set(en))
    if orphan:
        fail("values-ka-ში სტრინგებ, რომლებ values/-ში არ არის: %s" % ", ".join(orphan))


def check_applied_patches() -> None:
    """overlay-ის შემდეგ: ყოველ patch რეალურად დევს atak/-ში."""
    if not os.path.isdir(ATAK_JAVA):
        fail("atak/ ვერ ვიპოვე — ჯერ tools/bootstrap-atak.sh + apply-dhgm-overlay.sh")
        return
    for rel, marker in PATCHED.items():
        path = os.path.join(ATAK_JAVA, rel)
        if not os.path.isfile(path):
            fail("%s ვერ მოიძებნა (ATAK-ის ხე შეიცვალა?)" % rel)
        elif marker not in read(path):
            fail("%s: marker %s არ დევს — apply-dhgm-overlay.sh გაუშვი" % (rel, marker))
    if not os.path.isfile(FSU):
        fail("FileSystemUtils.java ვერ მოიძებნა — mount deadlock fix ვერ დაიდება")
    elif "DHGM: drain mount stdout before waitFor" not in read(FSU):
        fail("FileSystemUtils.java: mount deadlock fix არ დევს")
    ka = os.path.join(ROOT, "atak/atak/ATAK/app/src/main/res/values-ka/strings.xml")
    if not os.path.isfile(ka):
        fail("values-ka/strings.xml overlay-ით არ დადებულა")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-only", action="store_true",
                   help="მხოლოდ repo-ს ინვარიანტებ (atak/ არ სჭირდება)")
    args = p.parse_args()

    check_trimmed_keys_in_guard()
    check_locale_keys()
    check_plugin_strings()
    if not args.source_only:
        check_applied_patches()

    if errors:
        for e in errors:
            print("✗ %s" % e, file=sys.stderr)
        return 1
    print("✓ overlay-ის ინვარიანტებ რიგზეა%s" % ("" if args.source_only else " (patch-ებიც დევს)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
