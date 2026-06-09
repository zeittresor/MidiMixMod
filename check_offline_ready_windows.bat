@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%~dp0"
cd /d "%ROOT%"
where powershell.exe >nul 2>&1 && set "HAS_PS=1" || set "HAS_PS=0"

if not exist "wheelhouse" (
    call :cecho Red "wheelhouse missing"
    pause
    exit /b 1
)
call :cecho Cyan "Wheelhouse contents:"
dir /b wheelhouse
echo.
call :cecho Green "If PyQt6, PyQt6_Qt6/PyQt6-Qt6, PyQt6_sip, mido, python_rtmidi and pyinstaller wheels are present, offline setup should work."
pause
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
