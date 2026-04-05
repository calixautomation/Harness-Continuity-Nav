@echo off
REM Deploy Harness Navigation System to BeagleBone Black
REM Usage: deploy_to_beaglebone.bat [beaglebone_ip]
REM Requires: scp, ssh (install Git for Windows or use WSL)

setlocal

set BBB_USER=debian
if "%1"=="" (set BBB_HOST=beaglebone.local) else (set BBB_HOST=%1)
set BBB_DIR=/home/debian/harness_nav
set PROJECT_DIR=%~dp0..

echo ========================================
echo Deploying to BeagleBone Black
echo Host: %BBB_USER%@%BBB_HOST%
echo Source: %PROJECT_DIR%
echo Target: %BBB_DIR%
echo ========================================

echo.
echo [1/4] Creating directory on BeagleBone...
ssh %BBB_USER%@%BBB_HOST% "mkdir -p %BBB_DIR%"

echo.
echo [2/4] Copying files...
scp -r "%PROJECT_DIR%\config" %BBB_USER%@%BBB_HOST%:%BBB_DIR%/
scp -r "%PROJECT_DIR%\core" %BBB_USER%@%BBB_HOST%:%BBB_DIR%/
scp -r "%PROJECT_DIR%\gui" %BBB_USER%@%BBB_HOST%:%BBB_DIR%/
scp -r "%PROJECT_DIR%\hal" %BBB_USER%@%BBB_HOST%:%BBB_DIR%/
scp -r "%PROJECT_DIR%\data" %BBB_USER%@%BBB_HOST%:%BBB_DIR%/
scp "%PROJECT_DIR%\main.py" %BBB_USER%@%BBB_HOST%:%BBB_DIR%/
scp "%PROJECT_DIR%\__init__.py" %BBB_USER%@%BBB_HOST%:%BBB_DIR%/
scp "%PROJECT_DIR%\requirements.txt" %BBB_USER%@%BBB_HOST%:%BBB_DIR%/

echo.
echo [3/4] Installing dependencies on BeagleBone...
ssh %BBB_USER%@%BBB_HOST% "cd ~/harness_nav && pip3 install --user PyQt5 PyYAML Adafruit-BBIO"

echo.
echo ========================================
echo Deployment complete!
echo ========================================
echo.
echo To run on BeagleBone:
echo   ssh %BBB_USER%@%BBB_HOST%
echo   cd %BBB_DIR%
echo   python3 main.py
echo.

pause
