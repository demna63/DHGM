#!/usr/bin/env python3
"""APK-ის ხელმოწერის შემოწმება — „ნამდვილად DHGM-ის build-ია?"

Play Protect self-signed APK-ზე გაფრთხილებას აჩვენებს („უცნობ დეველოპერი"), და ეს
მხოლოდ გაფრთხილებაა — ავთენტურობას ის **არ** ამოწმებს. ამიტომ ყოველ release-ს ვაქვეყნებთ:

  * APK-ის SHA-256 (ფაილ არ შეცვლილა)
  * ხელმომწერ სერტიფიკატის SHA-256 (იგივე DHGM-ის key-ია)

    python3 tools/verify-apk.py DHGM-0.4.1-app.apk        # ორივეს ბეჭდავს + ადარებს
    python3 tools/verify-apk.py --print-only file.apk     # მხოლოდ ბეჭდავს (ახალ key-ზე)

exit 1 — თუ სერტიფიკატი მოსალოდნელს არ ემთხვევა (ე.ი. APK სხვა key-ითაა ხელმოწერილ).
საჭიროებს `openssl`-ს (macOS/Linux-ზე default). იხ. docs/distribution.md.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import zipfile

#: DHGM-ის ორ signing key — ერთ keystore-ში, ორ alias-ზე (public ინფო, შედარებისთვისაა).
#: ორივეს subject: CN=DroneHub Georgia, O=DroneHub Georgia, OU=DHGM, L=Tbilisi, C=GE
#:
#: ATAK-ის `civSdk` ვარიანტ takDebugKey*-ს იყენებს, plugin-ის release build კი
#: takReleaseKey*-ს — ე.ი. app და plugin **სხვადასხვა key-ითაა** ხელმოწერილ და ასეა
#: v0.2.9-დან. app-ის key-ის შეცვლა = ყველა მომხმარებელს reinstall (signature mismatch,
#: ATAK-ის მონაცემებ იკარგება), ამიტომ ამ ორს შეგნებულად ვინარჩუნებთ. იხ. docs/distribution.md
APP_CERT_SHA256 = "C2B69E87A8F024875871BD76F4CA71150987C19F6F39D51E184769CEE6B96A2C"
PLUGIN_CERT_SHA256 = "C0FE3B24250D78FB6CDB000623D84C446444FFC01E4D5A2A435CDC041675EA47"

KEY_LABEL = {
    APP_CERT_SHA256: "app key (keystore alias: dhgm-debug — ATAK civSdk)",
    PLUGIN_CERT_SHA256: "plugin key (keystore alias: dhgm-release)",
}


def expected_cert(path: str) -> tuple[str | None, str]:
    """ფაილის სახელიდან → (მოსალოდნელ cert, არტეფაქტის როლ).

    CI-ის „Stage release assets" ნაბიჯ სახელებს დეტერმინისტულად არქმევს
    (`DHGM-<ver>-app.apk`, `DHGM-Drones-<ver>.apk`), ე.ი. როლ სახელით იკითხება.
    უცნობ სახელზე (ლოკალურ build) კონკრეტულ key-ს არ ვითხოვთ — მხოლოდ იმას,
    რომ DHGM-ის ორიდან ერთ-ერთი იყოს.
    """
    base = os.path.basename(path).lower()
    if "drones" in base or "plugin" in base:
        return PLUGIN_CERT_SHA256, "plugin"
    if base.endswith("-app.apk"):
        return APP_CERT_SHA256, "app"
    return None, "უცნობ"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def signer_cert(path: str) -> tuple[str, str]:
    """→ (cert SHA-256, subject). v1 (JAR) ხელმოწერის PKCS#7-იდან."""
    with zipfile.ZipFile(path) as z:
        blocks = [n for n in z.namelist()
                  if n.upper().startswith("META-INF/")
                  and n.upper().endswith((".RSA", ".DSA", ".EC"))]
        if not blocks:
            raise SystemExit("✗ v1 ხელმოწერა ვერ ვიპოვე (META-INF/*.RSA) — APK ხელმოუწერელია?")
        der = z.read(sorted(blocks)[0])

    pem = subprocess.run(["openssl", "pkcs7", "-inform", "DER", "-print_certs"],
                         input=der, capture_output=True)
    if pem.returncode != 0:
        raise SystemExit("✗ openssl pkcs7 ვერ წაიკითხა: %s" % pem.stderr.decode()[:200])
    info = subprocess.run(["openssl", "x509", "-noout", "-fingerprint", "-sha256", "-subject"],
                          input=pem.stdout, capture_output=True)
    if info.returncode != 0:
        raise SystemExit("✗ openssl x509 ვერ წაიკითხა: %s" % info.stderr.decode()[:200])

    fp, subject = "", ""
    for line in info.stdout.decode("utf-8", "replace").splitlines():
        if line.startswith("sha256 Fingerprint="):
            fp = line.split("=", 1)[1].replace(":", "").strip().upper()
        elif line.startswith("subject="):
            subject = line.split("=", 1)[1].strip()
    return fp, subject


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("apk", nargs="+")
    p.add_argument("--print-only", action="store_true",
                   help="მხოლოდ ბეჭდვა, შედარების გარეშე (key-ის შეცვლისას)")
    args = p.parse_args()

    bad = 0
    for apk in args.apk:
        fp, subject = signer_cert(apk)
        print("%s\n  SHA-256 (ფაილ): %s\n  ხელმომწერი:     %s\n  cert SHA-256:   %s"
              % (apk, sha256_file(apk), subject or "—", fp))
        if args.print_only:
            continue
        want, role = expected_cert(apk)
        if want is None:
            if fp in KEY_LABEL:
                print("  ✓ DHGM-ის %s" % KEY_LABEL[fp])
            else:
                print("  ✗ სერტიფიკატი არცერთ DHGM key-ს არ ემთხვევა", file=sys.stderr)
                bad += 1
        elif fp != want:
            print("  ✗ %s-ის key არ ემთხვევა (მოსალოდნელი %s — %s)"
                  % (role, want, KEY_LABEL[want]), file=sys.stderr)
            bad += 1
        else:
            print("  ✓ DHGM-ის %s" % KEY_LABEL[fp])
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
