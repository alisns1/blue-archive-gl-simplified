@echo off
chcp 65001 >nul
echo ============================================================
echo   Blue Archive GL  -  Traditional Chinese to Simplified
echo ============================================================
echo.
echo   1. Connect your phone via USB, enable USB debugging
echo   2. Close the game on the phone
echo   3. Press any key to start
echo.
pause >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0localize_phone.ps1"
echo.
echo Finished. Press any key to close.
pause >nul
