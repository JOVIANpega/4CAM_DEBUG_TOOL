# 4CAM_DEBUG_TOOL

## 專案簡介
4CAM_DEBUG_TOOL 是一個專為 4 攝影機 DUT（Device Under Test）設計的 SSH 控制工具，透過圖形化介面提供便捷的指令執行和檔案管理功能。

## 主要功能
- **SSH 連線管理**：支援 DUT SSH 連線測試與狀態監控
- **多標籤頁介面**：左側以標籤頁管理五大區塊：指令、LINUX 指令、手動指令、檔案傳輸、設定
- **指令執行**：從 `REF/Command.txt` 載入或手動輸入指令執行
- **Linux 指令集**：固定從 `COMMANDS/linux.txt` 載入基礎 Linux 指令
- **手動指令輸入**：支援直接輸入自訂指令執行
- **檔案傳輸**：支援萬用字元（glob）檔案複製功能，固定使用 `COMMANDS/download.txt`
- **智能 Tooltip**：懸停提示功能，3 秒後自動消失
- **連線狀態指示器**：即時顯示 SSH 連線狀態（綠/黃/黑）
- **GUI 設定保存**：自動保存視窗大小、檔案路徑、字體大小與選項
- **獨立字體控制**：支援左側視窗、右側視窗、彈出視窗的獨立字體大小調整
- **頂部工具列**：
  - 標題區域：顯示「4CAM DEBUG TOOL」
  - 通用按鍵：說明、清空、存取LOG（全域可用）
  - 工具列：「每次下指令清除舊訊息」勾選框
- **設定頁面**：版本設定與字體設定集中管理
- **截圖預覽**：左側底部自動顯示 `assets/screenshots` 內的 PNG/JPG 縮圖

## 技術特色
- **Tkinter GUI**：使用 Python Tkinter 開發，穩定可靠
- **模組化設計**：函式獨立定義，易於維護
- **錯誤處理**：完整的 try-except 錯誤處理機制
- **PyInstaller 打包**：支援打包為單一 EXE 檔案
- **資源路徑管理**：支援打包後的相對路徑存取
- **動態字體調整**：支援即時調整所有介面元件字體大小
- **智能提示系統**：Tooltip 自動消失，避免界面殘留
- **指令分類管理**：使用三個專用 TXT 檔案管理不同類型指令

## 系統需求
- Python 3.7+
- Windows 10/11
- 網路連線（用於 SSH 連線）

## 安裝與使用

### 1. 直接執行
```bash
python main.py
```

### 2. 打包為 EXE
```bash
# 執行打包腳本
build_exe.bat
```

或使用指令（單檔、隱藏主控台、含圖示）：
```bash
pyinstaller --onefile --noconsole --icon=assets/icon.ico main.py
```

### 3. 使用說明

#### 快速開始
1. **啟動程式**：執行 `python main.py` 或雙擊 EXE 檔案
2. **檢查連線**：程式會自動嘗試連線到 DUT（預設 IP：192.168.11.143）
3. **執行指令**：選擇指令並點擊「執行指令」
4. **檔案傳輸**：設定來源和目標路徑，點擊「開始傳輸」

#### 詳細操作
1. **連線設定**：輸入 DUT IP 位址和使用者名稱，點擊「測試連線」確認 SSH 連線
2. **指令執行**：
   - **指令標籤頁**：選擇或載入 `REF/Command.txt`，按「執行指令」
   - **LINUX 指令標籤頁**：從 `COMMANDS/linux.txt` 選擇指令執行，按「開啟指令表」編輯檔案
   - **手動指令標籤頁**：直接輸入自訂指令執行
3. **檔案傳輸**：在「檔案傳輸」標籤頁設定來源與目標後按「開始傳輸」，按「開啟指令表」查看 `COMMANDS/download.txt`
4. **字體調整**：在「設定」標籤頁調整左側、右側、彈出視窗的獨立字體大小
5. **其他功能**：勾選頂部「每次下指令清除舊訊息」自動清空舊訊息

## 檔案結構
```
4CAM_DEBUG_TOOL/
├── main.py                    # 主程式入口
├── command_loader.py          # 指令載入模組
├── ssh_client.py              # SSH 客戶端管理
├── build_exe.bat              # EXE 打包腳本（批次檔）
├── build_exe.py               # EXE 打包腳本（Python）
├── requirements.txt           # Python 依賴套件
├── settings.json              # 應用程式設定檔
├── assets/                    # 資源檔案
│   ├── icon.ico              # 應用程式圖示
│   └── screenshots/          # 截圖資料夾（放 PNG/JPG 即會於左側底部顯示縮圖）
├── COMMANDS/                  # 指令檔案目錄
│   ├── linux.txt             # 基礎 Linux 指令
│   ├── command_simple.txt    # 4CAM 專用指令
│   └── download.txt          # 檔案下載指令
├── REF/                       # 參考檔案目錄
│   └── Command.txt           # 預設指令檔案
├── LOG/                       # 日誌檔案目錄
└── dist/                      # 打包輸出目錄
```

## 指令檔案說明

### COMMANDS/ 目錄
- **linux.txt**：基礎 Linux 系統指令
  - 系統資訊查詢（uname、df、ps）
  - 檔案操作（rm、ls）
  - 系統控制（reboot）
  
- **command_simple.txt**：4CAM 專用診斷指令
  - DUT 基本資料讀取（diag -g）
  - 四鏡頭拍照指令（diag -s snapshot）
  - 影片錄製指令（hd_video_record）
  
- **download.txt**：檔案下載相關指令
  - 檔案列表檢查（ls、find）
  - 檔案搜尋與計數
  - 下載清單產生

### REF/ 目錄
- **Command.txt**：預設指令檔案，包含常用的 4CAM 測試指令

## 版本資訊
- **版本**：v1.9.3
- **更新日期**：2025-01-27
- **新增/變更**：
  - **頂部工具列布局**：重新設計頂部區域，包含標題、通用按鍵（說明、清空、存取LOG）
  - **工具列分離**：將「每次下指令清除舊訊息」勾選框移至獨立工具列
  - **版本設定移動**：應用程式版本設定移至「設定」標籤頁
  - **介面優化**：左側改為 `ttk.Notebook` 五標籤頁（指令 / LINUX 指令 / 手動指令 / 檔案傳輸 / 設定）
  - **指令管理**：新增三個專用指令檔案（linux.txt、command_simple.txt、download.txt）
  - **字體控制**：支援左側視窗（預設10）、右側視窗（預設12）、彈出視窗（預設12）獨立字體調整
  - **智能 Tooltip**：Tooltip 3 秒後自動消失，支援 Combobox 下拉選單懸停提示
  - **統一按鍵**：所有「開啟指令表」按鍵統一命名，分別開啟對應的指令檔案
  - **檔案傳輸優化**：固定使用 download.txt，移除不必要的檔案選擇功能
  - **Linux 指令簡化**：移除指令類型選擇器，固定使用 linux.txt
  - **設定保存**：自動保存視窗大小、連線設定、字體大小等配置
  - **錯誤處理**：完整的 try-except 錯誤處理機制
  - **打包支援**：提供批次檔和 Python 兩種打包方式

## 開發者
- **作者**：AI 助手
- **GitHub**：https://github.com/JOVIANpega/4CAM_DEBUG_TOOL

## 授權
本專案採用 MIT 授權條款。

## 聯絡資訊
如有問題或建議，請透過 GitHub Issues 聯繫。
