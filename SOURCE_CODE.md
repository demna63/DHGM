# DHGM — წყაროს კოდის მიღება (GPL)

DHGM არის **ATAK-CIV-ის პარივაცია (derivative work)** GPL-3.0 ლიცენზიით.
ბინარის (APK) გავრცელებისას უნდა მიეწოდოს შესაბამისი წყაროს კოდი ან წერილობითი
შეთავაზება მის მიღებაზე.

## სრული წყარო (რეკომენდებული)

1. **DHGM ცვლილებები** — ეს repository:
   ```
   git clone https://github.com/demna63/DHGM.git
   ```

2. **ATAK-CIV ბაზა** — pinned tag (იხ. `ATAK_REF` workflow-ში):
   ```
   git clone --branch 4.6.0.5 --recurse-submodules \
     https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV.git atak
   cd DHGM && ./tools/apply-dhgm-overlay.sh
   ```

3. **APK აწყობა** — Linux-ზე (იხ. `README.md`, `.github/workflows/build-dhgm.yml`).
   macOS-ზე native build არ მუშაობს; გამოიყენეთ GitHub Actions artifact.

## GitHub Releases

თაგებით (`v*`) გამოქვეყნებულ release-ებზე APK artifact ერთვება.
წყაროსთან შესაბამისი commit იგივე tag-ზეა მიბმული.

## კონტაქტი

წყაროს მიღების მოთხოვნისთვის: GitHub Issues — https://github.com/demna63/DHGM/issues
