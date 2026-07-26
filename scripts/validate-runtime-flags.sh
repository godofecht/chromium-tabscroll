#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail=0

for file in "$HERE"/config/runtime-flags/*.flags; do
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      ""|\#*) continue ;;
    esac
    if [[ "$line" != --* ]]; then
      echo "bad flag in ${file#$HERE/}: $line" >&2
      fail=1
    fi
    if [[ "$line" == *" "* ]]; then
      echo "spaces are not allowed in ${file#$HERE/}: $line" >&2
      fail=1
    fi
  done < "$file"
done

"$HERE/scripts/print-flags.sh" base performance privacy no-ai >/dev/null
"$HERE/scripts/print-flags.sh" compatibility >/dev/null
"$HERE/scripts/print-flags.sh" adblock-friendly >/dev/null

exit "$fail"
