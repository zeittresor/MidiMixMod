@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%~dp0"
cd /d "%ROOT%"
where powershell.exe >nul 2>&1 && set "HAS_PS=1" || set "HAS_PS=0"

call :cecho Magenta "============================================================"
call :cecho Magenta " MidiMixMod Channel Workbench - ONLINE SETUP"
call :cecho Magenta "============================================================"
echo.

call :cecho Cyan "[1/5] Checking Python launcher..."
py -3 --version >nul 2>&1
if errorlevel 1 (
    call :cecho Red "ERROR: Python 3 launcher not found. Install Python 3.11+ x64 first."
    pause
    exit /b 1
)

call :cecho Cyan "[2/5] Creating local virtual environment .venv..."
if not exist ".venv" py -3 -m venv .venv
if errorlevel 1 goto :fail

call :cecho Cyan "[3/5] Upgrading pip inside .venv..."
call ".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail

call :cecho Cyan "[4/5] Downloading binary wheels into local wheelhouse..."
if not exist "wheelhouse" mkdir "wheelhouse"
call ".venv\Scripts\python.exe" -m pip download --only-binary=:all: -r requirements.txt -d wheelhouse
if errorlevel 1 (
    call :cecho Yellow "Wheel download failed. This usually means one dependency has no wheel for your Python/Windows architecture."
    call :cecho Yellow "Try Python 3.11 or 3.12 x64, then run this script again."
    goto :fail
)

call :cecho Cyan "[5/5] Installing from local wheelhouse..."
call ".venv\Scripts\python.exe" -m pip install --no-index --find-links=wheelhouse -r requirements.txt
if errorlevel 1 goto :fail

echo.
call :cecho Green "SUCCESS: Online setup complete."
call :cecho Green "The wheelhouse folder can be copied to offline machines together with this project."
call :launch_after_setup
exit /b 0

:fail
echo.
call :cecho Red "SETUP FAILED."
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
