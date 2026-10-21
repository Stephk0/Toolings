@echo off
rem Opens the Export Lab in the default browser through a local server (browsers do not run
rem the page's modules from file://). Uses Python when installed, else PowerShell.
cd /d "%~dp0"
set PORT=8791
where python >nul 2>nul
if %errorlevel%==0 (
    start "" "http://localhost:%PORT%/"
    python serve.py . %PORT%
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0serve.ps1" -Port %PORT%
)
