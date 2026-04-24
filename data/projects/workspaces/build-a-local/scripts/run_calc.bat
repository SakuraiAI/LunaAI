@echo off
setlocal
cd /d "%~dp0.."

if exist .venv\Scripts\activate.bat (
  call .venv\Scripts\activate.bat
)

if exist src\main.py (
  python -u src\main.py
) else (
  echo Calculator entrypoint not found: src\main.py
)

pause
