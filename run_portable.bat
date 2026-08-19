@echo off
setlocal

cd /d "%~dp0"

if not exist "AnimeUploader.exe" (
    echo AnimeUploader.exe was not found.
    echo Keep this file in the same folder as AnimeUploader.exe.
    pause
    exit /b 1
)

if not exist ".env" (
    echo Warning: .env was not found.
    echo Configure .env before starting the uploader.
    echo.
)

echo Starting Anime Streaming Platform...
echo.
AnimeUploader.exe

if errorlevel 1 (
    echo.
    echo Application stopped with an error.
) else (
    echo.
    echo Application stopped.
)

pause
