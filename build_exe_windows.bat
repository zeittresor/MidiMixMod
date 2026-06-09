@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%~dp0"
cd /d "%ROOT%"
where powershell.exe >nul 2>&1 && set "HAS_PS=1" || set "HAS_PS=0"

if not exist ".venv\Scripts\python.exe" (
    call :cecho Red "ERROR: .venv not found. Run setup first."
    pause
    exit /b 1
)
call :cecho Cyan "Building Windows EXE with PyInstaller..."
call ".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name MidiMixMod_Channel_Workbench main.py
if errorlevel 1 goto :fail
echo.
call :cecho Green "SUCCESS: EXE created in dist\MidiMixMod_Channel_Workbench.exe"
pause
exit /b 0
:fail
call :cecho Red "Build failed."
pause
exit /b 1

:cecho
set "CE_COLOR=%~1"
set "CE_TEXT=%~2"
if "%HAS_PS%"=="1" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Write-Host $env:CE_TEXT -ForegroundColor $env:CE_COLOR"
) else (
    echo %CE_TEXT%
)
exit /b 0
