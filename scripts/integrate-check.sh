#!/usr/bin/env bash
# Fast, free anchor-drift check. Fetches only the files the integrator edits from
# the chromium mirror at HEAD, runs integrate.py against them, and asserts the
# edits landed. Catches an upstream roll moving an anchor before a multi-hour
# build ever starts. Needs `gh` (authenticated) and python3; no checkout.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REF="${1:-main}"                       # branch/tag/sha to check against
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

FILES=(
  "chrome/browser/ui/tabs/features.h"
  "chrome/browser/ui/tabs/features.cc"
  "chrome/browser/ui/BUILD.gn"
  "chrome/browser/ui/views/frame/horizontal_tab_strip_region_view.h"
  "chrome/browser/ui/views/frame/horizontal_tab_strip_region_view.cc"
)

echo ">> fetching ${#FILES[@]} target files at $REF"
for f in "${FILES[@]}"; do
  mkdir -p "$WORK/$(dirname "$f")"
  gh api "repos/chromium/chromium/contents/$f?ref=$REF" \
     -H "Accept: application/vnd.github.raw" > "$WORK/$f"
done

# The overlay files must also be present for a realistic run (integrate.py only
# edits existing files, but apply-patches.sh copies these; mirror that here).
(cd "$HERE/src" && find . -type f) | while read -r rel; do
  mkdir -p "$WORK/$(dirname "${rel#./}")"
  cp "$HERE/src/${rel#./}" "$WORK/${rel#./}"
done

echo ">> running integrator"
CHROMIUM_SRC="$WORK" python3 "$HERE/integration/integrate.py"

echo ">> asserting edits landed"
fail=0
assert() { grep -q "$2" "$WORK/$1" || { echo "MISSING in $1: $2"; fail=1; }; }
assert "chrome/browser/ui/tabs/features.h"  "kHorizontalTabScrolling"
assert "chrome/browser/ui/tabs/features.cc" "BASE_FEATURE(kHorizontalTabScrolling"
assert "chrome/browser/ui/BUILD.gn"         "horizontal_tab_scroll_container.cc"
assert "chrome/browser/ui/views/frame/horizontal_tab_strip_region_view.h"  "scroll_container_"
assert "chrome/browser/ui/views/frame/horizontal_tab_strip_region_view.cc" "HorizontalTabScrollContainer>"
assert "chrome/browser/ui/views/frame/horizontal_tab_strip_region_view.cc" "SetAvailableWidthCallback"
assert "chrome/browser/ui/views/frame/horizontal_tab_strip_region_view.cc" "children.emplace_back(scroll_container_.get())"

# Idempotency: a second run must not error or double-apply.
CHROMIUM_SRC="$WORK" python3 "$HERE/integration/integrate.py" >/dev/null

if [ "$fail" -ne 0 ]; then
  echo ">> ANCHOR DRIFT: upstream moved. Update integration/integrate.py anchors." >&2
  exit 1
fi
echo ">> OK: all anchors resolved and edits applied cleanly."
