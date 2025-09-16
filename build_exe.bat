@echo off
chcp 65001 >nul
echo ========================================
echo 4CAM_DEBUG_TOOL EXE 打包工具
echo ========================================
echo.

REM 檢查 Python 環境
python --version >nul 2>&1
if errorlevel 1 (
    echo 錯誤：找不到 Python，請確認 Python 已安裝並加入 PATH
    pause
    exit /b 1
)

REM 檢查 PyInstaller
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo 正在安裝 PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo 錯誤：PyInstaller 安裝失敗
        pause
        exit /b 1
    )
)

REM 檢查並創建圖示檔案
if not exist "assets\icon.ico" (
    echo 未找到圖示檔案，正在創建...
    python create_icon.py
    if errorlevel 1 (
        echo 警告：圖示創建失敗，將使用預設圖示
    )
)

REM 清理舊的建置檔案
echo 清理舊的建置檔案...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "__pycache__" rmdir /s /q "__pycache__"

REM 設定版本號
set VERSION=v1.2
set EXE_NAME=4CAM_DEBUG_TOOL_%VERSION%

echo.
echo 開始打包 %EXE_NAME%.exe...
echo.

REM 檢查是否有圖示檔案
if exist "assets\icon.ico" (
    echo 使用自訂圖示打包...
    pyinstaller --onefile --noconsole --icon=assets/icon.ico --add-data "COMMANDS;COMMANDS" --add-data "REF;REF" --name=%EXE_NAME% main.py
) else (
    echo 未找到圖示檔案，使用預設圖示打包...
    pyinstaller --onefile --noconsole --add-data "COMMANDS;COMMANDS" --add-data "REF;REF" --name=%EXE_NAME% main.py
)

if errorlevel 1 (
    echo.
    echo 錯誤：打包失敗！
    pause
    exit /b 1
)

REM 檢查 EXE 是否成功生成
if exist "dist\%EXE_NAME%.exe" (
    echo.
    echo ========================================
    echo 打包成功！
    echo 檔案位置：dist\%EXE_NAME%.exe
    echo ========================================
    echo.
    
    REM 複製資源目錄到 dist
    echo 複製資源目錄到 dist...
    if exist "COMMANDS" (
        xcopy "COMMANDS" "dist\COMMANDS" /E /I /Q
        echo - COMMANDS 目錄已複製
    )
    if exist "REF" (
        xcopy "REF" "dist\REF" /E /I /Q
        echo - REF 目錄已複製
    )
    if exist "assets" (
        xcopy "assets" "dist\assets" /E /I /Q
        echo - assets 目錄已複製
    )
    
    REM 顯示檔案資訊
    echo.
    echo 檔案資訊：
    dir "dist\%EXE_NAME%.exe"
    echo.
    
    REM 顯示 dist 目錄內容
    echo dist 目錄內容：
    dir "dist" /B
    echo.
    
    REM 詢問是否開啟資料夾
    set /p choice="是否開啟 dist 資料夾？(Y/N): "
    if /i "%choice%"=="Y" (
        explorer "dist"
    )
) else (
    echo.
    echo 錯誤：EXE 檔案未成功生成！
)

echo.
pause
