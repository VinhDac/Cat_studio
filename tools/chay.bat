@echo off
REM Mở app. Sửa giao diện xong phải build lại (tools\build_ui.bat) mới thấy đổi.
cd /d "%~dp0.."
.venv\Scripts\python.exe app_web.py
