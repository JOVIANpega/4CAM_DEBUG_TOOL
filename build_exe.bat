@echo off
echo ========================================
echo 4CAM DEBUG TOOL EXE Builder
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found
    pause
    exit /b 1
)

REM Check PyInstaller
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo Error: PyInstaller install failed
        pause
        exit /b 1
    )
)

REM Clean old files
echo Cleaning old build files...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "__pycache__" rmdir /s /q "__pycache__"

REM Create version info
echo Creating version info...
python create_version_info.py
if errorlevel 1 (
    echo Error: version_info.txt creation failed
    pause
    exit /b 1
)

REM Set version
for /f "usebackq delims=" %%v in (`type version_info.txt ^| findstr /i "FileVersion"`) do set VERSION=%%v
for /f "tokens=2 delims='" %%a in ("%VERSION%") do set VERSION=%%a
if "%VERSION%"=="" set VERSION=v1.9.1
set EXE_NAME=4CAM_DEBUG_TOOL_%VERSION%

echo.
echo Building %EXE_NAME%.exe...
echo.

REM Create COMMANDS directory if needed
if not exist "COMMANDS" mkdir "COMMANDS"
if not exist "COMMANDS\linux.txt" (
    echo Creating default linux.txt...
    echo # Linux Commands > "COMMANDS\linux.txt"
    echo List /mnt/usr/ files = ls -la /mnt/usr/ >> "COMMANDS\linux.txt"
    echo Delete JPG files = rm -f /mnt/usr/*.jpg >> "COMMANDS\linux.txt"
    echo Delete YUV files = rm -f /mnt/usr/*.yuv >> "COMMANDS\linux.txt"
    echo System info = uname -a >> "COMMANDS\linux.txt"
    echo Disk usage = df -h >> "COMMANDS\linux.txt"
    echo Memory usage = free -h >> "COMMANDS\linux.txt"
)

REM Build EXE
if exist "assets\icon.ico" (
    echo Building with custom icon...
    pyinstaller --onefile --noconsole --icon=assets/icon.ico --version-file version_info.txt --add-data "COMMANDS;COMMANDS" --add-data "REF;REF" --add-data "settings.json;." --name=%EXE_NAME% main.py
) else (
    echo Building without icon...
    pyinstaller --onefile --noconsole --version-file version_info.txt --add-data "COMMANDS;COMMANDS" --add-data "REF;REF" --add-data "settings.json;." --name=%EXE_NAME% main.py
)

if errorlevel 1 (
    echo.
    echo Error: Build failed!
    pause
    exit /b 1
)

REM Check if EXE was created
if exist "dist\%EXE_NAME%.exe" (
    echo.
    echo ========================================
    echo Build successful!
    echo File location: dist\%EXE_NAME%.exe
    echo ========================================
    echo.
    
    REM Copy resource directories
    echo Copying resource directories...
    if exist "COMMANDS" (
        if exist "dist\COMMANDS" rmdir /s /q "dist\COMMANDS"
        xcopy "COMMANDS" "dist\COMMANDS" /E /I /Q /Y
        echo - COMMANDS directory copied
    )
    if exist "REF" (
        xcopy "REF" "dist\REF" /E /I /Q
        echo - REF directory copied
    )
    if exist "assets" (
        xcopy "assets" "dist\assets" /E /I /Q
        echo - assets directory copied
    )

    REM Copy settings.json
    if exist "settings.json" (
        copy /Y "settings.json" "dist\settings.json" >nul
        echo - settings.json copied
    )
    
    REM Show file info
    echo.
    echo File information:
    dir "dist\%EXE_NAME%.exe"
    echo.
    
    REM Show dist directory contents
    echo dist directory contents:
    dir "dist" /B
    echo.
    
    REM Ask to open folder
    set /p choice="Open dist folder? (Y/N): "
    if /i "%choice%"=="Y" (
        explorer "dist"
    )
) else (
    echo.
    echo Error: EXE file not created!
)

echo.
pause