@echo off
echo ====================================
echo       MEMO - Desktop Companion
echo ====================================
echo.

REM Check for optimized version
if exist main_optimized.py (
    echo Starting MEMO (Optimized)...
    python main_optimized.py %*
) else (
    echo Starting MEMO (Standard)...
    python main.py %*
)

pause
