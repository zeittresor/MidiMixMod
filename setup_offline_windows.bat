@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%~dp0"
cd /d "%ROOT%"
where powershell.exe >nul 2>&1 && set "HAS_PS=1" || set "HAS_PS=0"

call :cecho Magenta "============================================================"
call :cecho Magenta " MidiMixMod Channel Workbench - OFFLINE SETUP"
call :cecho Magenta "============================================================"
echo.

call :cecho Cyan "[1/4] Checking local wheelhouse..."
if not exist "wheelhouse" goto :missing_wheelhouse
dir /b "wheelhouse\*.whl" >nul 2>&1
if errorlevel 1 goto :missing_wheelhouse

py -3 --version >nul 2>&1
if errorlevel 1 (
    call :cecho Red "ERROR: Python 3 launcher not found. Install Python 3.11+ x64 first."
    pause
    exit /b 1
)

call :cecho Cyan "[2/4] Creating local virtual environment .venv..."
if not exist ".venv" py -3 -m venv .venv
if errorlevel 1 goto :fail

call :cecho Cyan "[3/4] Installing dependencies from wheelhouse only..."
call ".venv\Scripts\python.exe" -m pip install --no-index --find-links=wheelhouse -r requirements.txt
if errorlevel 1 goto :fail

call :cecho Cyan "[4/4] Verifying import..."
call ".venv\Scripts\python.exe" -c "import PyQt6, mido; print('Imports OK')"
if errorlevel 1 goto :fail

echo.
call :cecho Green "SUCCESS: Offline setup complete."
call :launch_after_setup
exit /b 0

:missing_wheelhouse
echo.
call :cecho Red "ERROR: wheelhouse folder is missing or contains no .whl files."
call :cecho Yellow "Offline setup cannot download dependencies by design."
call :cecho Yellow "What to do: run setup_online_windows.bat once on an internet-connected Windows machine, then copy this complete project folder including the wheelhouse folder to the offline machine."
call :cecho Yellow "After that, run setup_offline_windows.bat again."
pause
exit /b 1

:fail
echo.
call :cecho Red "OFFLINE SETUP FAILED."
pause
exit /b 1

:launch_after_setup
echo.
call :cecho Cyan "The app will start in 10 seconds."
choice /C YN /N /T 10 /D Y /M "Press Y to start now, press N to cancel, or wait 10 seconds: "
if errorlevel 2 (
    call :cecho Yellow "Auto-start canceled. You can start later with run_windows.bat."
    pause
    exit /b 0
)
call :cecho Green "Starting MidiMixMod Channel Workbench..."
call "%ROOT%run_windows.bat"
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
