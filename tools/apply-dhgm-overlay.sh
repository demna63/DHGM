#!/usr/bin/env bash
# DHGM overlay-ის დადება ATAK-CIV წყაროზე (იდემპოტენტური).
# GCS-ის tools/apply-qgc-patches.sh-ის ანალოგი: upstream ფაილები არ იცვლება,
# გარდა ქირურგიული, აღნიშნული sed-ებისა.
set -euo pipefail
cd "$(dirname "$0")/.."

[ -d atak/atak ] || { echo "✗ atak/ არ არის დაკლონილი — ჯერ tools/bootstrap-atak.sh"; exit 1; }

echo "== 1/2: overlay ფაილების კოპირება (custom/overlay/ → atak/) =="
rsync -a --out-format="  + %n" custom/overlay/atak/ atak/atak/

echo "== 2/2: branding (app label ATAK → DHGM) =="
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

echo "== 3/3: DEVELOPER BUILD წარწერის მოხსნა (civSdk build type) =="
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

echo "✓ overlay დადებულია"
