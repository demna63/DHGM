#!/usr/bin/env bash
# DHGM release — ერთ ბრძანებით: ტესტებ → VERSION → commit → tag → push.
# tag-ის push-ზე CI (build-dhgm.yml) აწყობს app + plugin APK-ებს და ქმნის GitHub Release-ს.
#
#   tools/release.sh 0.3.1          # ინტერაქტიულ დამოწმებით
#   tools/release.sh 0.3.1 --yes    # დამოწმების გარეშე
set -euo pipefail
cd "$(dirname "$0")/.."

NEW="${1:-}"
YES="${2:-}"
die() { echo "✗ $*" >&2; exit 1; }

[[ "$NEW" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]] || die "გამოყენება: tools/release.sh MAJOR.MINOR.PATCH [--yes]"
(( BASH_REMATCH[2] <= 99 && BASH_REMATCH[3] <= 99 )) || die "MINOR/PATCH ≤ 99 (plugin versionCode = M*10000+m*100+p)"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[[ "$BRANCH" == "main" ]] || die "release მხოლოდ main-იდან (ახლა: $BRANCH)"
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || die "working tree სუფთა არ არის — commit/stash ჯერ"

git fetch --quiet --tags origin
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || die "main origin/main-ს არ ემთხვევა — git pull ჯერ"
git rev-parse -q --verify "refs/tags/v$NEW" >/dev/null && die "tag v$NEW უკვე არსებობს"

LAST="$(git tag --list 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname | head -1 | sed 's/^v//')"
if [[ -n "$LAST" ]]; then
  HIGHEST="$(printf '%s\n%s\n' "$LAST" "$NEW" | sort -V | tail -1)"
  [[ "$HIGHEST" == "$NEW" && "$LAST" != "$NEW" ]] || die "v$NEW ≤ ბოლო release v$LAST"
fi

echo "== ტესტებ =="
(cd bridge && python3 -m unittest discover -s tests)
if command -v javac >/dev/null; then
  bash tools/run-plugin-jvm-tests.sh
else
  echo "⚠ javac არ მოიძებნა — plugin JVM ტესტებ CI-ზე ეშვევიან"
fi

echo
echo "release: v${LAST:-—} → v$NEW   (commit + tag + push origin main v$NEW)"
if [[ "$YES" != "--yes" ]]; then
  read -r -p "გავაგრძელო? [y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]] || die "გაუქმდა"
fi

echo "$NEW" > VERSION
git add VERSION
git commit -m "chore: release v$NEW"
git tag -a "v$NEW" -m "DHGM v$NEW"
git push origin main
git push origin "v$NEW"

echo "✓ v$NEW push-და → https://github.com/demna63/DHGM/actions"
