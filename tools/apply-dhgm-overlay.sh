#!/usr/bin/env bash
# DHGM overlay-ის დადება ATAK-CIV წყაროზე (იდემპოტენტური).
# GCS-ის tools/apply-qgc-patches.sh-ის ანალოგი: upstream ფაილები არ იცვლება,
# გარდა ქირურგიული, აღნიშნული sed-ებისა.
set -euo pipefail
cd "$(dirname "$0")/.."

[ -d atak/atak ] || { echo "✗ atak/ არ არის დაკლონილი — ჯერ tools/bootstrap-atak.sh"; exit 1; }

if [ -f tools/gen-icons.py ] && [ -f custom/brand/dhgm-logo.svg ]; then
  echo "== 1/9: brand assets (SVG → PNG) =="
  pip install -q cairosvg pillow 2>/dev/null || true
  python3 tools/gen-icons.py || echo "  ⚠ gen-icons.py ვერ გაეშვა (cairosvg/pillow?)"
fi

echo "== 2/9: overlay ფაილების კოპირება (custom/overlay/ → atak/) =="
rsync -a --out-format="  + %n" custom/overlay/atak/ atak/atak/

echo "== 3/9: branding (app label ATAK → DHGM) =="
MANIFEST=atak/atak/ATAK/app/src/main/AndroidManifest.xml
if [ -f "$MANIFEST" ]; then
  if grep -q 'android:icon="@drawable/ic_atak_launcher"' "$MANIFEST"; then
    sed -i '' 's|android:icon="@drawable/ic_atak_launcher"|android:icon="@mipmap/ic_atak_launcher"|g' "$MANIFEST" 2>/dev/null \
      || sed -i 's|android:icon="@drawable/ic_atak_launcher"|android:icon="@mipmap/ic_atak_launcher"|g' "$MANIFEST"
    echo "  ✓ launcher icon → @mipmap/ic_atak_launcher (adaptive API 26+)"
  elif grep -q 'android:icon="@mipmap/ic_atak_launcher"' "$MANIFEST"; then
    echo "  ✓ launcher icon უკვე @mipmap/ic_atak_launcher-ია"
  fi
  if grep -q 'android:icon="@drawable/ic_mil_atak_launcher"' "$MANIFEST"; then
    sed -i '' 's|android:icon="@drawable/ic_mil_atak_launcher"|android:icon="@mipmap/ic_mil_atak_launcher"|g' "$MANIFEST" 2>/dev/null \
      || sed -i 's|android:icon="@drawable/ic_mil_atak_launcher"|android:icon="@mipmap/ic_mil_atak_launcher"|g' "$MANIFEST"
    echo "  ✓ mil launcher icon → @mipmap/ic_mil_atak_launcher"
  fi
fi
STRINGS=atak/atak/ATAK/app/src/main/res/values/strings.xml
if grep -q '<string name="app_name" translatable="false">ATAK</string>' "$STRINGS"; then
  sed -i '' 's|<string name="app_name" translatable="false">ATAK</string>|<string name="app_name" translatable="false">DHGM</string>|' "$STRINGS" 2>/dev/null \
    || sed -i 's|<string name="app_name" translatable="false">ATAK</string>|<string name="app_name" translatable="false">DHGM</string>|' "$STRINGS"
  echo "  ✓ app_name → DHGM"
elif grep -q '>DHGM<' "$STRINGS"; then
  echo "  ✓ app_name უკვე DHGM-ია"
else
  echo "  ⚠ app_name-ის ნიმუში ვერ ვიპოვე — upstream შეიცვალა, გადაამოწმე ხელით: $STRINGS"
fi

echo "== 4/9: DEVELOPER BUILD წარწერის მოხსნა (civSdk build type) =="
GRADLE=atak/atak/ATAK/app/build.gradle
if grep -q "'\"DEVELOPER BUILD\"'" "$GRADLE"; then
  sed -i '' "s|'\"DEVELOPER BUILD\"'|'\"\"'|" "$GRADLE" 2>/dev/null \
    || sed -i "s|'\"DEVELOPER BUILD\"'|'\"\"'|" "$GRADLE"
  echo "  ✓ DEV_BANNER → ცარიელი (watermark მოიხსნა)"
elif grep -q "DEV_BANNER', '\"\"'" "$GRADLE"; then
  echo "  ✓ DEV_BANNER უკვე ცარიელია"
