# 4CAM_DEBUG_TOOL

## 專案簡介
4CAM_DEBUG_TOOL 是一個用於 4 攝影機 DUT（Device Under Test）SSH 控制工具，透過圖形化介面提供便捷的指令執行和檔案管理功能。

## 主要功能
- **SSH 連線管理**：支援 DUT SSH 連線測試與狀態監控
- **Notebook 分頁**：左側以分頁管理三大區塊：指令、LINUX 指令、檔案傳輸
- **指令執行**：從 `REF/Command.txt` 載入或手動輸入指令執行
- **LINUX 指令檔**：從 `COMMANDS/linux.txt` 載入，清單前綴編號；分頁內新增「開啟指令檔」
- **檔案複製**：支援萬用字元（glob）檔案複製功能
- **連線狀態指示器**：即時顯示 SSH 連線狀態（綠/黃/黑）
- **GUI 設定保存**：自動保存視窗大小、檔案路徑、字體大小與選項
- **字體大小調整**：支援 + / - 全域調整
- **全域控制**：
  - 「每次下指令清除舊訊息」勾選（位於頂部）
  - 「使用說明」按鈕移至頂部（全域可用）
- **截圖預覽**：左側底部自動顯示 `assets/screenshots` 內的 PNG/JPG 縮圖

## 技術特色
- **Tkinter GUI**：使用 Python Tkinter 開發，穩定可靠
- **模組化設計**：函式獨立定義，易於維護
- **錯誤處理**：完整的 try-except 錯誤處理機制
- **PyInstaller 打包**：支援打包為單一 EXE 檔案
- **資源路徑管理**：支援打包後的相對路徑存取

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
1. 輸入 DUT IP 位址和使用者名稱
2. 點擊「測試連線」確認 SSH 連線
3. 在分頁「指令」選擇或載入 `Command.txt`，按「執行指令」
4. 在分頁「LINUX 指令」選擇 `linux.txt` 項、或手動輸入後執行；可直接按「開啟指令檔」
5. 在分頁「檔案傳輸」設定來源與目標後按「開始傳輸」
6. 需要清空舊訊息時可勾選頂部「每次下指令清除舊訊息」

## 檔案結構
```
4CAM_DEBUG_TOOL/
├── main.py              # 主程式入口
├── ssh_client.py        # SSH 客戶端管理
├── build_exe.bat        # EXE 打包腳本
├── assets/              # 資源檔案
│   └── screenshots/     # 截圖資料夾（放 PNG/JPG 即會於左側底部顯示縮圖）
├── COMMANDS/            # 指令檔案目錄
├── REF/                 # 參考檔案目錄
└── dist/                # 打包輸出目錄
```

## 版本資訊
- **版本**：v1.2.0
- **更新日期**：2025-09-18
- **新增/變更**：
  - 左側改為 `ttk.Notebook` 三分頁（指令 / LINUX 指令 / 檔案傳輸）
  - 頂部新增全域「每次下指令清除舊訊息」與「使用說明」
  - LINUX 分頁新增「開啟指令檔」按鈕
  - 新增截圖預覽區塊（assets/screenshots）
  - 關閉流程非阻塞化，縮短退出延遲；強化 SSH 關閉穩定性

## 開發者
- **作者**：AI 助手
- **GitHub**：https://github.com/JOVIANpega/4CAM_DEBUG_TOOL

## 授權
本專案採用 MIT 授權條款。

## 聯絡資訊
如有問題或建議，請透過 GitHub Issues 聯繫。
