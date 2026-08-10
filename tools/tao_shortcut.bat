@echo off
REM Tạo shortcut "Cat Studio" ra Desktop và cạnh mã nguồn.
REM Chạy bằng pythonw.exe nên KHÔNG hiện cửa sổ console đen lúc mở app.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tao_shortcut.ps1"
pause
