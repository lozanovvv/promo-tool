#!/bin/bash
# Сборка PromoTool.app и красивого PromoTool.dmg на macOS. by lozanovvv_
cd "$(dirname "$0")"
PY=$(command -v python3)
if [ -z "$PY" ] || ! "$PY" -c "import tkinter, sys; assert sys.version_info >= (3, 10)" 2>/dev/null; then
  echo "Нужен Python 3.10+ с tkinter."
  echo "Если Python из Homebrew:  brew install python-tk"
  echo "Или установщик с https://www.python.org/downloads/macos/"
  read -p "Enter для выхода"; exit 1
fi
"$PY" -m venv .venv || exit 1
source .venv/bin/activate
pip install -r requirements.txt || { read -p "Ошибка установки. Enter для выхода"; exit 1; }
bash tools/make_icns.sh
rm -rf build dist
pyinstaller --noconfirm --windowed --name PromoTool --icon assets/icon.icns --osx-bundle-identifier ru.lozanovvv.promotool --add-data "assets:assets" --collect-all imageio_ffmpeg --collect-all customtkinter app.py || { read -p "Ошибка сборки. Enter для выхода"; exit 1; }
mkdir -p ../app
bash tools/make_dmg.sh dist/PromoTool.app ../app/PromoTool.dmg
echo
echo "Готово: папка app → PromoTool.dmg"
open ../app
read -p "Enter для выхода"
