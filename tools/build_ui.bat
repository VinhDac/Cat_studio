@echo off
REM Build lại giao diện web. app_web.py chỉ nạp `webui\dist`, không nạp mã nguồn.
cd /d "%~dp0..\webui"
call npm run build