else
  echo "  ⚠ DEV_BANNER-ის ნიმუში ვერ ვიპოვე — upstream შეიცვალა, გადაამოწმე: $GRADLE"
fi

echo "== 5/9: package identity (applicationId + APK სახელი) =="
if grep -q 'applicationId = "com.atakmap.app"' "$GRADLE"; then
  sed -i '' 's|applicationId = "com.atakmap.app"|applicationId = "ge.dronehub.dhgm"|' "$GRADLE" 2>/dev/null \
    || sed -i 's|applicationId = "com.atakmap.app"|applicationId = "ge.dronehub.dhgm"|' "$GRADLE"
  echo "  ✓ applicationId → ge.dronehub.dhgm"
elif grep -q 'applicationId = "ge.dronehub.dhgm"' "$GRADLE"; then
  echo "  ✓ applicationId უკვე ge.dronehub.dhgm-ია"
else
  echo "  ⚠ applicationId-ის ნიმუში ვერ ვიპოვე — გადაამოწმე: $GRADLE"
fi
# civ flavor-ის suffix (.civ) ამოღება — საბოლოო id: ge.dronehub.dhgm
if grep -q 'applicationIdSuffix = ".civ"' "$GRADLE"; then
  sed -i '' 's|applicationIdSuffix = ".civ"|applicationIdSuffix = ""|' "$GRADLE" 2>/dev/null \
    || sed -i 's|applicationIdSuffix = ".civ"|applicationIdSuffix = ""|' "$GRADLE"
  echo "  ✓ applicationIdSuffix .civ → ცარიელი"
fi
if grep -q 'setProperty("archivesBaseName", "ATAK-"' "$GRADLE"; then
  sed -i '' 's|setProperty("archivesBaseName", "ATAK-"|setProperty("archivesBaseName", "DHGM-"|' "$GRADLE" 2>/dev/null \
    || sed -i 's|setProperty("archivesBaseName", "ATAK-"|setProperty("archivesBaseName", "DHGM-"|' "$GRADLE"
  echo "  ✓ archivesBaseName → DHGM-"
elif grep -q 'setProperty("archivesBaseName", "DHGM-"' "$GRADLE"; then
  echo "  ✓ archivesBaseName უკვე DHGM-ია"
fi

echo "== 6/9: სისტემური ზოლების ფერი (status/navigation bar) =="
STYLES=atak/atak/ATAK/app/src/main/res/values/styles.xml
if [ -f "$STYLES" ] && ! grep -q 'android:statusBarColor' "$STYLES"; then
  sed -i '' 's|android:navigationBarColor">@android:color/black|android:navigationBarColor">@color/darker_gray|g' "$STYLES" 2>/dev/null \
    || sed -i 's|android:navigationBarColor">@android:color/black|android:navigationBarColor">@color/darker_gray|g' "$STYLES"
  # statusBarColor ჩასმა navigationBarColor-ის შემდეგ (ATAKTheme + ATAKThemeActionBar)
  sed -i '' '/android:navigationBarColor">@color\/darker_gray/a\
        <item name="android:statusBarColor">@color/darker_gray</item>' "$STYLES" 2>/dev/null \
    || sed -i '/android:navigationBarColor">@color\/darker_gray/a\        <item name="android:statusBarColor">@color/darker_gray</item>' "$STYLES"
  echo "  ✓ statusBarColor/navigationBarColor → DroneHub navy"
elif [ -f "$STYLES" ] && grep -q 'android:statusBarColor' "$STYLES"; then
  echo "  ✓ statusBarColor უკვე დაყენებულია"
fi

echo "== 7/9: encryption passphrase auto-key (first-run დიალოგის მოხსნა) =="
DBH=atak/atak/ATAK/app/src/main/java/com/atakmap/app/ATAKDatabaseHelper.java
python3 - "$DBH" <<'PY'
import sys
p = sys.argv[1]
src = open(p, encoding="utf-8").read()
needle = "            changeKeyImpl(context, true, ksl);"
replacement = (
    "            {\n"
    "                // DHGM: first-run-ზე passphrase-ს ავტომატურად ვაგენერირებთ —\n"
    "                // მომხმარებელს დიალოგი აღარ ეკითხება (იგივე save→re-prompt ნაკადი).\n"
    "                final String dhgmAutoKey = \"DHGM\"\n"
    "                        + Long.toHexString(System.nanoTime())\n"
    "                        + Integer.toHexString(new java.util.Random().nextInt());\n"
    "                AtakAuthenticationDatabase.saveCredentials(\n"
    "                        AtakAuthenticationCredentials.TYPE_APK_DOWNLOADER,\n"
    "                        \"com.atakmap.app.v2\", \"atakuser\", dhgmAutoKey, false);\n"
    "                promptForKey(context, ksl);\n"
    "            }"
)
if "dhgmAutoKey" in src:
    print("  ✓ auto-key უკვე დადებულია")
