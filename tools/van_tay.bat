@echo off
cd /d "%~dp0.."
.venv\Scripts\python.exe tools\van_tay.py %*
