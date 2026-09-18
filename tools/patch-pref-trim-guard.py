#!/usr/bin/env python3
"""ATAK settings-ის crash-ის fix — მოჭრილ preference-ებზე findPreference() null აღარ ბრუნდება.

პრობლემა: `hide-preferences.py`-ით XML-იდან ამოღებულ entry-ებს core უპირობოდ ეძებს, მაგ.
``MyPreferenceFragment.onCreate``:

    Preference networkPrefs = findPreference("networkPrefs");
    networkPrefs.setOnPreferenceClickListener(...);   // NPE → პარამეტრებ იკრაშება

ATAK-ის core არსად არ ამოწმებს ``findPreference(...) == null``, ამიტომ ერთი ქირურგიული
override ჰყოფნის: მოჭრილ key-ებზე ვაბრუნებთ **მიუმაგრებელ** dummy Preference-ს — listener
დაესმება, ეკრანზე არაფერ ჩანს, NPE არ ხდება. სხვა key-ებზე ქცევა უცვლელია.

გაშვება (იდემპოტენტური):  python3 tools/patch-pref-trim-guard.py <AtakPreferenceFragment.java>
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "DHGM: trimmed-preference guard"

#: key-ებ, რომლებ `apply-dhgm-overlay.sh` 9/9-ში XML-იდან იჭრება (სინქრონში დაიჭირე).
TRIMMED_KEYS = (
    "networkPrefs", "accounts", "legacyPrefs",          # my_preferences.xml
    "settingsPref", "bluetoothPref", "atakAccounts",    # main_preferences.xml
    "serverConnections", "tadiljSettings",              # network_preferences.xml
)

#: core-ის findPreference()-ის ბოლო (upstream): super → allkeys → return.
ANCHOR = """        Preference p = super.findPreference(key);
        if (p == null)
            p = allkeys.get(key.toString());
        return p;
    }"""

REPLACEMENT = """        Preference p = super.findPreference(key);
        if (p == null)
            p = allkeys.get(key.toString());
        if (p == null)
            p = dhgmTrimmedStub(key);
        return p;
    }

    // ==== %(marker)s ====
    // DHGM-ში ეს entry-ებ settings-ის XML-იდან ამოღებულია (TAK server / Bluetooth /
    // Accounts / TADIL-J არ სჭირდება). ATAK-ის core მათ უპირობოდ ეძებს და მიღებულ
    // Preference-ზე listener-ს სვამს — null-ზე NPE-ს იძლეოდა settings-ის გახსნისას.
    // აქ ვაბრუნებთ მიუმაგრებელ stub-ს: core-ის კოდ უცვლელად მუშაობს, UI-ზე არაფერ ჩანს.
    private static final java.util.Set<String> DHGM_TRIMMED_KEYS = new java.util.HashSet<>(
            java.util.Arrays.asList(%(keys)s));

    private final Map<String, Preference> dhgmTrimmedStubs = new HashMap<>();

    private Preference dhgmTrimmedStub(final CharSequence key) {
        if (key == null || !DHGM_TRIMMED_KEYS.contains(key.toString()))
            return null;
        final String k = key.toString();
        Preference stub = dhgmTrimmedStubs.get(k);
        if (stub == null) {
            Context ctx = getActivity();
            if (ctx == null)
                ctx = appContext;
            if (ctx == null)
                return null;  // context-ის გარეშე stub-ს ვერ შევქმნით
            stub = new Preference(ctx);
            stub.setKey(k);
            dhgmTrimmedStubs.put(k, stub);
            Log.d(TAG, "DHGM: trimmed preference requested, returning stub: " + k);
        }
        return stub;
    }
    // ==== /%(marker)s ====""" % {
    "marker": MARKER,
    "keys": ", ".join('"%s"' % k for k in TRIMMED_KEYS),
}


def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return False
    if ANCHOR not in text:
        raise SystemExit("✗ AtakPreferenceFragment.findPreference()-ის ნიმუში ვერ ვიპოვე — "
                         "upstream შეიცვალა: %s" % path)
    path.write_text(text.replace(ANCHOR, REPLACEMENT, 1), encoding="utf-8")
    return True


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: patch-pref-trim-guard.py <AtakPreferenceFragment.java>", file=sys.stderr)
        return 1
    path = Path(sys.argv[1])
    if not path.is_file():
        print("  ⚠ %s ვერ მოიძებნა — გამოტოვებულია" % path, file=sys.stderr)
        return 0
    print("  ✓ trimmed-preference guard %s: %s"
          % ("დაიდო" if patch(path) else "უკვე დადებულია", path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
