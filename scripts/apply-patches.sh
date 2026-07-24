#!/usr/bin/env bash
# Install the from-scratch horizontal tab-scrolling rewrite into a Chromium 'src'
# checkout: drop the new source files in as an overlay, then run the anchored
# integrator to wire them into the build, the region view, and the feature flags.
#
#   Usage: CHROMIUM_SRC=/path/to/src ./apply-patches.sh
set -euo pipefail

SRC="${CHROMIUM_SRC:-$PWD}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$SRC"
[ -f "chrome/browser/ui/tabs/features.cc" ] || {
  echo "error: not a Chromium src dir (set CHROMIUM_SRC=/path/to/src)"; exit 1; }

echo ">> overlaying new source files"
# Self-authored files that don't exist upstream, copied verbatim into the tree.
(cd "$HERE/src" && find . -type f) | while read -r rel; do
  dest="$SRC/${rel#./}"
  mkdir -p "$(dirname "$dest")"
  cp "$HERE/src/${rel#./}" "$dest"
  echo "   + ${rel#./}"
done

echo ">> wiring integration (anchored edits)"
CHROMIUM_SRC="$SRC" python3 "$HERE/integration/integrate.py"

echo ">> done. Configure with config/args.gn, then build 'chrome'."
echo "   The feature ships ENABLED in this fork. To A/B test it:"
echo "     --enable-features=HorizontalTabScrolling  /  --disable-features=HorizontalTabScrolling"
