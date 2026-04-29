@echo off
echo Starting application...

REM Check if python is available
where python >nul 2>&1
if %errorlevel% equ 0 (
    python main.py
) else (
    echo Error: Python is not installed or not in PATH.
    echo Please install Python and try again.
    pause
)