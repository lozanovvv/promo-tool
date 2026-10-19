@echo off
REM Сборка в один .exe (нужен установленный Python 3.10+). by lozanovvv_
py -m pip install -r requirements.txt
py -m PyInstaller --noconfirm --onefile --windowed --name PromoTool --icon assets\icon.ico --add-data "assets;assets" --collect-all imageio_ffmpeg --collect-all customtkinter app.py
if not exist ..\app mkdir ..\app
copy /Y dist\PromoTool.exe ..\app\PromoTool.exe
echo.
echo Готово: папка app\PromoTool.exe
pause
