@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if errorlevel 1 (
  echo.
  echo Global Layoff Lens could not start. Read the message above, then press any key to close.
  pause >nul
)
