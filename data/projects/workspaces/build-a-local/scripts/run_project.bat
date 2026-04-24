@echo off
setlocal
cd /d "%~dp0.."

if exist .venv\Scripts\activate.bat (
  call .venv\Scripts\activate.bat
)

if exist package.json (
  where npm >nul 2>nul
  if %ERRORLEVEL% EQU 0 (
    npm run dev
    pause
    exit /b
  )
)

if exist src\main.py (
  python -u src\main.py
) else if exist main.py (
  python -u main.py
) else if exist app.py (
  python -u app.py
) else (
  echo No runnable entrypoint found. Expected package.json, src\main.py, main.py, or app.py.
)

pause
