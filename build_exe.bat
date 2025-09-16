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

REM 確保 COMMANDS\linux.txt 存在（UTF-8）
if not exist "COMMANDS" (
    mkdir "COMMANDS"
)
if not exist "COMMANDS\linux.txt" (
    echo 產生預設 COMMANDS\linux.txt ...
    powershell -NoProfile -Command ^
        "$lines = @(
        '# 常用 LINUX 指令（格式：NAME = COMMAND）',
        '# 範例：列出 /mnt/usr/ 所有檔案 = ls -la /mnt/usr/',
        '',
        '列出 /mnt/usr/ 所有檔案 = ls -la /mnt/usr/',
        '刪除 /mnt/usr/ JPG 檔 = rm -f /mnt/usr/*.jpg',
        '刪除 /mnt/usr/ YUV 檔 = rm -f /mnt/usr/*.yuv',
        '刪除 /var/vsp/ JPG 檔 = rm -f /var/vsp/*.jpg',
        '刪除 /var/vsp/ YUV 檔 = rm -f /var/vsp/*.yuv',
        '顯示系統資訊 = uname -a',
        '顯示磁碟使用量 = df -h',
        '顯示記憶體使用量 = free -h',
        '顯示目前目錄詳細檔案 = ls -la',
        '列出根目錄檔案 = ls -la /',
        '列出臨時目錄檔案 = ls -la /tmp',
        '列出使用者目錄檔案 = ls -la /mnt/usr',
        '網路連線 = netstat -an',
        '網路介面 = ifconfig',
        '路由表 = route -n',
        '核心版本 = cat /proc/version',
        'CPU 資訊 = cat /proc/cpuinfo',
        '記憶體資訊 = cat /proc/meminfo',
        '系統運行時間 = uptime',
        '系統時間 = date',
        '硬體時鐘 = hwclock',
        '掛載點 = mount',
        '已載入模組 = lsmod',
        'USB 設備 = lsusb',
        'PCI 設備 = lspci',
        'I2C 匯流排 0 = i2cdetect -y 0',
        'I2C 匯流排 1 = i2cdetect -y 1',
        '最近核心訊息 = dmesg | tail -20',
        '錯誤訊息過濾 = dmesg | grep -i error',
        '攝影機訊息過濾 = dmesg | grep -i camera',
        'VSP 目錄 = ls -la /var/vsp',
        'TMP TAR 目錄 = ls -la /tmp/tar',
        '檢查錄影程序 = ps aux | grep hd_video',
        '檢查診斷程序 = ps aux | grep diag',
        '停止錄影程序 = killall hd_video_record_with_vsp_4dev_smart2_pega_dre',
        '檢查 /tmp 空間 = df -h /tmp',
        '檢查 /var/vsp 空間 = df -h /var/vsp',
        '檢查 /mnt/usr 空間 = df -h /mnt/usr',
        '系統負載 = cat /proc/loadavg'
        );
        [IO.File]::WriteAllLines('COMMANDS/linux.txt', $lines, (New-Object System.Text.UTF8Encoding($false)))"
)

REM 檢查是否有圖示檔案
if exist "assets\icon.ico" (
    echo 使用自訂圖示打包...
    pyinstaller --onefile --noconsole --icon=assets/icon.ico --add-data "COMMANDS;COMMANDS" --add-data "REF;REF" --add-data "settings.json;." --name=%EXE_NAME% main.py
) else (
    echo 未找到圖示檔案，使用預設圖示打包...
    pyinstaller --onefile --noconsole --add-data "COMMANDS;COMMANDS" --add-data "REF;REF" --add-data "settings.json;." --name=%EXE_NAME% main.py
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
        if not exist "dist\COMMANDS" (
            xcopy "COMMANDS" "dist\COMMANDS" /E /I /Q
            echo - COMMANDS 目錄已複製
        ) else (
            echo - dist\COMMANDS 已存在，略過複製（避免覆蓋您的修改）
        )
    )
    if exist "REF" (
        xcopy "REF" "dist\REF" /E /I /Q
        echo - REF 目錄已複製
    )
    if exist "assets" (
        xcopy "assets" "dist\assets" /E /I /Q
        echo - assets 目錄已複製
    )

    REM 複製設定檔 settings.json 至 dist（若存在）
    if exist "settings.json" (
        copy /Y "settings.json" "dist\settings.json" >nul
        echo - settings.json 已複製
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
