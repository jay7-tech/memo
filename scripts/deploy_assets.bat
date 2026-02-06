@echo off
setlocal
echo ==========================================
echo      MEMO ASSET DEPLOYER (WINDOWS)
echo ==========================================
echo.
echo This script will send your desktop assets to the Raspberry Pi.
echo source: %~dp0..\interface\lcd\assets
echo.

set /p PI_IP="Enter Raspberry Pi IP Address (e.g. 192.168.1.x): "
set /p PI_USER="Enter Pi Username (default: mino): "
if "%PI_USER%"=="" set PI_USER=mino

echo.
echo Sending files... (You may be asked for the Pi's password)
echo.

scp -r "%~dp0..\interface\lcd\assets\*" %PI_USER%@%PI_IP%:~/mino_main/memo/interface/lcd/assets/

if %errorlevel% equ 0 (
    echo.
    echo ✅ SUCCESS! Assets transferred.
    echo Now restart MEMO on the Pi: ./run_memo.sh
) else (
    echo.
    echo ❌ ERROR: Transfer failed. Check IP and try again.
)
pause
