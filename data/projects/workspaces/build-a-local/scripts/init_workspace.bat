@echo off
setlocal
cd /d "%~dp0.."

echo Preparing LunaAI project workspace...
if not exist src mkdir src
if not exist docs mkdir docs
if not exist tests mkdir tests
if not exist scripts mkdir scripts

if not exist .venv (
  python -m venv .venv
)

call .venv\Scripts\activate.bat
if exist requirements.txt (
  python -m pip install -r requirements.txt
) else (
  echo No requirements.txt found. Skipping dependency install.
)

echo Workspace is ready.
pause
