#!/usr/bin/env python3
"""DHGM: აპლიკაციის ენის override — attachBaseContext → DhgmLocale.wrap().

ATAK-ს ენის არჩევანი არ აქვს (სისტემის locale-ს მიჰყვება). რომ ქართულ `values-ka`
ინგლისურ ტელეფონზეც მუშაობდეს, არჩეულ locale-ს ვადებთ სამ base კლასზე:

  * ``MetricFragmentActivity``   — ATAKActivity და ყველა map-Activity
  * ``MetricPreferenceActivity`` — SettingsActivity (პარამეტრებ)
  * ``ATAKApplication``          — app context (Toast, plugin-ებ, service-ებ)

იდემპოტენტური; ნიმუშის დაკარგვაზე ხმამაღლა ვარდება (silent skip არა).

    python3 tools/patch-locale-override.py <atak-src-root>
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "DHGM: locale override"

TARGETS = {
    "com/atakmap/android/metrics/activity/MetricFragmentActivity.java":
        "public class MetricFragmentActivity extends FragmentActivity {",
    "com/atakmap/android/metrics/activity/MetricPreferenceActivity.java":
        "public class MetricPreferenceActivity extends PreferenceActivity {",
    "com/atakmap/app/ATAKApplication.java":
        "public class ATAKApplication extends Application {",
}

OVERRIDE = '''

    // ==== %s ====
    // არჩეულ ენა (DHGM plugin → toolbar „ენა / Language") მოწყობილობის locale-ს ცვლის.
    // ცვლილება აპის გადატვირთვისას შედის ძალაში — Android resources-ს აქ კითხულობს.
    @Override
    protected void attachBaseContext(android.content.Context base) {
        super.attachBaseContext(com.atakmap.app.DhgmLocale.wrap(base));
    }
    // ==== /%s ====
''' % (MARKER, MARKER)


def patch(path: Path, anchor: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return False
    if anchor not in text:
        raise SystemExit("✗ ნიმუში ვერ ვიპოვე (upstream შეიცვალა): %s\n    %s" % (path, anchor))
    path.write_text(text.replace(anchor, anchor + OVERRIDE, 1), encoding="utf-8")
    return True


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: patch-locale-override.py <atak-src-root>", file=sys.stderr)
        return 1
    root = Path(sys.argv[1])
    if not root.is_dir():
        print("  ⚠ %s ვერ მოიძებნა — გამოტოვებულია" % root, file=sys.stderr)
        return 0
    for rel, anchor in TARGETS.items():
        path = root / rel
        if not path.is_file():
            raise SystemExit("✗ %s ვერ მოიძებნა — ATAK-ის ხე შეიცვალა" % path)
        print("  ✓ locale override %s: %s"
              % ("დაიდო" if patch(path, anchor) else "უკვე დადებულია", rel))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
