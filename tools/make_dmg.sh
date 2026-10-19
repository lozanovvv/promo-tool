#!/bin/bash
# Красивый установочный .dmg: тёмный фон, стрелка, ярлык Applications. by lozanovvv_
# Использование: tools/make_dmg.sh путь/PromoTool.app путь/PromoTool.dmg
APP="$1"; OUT="$2"; VOL="PromoTool"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
[ -d "$APP" ] || { echo "Нет $APP"; exit 1; }
TMP="$(mktemp -d)"; SRC="$TMP/src"; RW="$TMP/rw.dmg"
mkdir -p "$SRC/.background"
cp -R "$APP" "$SRC/PromoTool.app"
ln -s /Applications "$SRC/Applications"
# фон: обычный + retina в одном файле
tiffutil -cathidpicheck "$HERE/assets/dmg_bg.png" "$HERE/assets/dmg_bg@2x.png" -out "$SRC/.background/bg.tiff" 2>/dev/null \
  || cp "$HERE/assets/dmg_bg.png" "$SRC/.background/bg.tiff"
[ -f "$HERE/assets/icon.icns" ] && cp "$HERE/assets/icon.icns" "$SRC/.VolumeIcon.icns"
# закрываем старый смонтированный том, если остался
hdiutil detach "/Volumes/$VOL" -force >/dev/null 2>&1
SIZE=$(( $(du -sm "$SRC" | cut -f1) + 40 ))
hdiutil create -srcfolder "$SRC" -volname "$VOL" -fs HFS+ -format UDRW -size ${SIZE}m -ov "$RW" >/dev/null || exit 1
DEV=$(hdiutil attach -readwrite -noverify -noautoopen "$RW" | grep -E '^/dev/' | head -1 | awk '{print $1}')
sleep 2
[ -f "$SRC/.VolumeIcon.icns" ] && SetFile -a C "/Volumes/$VOL" 2>/dev/null
osascript <<EOF || echo "Не удалось оформить окно диска (разреши Terminal управлять Finder) — .dmg всё равно собран"
tell application "Finder"
  tell disk "$VOL"
    open
    set current view of container window to icon view
    set toolbar visible of container window to false
    set statusbar visible of container window to false
    set the bounds of container window to {200, 120, 860, 520}
    set opts to the icon view options of container window
    set arrangement of opts to not arranged
    set icon size of opts to 128
    set text size of opts to 13
    set background picture of opts to file ".background:bg.tiff"
    set position of item "PromoTool.app" of container window to {180, 190}
    set position of item "Applications" of container window to {480, 190}
    update without registering applications
    delay 2
    close
  end tell
end tell
EOF
sync; sleep 1
hdiutil detach "$DEV" >/dev/null 2>&1 || hdiutil detach "$DEV" -force >/dev/null
mkdir -p "$(dirname "$OUT")"
hdiutil convert "$RW" -format UDZO -imagekey zlib-level=9 -ov -o "$OUT" >/dev/null || exit 1
rm -rf "$TMP"
echo "Готово: $OUT"
