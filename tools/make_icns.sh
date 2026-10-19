#!/bin/bash
# Делает assets/icon.icns из assets/icon.png (только macOS). by lozanovvv_
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
SET="$(mktemp -d)/icon.iconset"
mkdir -p "$SET"
for s in 16 32 128 256 512; do
  sips -z $s $s "$HERE/assets/icon.png" --out "$SET/icon_${s}x${s}.png" >/dev/null
  sips -z $((s*2)) $((s*2)) "$HERE/assets/icon.png" --out "$SET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$SET" -o "$HERE/assets/icon.icns"
