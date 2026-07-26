#!/usr/bin/env bash
# Print composable Chromium runtime profiles as a flat argv list.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ "$#" -eq 0 ]; then
  set -- base performance privacy no-ai
fi

enable_features=""
disable_features=""
other_flags=()

append_csv_unique() {
  local current="$1"
  local value="$2"
  local next
  local old_ifs

  if [ -z "$value" ]; then
    printf '%s' "$current"
    return
  fi

  old_ifs="$IFS"
  IFS=,
  for next in $value; do
    case ",$current," in
      *,"$next",*) ;;
      *)
        if [ -z "$current" ]; then
          current="$next"
        else
          current="$current,$next"
        fi
        ;;
    esac
  done
  IFS="$old_ifs"
  printf '%s' "$current"
}

for profile in "$@"; do
  file="$HERE/config/runtime-flags/$profile.flags"
  [ -f "$file" ] || {
    echo "error: unknown runtime profile: $profile" >&2
    exit 1
  }
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      ""|\#*) continue ;;
      --enable-features=*)
        enable_features="$(append_csv_unique "$enable_features" "${line#--enable-features=}")"
        ;;
      --disable-features=*)
        disable_features="$(append_csv_unique "$disable_features" "${line#--disable-features=}")"
        ;;
      *)
        seen=0
        if [ "${#other_flags[@]}" -gt 0 ]; then
          for flag in "${other_flags[@]}"; do
            if [ "$flag" = "$line" ]; then
              seen=1
              break
            fi
          done
        fi
        [ "$seen" -eq 1 ] || other_flags+=("$line")
        ;;
    esac
  done < "$file"
done

if [ "${#other_flags[@]}" -gt 0 ]; then
  for flag in "${other_flags[@]}"; do
    printf '%s\n' "$flag"
  done
fi
[ -z "$enable_features" ] || printf '%s\n' "--enable-features=$enable_features"
[ -z "$disable_features" ] || printf '%s\n' "--disable-features=$disable_features"
