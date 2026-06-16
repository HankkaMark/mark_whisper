@echo off
cd /d "%~dp0"
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo Run install.cmd first.
  exit /b 1
)
set "PYTHONPATH=%~dp0"
"%PY%" -m whisper
