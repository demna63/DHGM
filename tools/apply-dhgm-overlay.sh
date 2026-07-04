#!/usr/bin/env bash
# DHGM overlay-ის დადება ATAK-CIV წყაროზე (იდემპოტენტური).
# GCS-ის tools/apply-qgc-patches.sh-ის ანალოგი: upstream ფაილები არ იცვლება,
# გარდა ქირურგიული, აღნიშნული sed-ებისა.
set -euo pipefail
cd "$(dirname "$0")/.."

[ -d atak/atak ] || { echo "✗ atak/ არ არის დაკლონილი — ჯერ tools/bootstrap-atak.sh"; exit 1; }

if [ -f tools/gen-icons.py ] && [ -f custom/brand/dhgm-logo.svg ]; then
  echo "== 1/7: brand assets (SVG → PNG) =="
  pip install -q cairosvg pillow 2>/dev/null || true
  python3 tools/gen-icons.py || echo "  ⚠ gen-icons.py ვერ გაეშვა (cairosvg/pillow?)"
fi

echo "== 2/7: overlay ფაილების კოპირება (custom/overlay/ → atak/) =="
rsync -a --out-format="  + %n" custom/overlay/atak/ atak/atak/

echo "== 3/7: branding (app label ATAK → DHGM) =="
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

echo "== 4/7: DEVELOPER BUILD წარწერის მოხსნა (civSdk build type) =="
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

echo "== 5/7: package identity (applicationId + APK სახელი) =="
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

echo "== 6/7: სისტემური ზოლების ფერი (status/navigation bar) =="
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

echo "== 7/7: encryption passphrase auto-key (first-run დიალოგის მოხსნა) =="
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

echo "✓ overlay დადებულია"
