#!/usr/bin/env bash
# DHGM signing keystore-ის გენერაცია (debug + release ერთ keystore-ში, ორი alias).
# ⚠️ custom/keys/ gitignore-შია — keystore და პაროლები repo-ში არასდროს ხვდება!
#    release keystore დაკარგვა = აპის განახლების შეუძლებლობა. შეინახე backup უსაფრთხოდ.
set -euo pipefail
cd "$(dirname "$0")/.."

KEYS=custom/keys
KS="$KEYS/dhgm.keystore"
PROPS="$KEYS/keystore.properties"

if [ -f "$KS" ]; then
  echo "✓ $KS უკვე არსებობს — ხელახლა არ ვაგენერირებ"
  exit 0
fi

# macOS-ის /usr/bin/keytool stub-ს ვერიდებით — რეალურ JDK-ს ვეძებთ
KEYTOOL=""
for cand in /opt/homebrew/opt/openjdk@17/bin/keytool /opt/homebrew/opt/openjdk/bin/keytool keytool; do
  if "$cand" -help >/dev/null 2>&1; then KEYTOOL="$cand"; break; fi
done
[ -n "$KEYTOOL" ] || { echo "✗ მუშა keytool ვერ ვიპოვე — brew install openjdk@17"; exit 1; }

mkdir -p "$KEYS"
PASS=$(openssl rand -hex 16)

for alias in dhgm-debug dhgm-release; do
  "$KEYTOOL" -genkeypair -keystore "$KS" -alias "$alias" \
    -keyalg RSA -keysize 4096 -validity 10950 \
    -storepass "$PASS" -keypass "$PASS" \
    -dname "CN=DroneHub Georgia, OU=DHGM, O=DroneHub Georgia, L=Tbilisi, C=GE" >/dev/null
  echo "  ✓ alias: $alias"
done

cat > "$PROPS" <<EOF
# DHGM signing — local.properties-ში ჩასაწერი მნიშვნელობები (გზები repo root-იდან)
takDebugKeyFile=../../custom/keys/dhgm.keystore
takDebugKeyFilePassword=$PASS
takDebugKeyAlias=dhgm-debug
takDebugKeyPassword=$PASS
takReleaseKeyFile=../../custom/keys/dhgm.keystore
takReleaseKeyFilePassword=$PASS
takReleaseKeyAlias=dhgm-release
takReleaseKeyPassword=$PASS
EOF
chmod 600 "$PROPS" "$KS"

echo "✓ keystore: $KS"
echo "✓ პაროლები/პარამეტრები: $PROPS (chmod 600)"
echo
echo "GitHub Actions-სთვის (repo Settings → Secrets):"
echo "  DHGM_KEYSTORE_B64:  base64 < $KS | pbcopy   ← ბუფერშია"
echo "  DHGM_KEYSTORE_PASS: (პაროლი $PROPS-დან)"
