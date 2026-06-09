@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%~dp0"
cd /d "%ROOT%"
where powershell.exe >nul 2>&1 && set "HAS_PS=1" || set "HAS_PS=0"

if not exist ".venv\Scripts\python.exe" (
    call :cecho Red "ERROR: .venv not found. Run setup_online_windows.bat or setup_offline_windows.bat first."
    pause
    exit /b 1
)
call :cecho Cyan "Starting MidiMixMod Channel Workbench..."
call ".venv\Scripts\python.exe" main.py
if errorlevel 1 pause
exit /b 0

:cecho
set "CE_COLOR=%~1"
set "CE_TEXT=%~2"
if "%HAS_PS%"=="1" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Write-Host $env:CE_TEXT -ForegroundColor $env:CE_COLOR"
) else (
    echo %CE_TEXT%
)
exit /b 0
