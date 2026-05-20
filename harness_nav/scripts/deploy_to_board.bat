@echo off
REM Deploy Harness Navigation System to Raspberry Pi
REM Usage: deploy_to_raspberrypi.bat [raspberrypi_ip]
REM Requires: scp, ssh (install Git for Windows or use WSL)

setlocal

set PI_USER=pi
if "%1"=="" (set PI_HOST=raspberrypi.local) else (set PI_HOST=%1)
set PI_DIR=/home/pi/harness_nav
set PROJECT_DIR=%~dp0..

echo ========================================
echo Deploying to Raspberry Pi
echo Host: %PI_USER%@%PI_HOST%
echo Source: %PROJECT_DIR%
echo Target: %PI_DIR%
echo ========================================

echo.
echo [1/4] Creating directory on Raspberry Pi...
ssh %PI_USER%@%PI_HOST% "mkdir -p %PI_DIR%"

echo.
echo [2/4] Copying files...
scp -r "%PROJECT_DIR%\config" %PI_USER%@%PI_HOST%:%PI_DIR%/
scp -r "%PROJECT_DIR%\core" %PI_USER%@%PI_HOST%:%PI_DIR%/
scp -r "%PROJECT_DIR%\gui" %PI_USER%@%PI_HOST%:%PI_DIR%/
scp -r "%PROJECT_DIR%\hal" %PI_USER%@%PI_HOST%:%PI_DIR%/
scp -r "%PROJECT_DIR%\data" %PI_USER%@%PI_HOST%:%PI_DIR%/
scp "%PROJECT_DIR%\main.py" %PI_USER%@%PI_HOST%:%PI_DIR%/
scp "%PROJECT_DIR%\__init__.py" %PI_USER%@%PI_HOST%:%PI_DIR%/
scp "%PROJECT_DIR%\requirements.txt" %PI_USER%@%PI_HOST%:%PI_DIR%/

echo.
echo [3/4] Installing dependencies on Raspberry Pi...
ssh %PI_USER%@%PI_HOST% "cd ~/harness_nav && pip3 install --user PyQt5 PyYAML"

echo.
echo ========================================
echo Deployment complete!
echo ========================================
echo.
echo To run on Raspberry Pi:
echo   ssh %PI_USER%@%PI_HOST%
echo   cd %PI_DIR%
echo   python3 main.py
echo.

pause
