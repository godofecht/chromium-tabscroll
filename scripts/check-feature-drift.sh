#!/usr/bin/env bash
# Best-effort check that tracked upstream feature names still exist in a checkout.
set -euo pipefail

ROOT="${1:-$PWD}"
features=(
  OptimizationGuideModelDownloading
  OptimizationGuideOnDeviceModel
  Compose
  TabOrganization
  HistorySearch
  LensOverlay
)

for feature in "${features[@]}"; do
  if rg -q "$feature" "$ROOT" 2>/dev/null; then
    echo "OK: $feature"
  else
    echo "WARN: feature string not found: $feature"
  fi
done
