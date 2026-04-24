@echo off
setlocal
cd /d "%~dp0.."

if exist .venv\Scripts\activate.bat (
  call .venv\Scripts\activate.bat
)

if exist tests (
  python -m pytest tests
) else (
  echo Tests folder does not exist yet.
)

pause
