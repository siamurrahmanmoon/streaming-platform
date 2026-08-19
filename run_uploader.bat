@echo off
setlocal

cd /d "%~dp0"

echo Starting Anime Streaming Platform...
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not available in PATH.
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv

    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )

    echo Installing required packages...
    "venv\Scripts\python.exe" -m pip install -r requirements.txt

    if errorlevel 1 (
        echo Failed to install required packages.
        pause
        exit /b 1
    )
)

echo Running application...
echo.

"venv\Scripts\python.exe" main.py

echo.
echo Application stopped.
pause