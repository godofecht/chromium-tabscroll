#!/usr/bin/env bash
# Launch a Chromium binary with the toolkit's composable runtime profiles.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHROME="${CHROME:-chrome}"
PROFILE_DIR="${PROFILE_DIR:-$PWD/tabscroll-profile}"

if [ "$#" -gt 0 ] && [ "$1" = "--profiles" ]; then
  shift
  profiles=()
  while [ "$#" -gt 0 ] && [ "$1" != "--" ]; do
    profiles+=("$1")
    shift
  done
  [ "$#" -eq 0 ] || shift
else
  profiles=(base performance privacy no-ai)
fi

flags=()
while IFS= read -r line || [ -n "$line" ]; do
  [ -z "$line" ] || flags+=("$line")
done < <("$HERE/scripts/print-flags.sh" "${profiles[@]}")

exec "$CHROME" --user-data-dir="$PROFILE_DIR" "${flags[@]}" "$@"