elif needle in src:
    src = src.replace(needle, replacement, 1)
    open(p, "w", encoding="utf-8").write(src)
    print("  ✓ encryption passphrase → auto-key (first-run დიალოგი მოიხსნა)")
else:
    print("  ⚠ changeKeyImpl(context, true, ksl) ვერ ვიპოვე — upstream შეიცვალა, გადაამოწმე:", p)
PY

echo "== 8/9: mount deadlock fix (FileSystemUtils, ATAK PR#329) =="
FSU=atak/takkernel/engine/src/main/java/com/atakmap/coremap/filesystem/FileSystemUtils.java
if [ -f "$FSU" ]; then
  python3 tools/fix-mount-deadlock.py "$FSU"
else
  echo "  ⚠ FileSystemUtils.java ვერ ვიპოვე — გამოტოვებულია"
fi

echo "== 9/9: ზედმეტი settings-პარამეტრების მოჭრა (DHGM LAN/GCS ნაკადი — TAK server არ სჭირდება) =="
NETPREF=atak/atak/ATAK/app/src/main/res/xml/network_preferences.xml
if [ -f "$NETPREF" ]; then
  # serverConnections (TAK Servers/streaming) + tadiljSettings (TADIL-J datalink) —
  # DHGM LAN multicast-ს (networkSettings, 239.2.3.1:6969) იყენებს, არა TAK server-ს.
  python3 tools/hide-preferences.py "$NETPREF" serverConnections tadiljSettings
else
  echo "  ⚠ network_preferences.xml ვერ მოიძებნა — გამოტოვებულია"
fi
# DHGM-ს settings-ის top-level ეკრანი: SettingsActivity-ის getDefaultHomePreferences()
# legacy_settings flag-ზეა დამოკიდებული — default (false) → MyPreferenceFragment
# (my_preferences.xml), legacy → MainPreferencesFragment (main_preferences.xml).
# ორივე ფაილს ვჭრით, რომ flag-ის მდგომარეობის მიუხედავად entry-ები არ ჩანდეს.
#
# my_preferences.xml (რეალურად რენდერდება default-ზე): networkPrefs — Network entry,
# რომლის შიგნიდან TAK „SERVER CONNECTIONS" ეკრანი ახალ Android-ზე იკრაშება;
# accounts — TAK server auth; legacyPrefs — legacy ეკრანის (main_preferences)
# შესასვლელი, სადაც Bluetooth/Accounts-ია → მოჭრით ამ crash/BT-გზასაც ვკეტავთ.
MYPREF=atak/atak/ATAK/app/src/main/res/xml/my_preferences.xml
if [ -f "$MYPREF" ]; then
  python3 tools/hide-preferences.py "$MYPREF" networkPrefs accounts legacyPrefs
else
  echo "  ⚠ my_preferences.xml ვერ მოიძებნა — გამოტოვებულია"
fi
MAINPREF=atak/atak/ATAK/app/src/main/res/xml/main_preferences.xml
if [ -f "$MAINPREF" ]; then
  # legacy layout-ის (legacy_settings=true) fallback — იგივე entry-ები:
  # settingsPref (Network → TAK SERVER CONNECTIONS crash), bluetoothPref (BT GPS puck),
  # atakAccounts (TAK server auth). DHGM LAN multicast-ს იყენებს, ეს არცერთი არ სჭირდება.
  python3 tools/hide-preferences.py "$MAINPREF" bluetoothPref atakAccounts settingsPref
else
  echo "  ⚠ main_preferences.xml ვერ მოიძებნა — გამოტოვებულია"
fi

# ⚠️ core უპირობოდ ეძებს ზემოთ მოჭრილ key-ებს (findPreference(...).setOn…) → NPE
# პარამეტრების გახსნისას. guard მათზე მიუმაგრებელ stub Preference-ს აბრუნებს.
APF=atak/atak/ATAK/app/src/main/java/com/atakmap/android/preference/AtakPreferenceFragment.java
python3 tools/patch-pref-trim-guard.py "$APF"

echo "✓ overlay დადებულია"
