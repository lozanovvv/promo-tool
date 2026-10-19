Promo Tool - замена надписи сверху (RMRP), названия сервера, промокода и цвета в заставке (шаблон KLA4_tver.mov, 2560x1440).

Windows: run.bat (без сборки) или build.bat -> dist\PromoTool.exe
macOS:   run_mac.command (без сборки) или build_mac.command -> dist/PromoTool.dmg и .app
         Первый раз: правый клик -> Открыть. Нужен Python 3.10+ с tkinter (python.org).
CLI: python3 app.py in.mov out.mov --brand RMRP --server НАЗВАНИЕ --promo КОД --hue 222
by lozanovvv_

ГОТОВЫЕ .exe И .dmg (без установки Python):
1. Создай на github.com пустой репозиторий и загрузи в него ВСЁ содержимое этой папки (включая скрытую папку .github).
2. Открой вкладку Actions -> build -> дождись зелёной галочки (5-10 минут).
3. Внизу страницы запуска, в разделе Artifacts, скачай:
   PromoTool-Windows-exe (PromoTool.exe), PromoTool-Mac-Apple-Silicon-dmg (M1/M2/M3/M4), PromoTool-Mac-Intel-dmg.
Mac: первый запуск - правый клик -> Открыть (приложение не подписано).
