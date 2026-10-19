#!/bin/bash
# Запуск на macOS без сборки. by lozanovvv_
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
python app.py
