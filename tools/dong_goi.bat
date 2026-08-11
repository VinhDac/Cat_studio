@echo off
REM ============================================================
REM  Dong goi Cat_Studio -> dist\Cat_Studio\ + Cat_Studio-windows.zip
REM
REM  Chay tu THU MUC GOC:   tools\dong_goi.bat
REM
REM  DUNG PYTHON TRONG .venv, khong dung Python global: goi
REM  quantconnect-stubs o Python global ship mot thu muc "Microsoft" chiem
REM  namespace .NET. Ma nguon da co _uu_tien_namespace_dotnet() de chua, nhung
REM  dong goi bang moi truong sach thi goi nhe hon va khong keo theo rac.
REM
REM  GIU --onedir (khai trong Cat_Studio.spec): ban gop-1-file giai nen ca cay
REM  DLL .NET vao thu muc tam moi lan mo -> cho vai giay moi thay cua so.
REM  Ban Auto_Clicker con bi Defender bao nham Trojan voi ban onefile.
REM ============================================================
cd /d "%~dp0.."

set PY=.venv\Scripts\python.exe
if not exist %PY% (
    echo *** Khong thay .venv - chay truoc:
    echo     python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt pyinstaller
    pause
    exit /b 1
)

echo [1/6] Dong ung dung neu dang chay...
taskkill /IM Cat_Studio.exe /F >nul 2>&1
timeout /t 1 /nobreak >nul
if exist dist\Cat_Studio rmdir /S /Q dist\Cat_Studio

echo [2/6] Build giao dien web (vite)...
pushd webui
call npm run build
if errorlevel 1 (
    popd
    echo *** BUILD GIAO DIEN THAT BAI ***
    pause
    exit /b 1
)
popd

echo [3/6] Chay bo kiem truoc khi dong goi...
%PY% tests\chay_tat_ca.py
if errorlevel 1 (
    echo.
    echo *** BO KIEM DO - KHONG dong goi. Sua xong roi chay lai. ***
    pause
    exit /b 1
)

echo [4/6] Dang dong goi Python...
%PY% -m PyInstaller Cat_Studio.spec --noconfirm --clean
if errorlevel 1 (
    echo.
    echo *** DONG GOI THAT BAI ***
    pause
    exit /b 1
)

echo [5/6] Them file huong dan...
> dist\Cat_Studio\DOC-TRUOC-KHI-CHAY.txt echo CAT STUDIO - ve so do chien luoc va backtest
>> dist\Cat_Studio\DOC-TRUOC-KHI-CHAY.txt echo =============================================
>> dist\Cat_Studio\DOC-TRUOC-KHI-CHAY.txt echo.
>> dist\Cat_Studio\DOC-TRUOC-KHI-CHAY.txt echo CACH DUNG: bam dup vao Cat_Studio.exe
>> dist\Cat_Studio\DOC-TRUOC-KHI-CHAY.txt echo.
>> dist\Cat_Studio\DOC-TRUOC-KHI-CHAY.txt echo LUU Y: giu nguyen ca thu muc nay, dung tach rieng file .exe ra.
>> dist\Cat_Studio\DOC-TRUOC-KHI-CHAY.txt echo.
>> dist\Cat_Studio\DOC-TRUOC-KHI-CHAY.txt echo Du lieu cua ban (chien luoc, nen, lich su chay) nam trong thu muc
>> dist\Cat_Studio\DOC-TRUOC-KHI-CHAY.txt echo du_lieu\ ngay canh file .exe. Muon chuyen sang may khac thi chep
>> dist\Cat_Studio\DOC-TRUOC-KHI-CHAY.txt echo ca thu muc do di theo.
>> dist\Cat_Studio\DOC-TRUOC-KHI-CHAY.txt echo.
>> dist\Cat_Studio\DOC-TRUOC-KHI-CHAY.txt echo CAN CO:
>> dist\Cat_Studio\DOC-TRUOC-KHI-CHAY.txt echo   - Microsoft Edge WebView2 Runtime (Windows 10/11 co san cung Edge)
>> dist\Cat_Studio\DOC-TRUOC-KHI-CHAY.txt echo   - .NET Framework 4.7.2 tro len
>> dist\Cat_Studio\DOC-TRUOC-KHI-CHAY.txt echo   - MetaTrader 5 (chi can khi TAI NEN lan dau; backtest thi khong can)
>> dist\Cat_Studio\DOC-TRUOC-KHI-CHAY.txt echo.
>> dist\Cat_Studio\DOC-TRUOC-KHI-CHAY.txt echo Lan dau chay chua co nen: mo Cai dat, chon symbol va khoang From/To,
>> dist\Cat_Studio\DOC-TRUOC-KHI-CHAY.txt echo roi bam Chay - app tu tai phan con thieu tu MT5.

REM  Nen bang ZipFile.CreateFromDirectory cua .NET, KHONG dung Compress-Archive:
REM  Compress-Archive gom het vao bo nho truoc khi ghi nen voi goi 211 file / 67 MB thi
REM  no treo - da do that: chay 22 PHUT chua xong, phai kill. Ban .NET ghi thang ra dia:
REM  2,6 GIAY, ra 29,2 MB. (Auto_Clicker dung Compress-Archive duoc vi goi nho hon nhieu.)
echo [6/6] Nen thanh .zip de phat hanh...
if exist Cat_Studio-windows.zip del /F /Q Cat_Studio-windows.zip
powershell -NoProfile -Command "Add-Type -AssemblyName System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::CreateFromDirectory((Resolve-Path 'dist\Cat_Studio').Path, (Join-Path (Get-Location) 'Cat_Studio-windows.zip'), [System.IO.Compression.CompressionLevel]::Optimal, $true)"
if errorlevel 1 (
    echo *** NEN ZIP THAT BAI ***
    pause
    exit /b 1
)

REM Don rac trung gian: build\ chi la thu muc lam viec cua PyInstaller, giu lai
REM chi to thu muc goc chu khong dung vao viec gi.
if exist build rmdir /S /Q build

echo.
echo Xong!
echo    Thu muc      : dist\Cat_Studio\
echo    Ban phat hanh: Cat_Studio-windows.zip
echo.
pause
