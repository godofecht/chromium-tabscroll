#!/usr/bin/env bash
# Free up ~30 GB on a GitHub-hosted ubuntu runner so a Chromium checkout fits.
# The default image ships large SDKs we don't need for a Chromium build.
set -euo pipefail
echo "disk before:"; df -h /
sudo rm -rf /usr/share/dotnet || true
sudo rm -rf /usr/local/lib/android || true
sudo rm -rf /opt/ghc || true
sudo rm -rf /opt/hostedtoolcache/CodeQL || true
sudo rm -rf /usr/local/.ghcup || true
sudo rm -rf /usr/lib/jvm || true
sudo rm -rf /usr/share/swift || true
sudo docker image prune --all --force || true
sudo apt-get clean || true
echo "disk after:"; df -h /
