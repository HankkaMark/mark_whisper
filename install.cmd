@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
set "BOOT=%~dp0tools\bootstrap_install.py"

if exist "%~dp0.python-path" (
  for /f "usebackq delims=" %%P in ("%~dp0.python-path") do (
    if exist "%%P" (
      "%%P" "%BOOT%"
      exit /b !ERRORLEVEL!
    )
  )
)

if exist "C:\Users\Default\AppData\Local\Koi\Python\WPy64-31290\python\python.exe" (
  "C:\Users\Default\AppData\Local\Koi\Python\WPy64-31290\python\python.exe" "%BOOT%"
  exit /b %ERRORLEVEL%
)

where py >nul 2>&1 && (
  py -3 "%BOOT%"
  exit /b %ERRORLEVEL%
)

where python >nul 2>&1 && (
  python "%BOOT%"
  exit /b %ERRORLEVEL%
)

echo No working Python found.
echo Try: winget install Python.Python.3.12
exit /b 1
