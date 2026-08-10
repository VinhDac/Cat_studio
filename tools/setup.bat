@echo off
REM Dựng môi trường từ đầu. Chạy MỘT lần sau khi clone.
cd /d "%~dp0.."

REM venv RIÊNG, không cài vào Python global: gói `quantconnect-stubs` (nếu máy có)
REM chiếm namespace `Microsoft` và giết pywebview ngay lúc khởi động.
if not exist ".venv" python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\pip.exe install -r requirements.txt

cd webui
call npm install
call npm run build
cd ..

echo.
echo Xong. Chay app:  tools\chay.bat
