@echo off
setlocal

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo venv not found.
    echo Run run_uploader.bat once first.
    pause
    exit /b 1
)

echo Installing PyInstaller...
"venv\Scripts\python.exe" -m pip install pyinstaller

if errorlevel 1 (
    echo PyInstaller installation failed.
    pause
    exit /b 1
)

echo Cleaning old build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Building Windows portable app...

"venv\Scripts\python.exe" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onedir ^
    --name AnimeUploader ^
    --collect-all supabase ^
    --collect-all postgrest ^
    --collect-all realtime ^
    --collect-all storage3 ^
    --collect-all gotrue ^
    main.py

if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)

copy /y ".env" "dist\AnimeUploader\.env" >nul
if not exist "dist\AnimeUploader\videos" mkdir "dist\AnimeUploader\videos"
if not exist "dist\AnimeUploader\archive" mkdir "dist\AnimeUploader\archive"
if not exist "dist\AnimeUploader\unmatched_videos" mkdir "dist\AnimeUploader\unmatched_videos"
if not exist "dist\AnimeUploader\quarantine" mkdir "dist\AnimeUploader\quarantine"
if not exist "dist\AnimeUploader\logs" mkdir "dist\AnimeUploader\logs"

copy /y "run_portable.bat" "dist\AnimeUploader\run_portable.bat" >nul
copy /y "README.md" "dist\AnimeUploader\README.md" >nul

echo.
echo Build completed successfully.
echo Folder: dist\AnimeUploader
echo.
pause