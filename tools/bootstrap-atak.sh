#!/usr/bin/env bash
# DHGM — ATAK-CIV წყაროს მოზიდვა (ფაზა 1-ის საწყისი ნაბიჯი).
# ⚠️ დიდი repo-ა (git-lfs, submodules, ~10+ GB build-ით). გაუშვი მხოლოდ მაშინ,
#    როცა ფაზა 1-ზე გადახვალ. ფაზა 0-ს (bridge + stock ATAK-CIV APK) ეს არ სჭირდება.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "== წინაპირობების შემოწმება =="
missing=0
for tool in git git-lfs; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "  ✗ $tool არ არის — დააინსტალირე (brew install $tool)"
    missing=1
  else
    echo "  ✓ $tool"
  fi
done
# macOS-ზე /usr/bin/java stub ყოველთვის არსებობს — რეალურ გაშვებადობას ვამოწმებთ
if java -version >/dev/null 2>&1; then
  echo "  ✓ java ($(java -version 2>&1 | head -1))"
else
  echo "  ✗ Java Runtime არ არის — დააინსტალირე JDK 17 (brew install --cask temurin@17)"
  missing=1
fi
if [ ! -d "$HOME/Library/Android/sdk" ] && [ -z "${ANDROID_HOME:-}" ]; then
  echo "  ✗ Android SDK არ ჩანს — დააინსტალირე Android Studio (NDK-თან ერთად)"
  missing=1
else
  echo "  ✓ Android SDK"
fi
[ "$missing" -eq 1 ] && { echo; echo "ჯერ წინაპირობები შეავსე, მერე ხელახლა გაუშვი."; exit 1; }

echo
echo "== ATAK-CIV კლონირება (atak/ — gitignore-შია, DroneHub-GCS-ის qgroundcontrol/-ის ანალოგიით) =="
if [ ! -d atak ]; then
  git lfs install
  git clone --recurse-submodules \
    https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV.git atak
else
  echo "  atak/ უკვე არსებობს — განახლება:"
  git -C atak pull --recurse-submodules
fi

echo
echo "== შემდეგი ნაბიჯები =="
echo "  1. წაიკითხე atak/BUILDING.md — ზუსტი NDK/SDK ვერსიები იქაა."
echo "  2. LICENSE გადაამოწმე atak/-ში (GPL-ტიპის — fork/rebrand ნებადართულია, source-გახსნით)."
echo "  3. საკუთარი signing key შექმენი — ჩვენი build-ის ATAK ჩვენივე ხელმოწერის"
echo "     plugin-ებს ჩატვირთავს (Play Store ATAK მხოლოდ TAK.gov-ის ხელმოწერილს იღებს)."
echo "  4. ქართული ლოკალიზაცია: atak/atak/ATAK/app/src/main/res/values-ka/strings.xml"
