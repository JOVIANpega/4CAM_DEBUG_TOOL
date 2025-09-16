# 4CAM_DEBUG_TOOL

## 專案簡介
4CAM_DEBUG_TOOL 是一個用於 4 攝影機 DUT（Device Under Test）SSH 控制工具，透過圖形化介面提供便捷的指令執行和檔案管理功能。

## 主要功能
- **SSH 連線管理**：支援 DUT SSH 連線測試與狀態監控
- **指令執行**：從 Command.txt 載入或手動輸入指令執行
- **檔案複製**：支援萬用字元檔案複製功能
- **連線狀態指示器**：即時顯示 SSH 連線狀態（綠色/黃色/黑色）
- **GUI 設定保存**：自動保存視窗大小和分割視窗位置
- **字體大小調整**：支援動態調整介面字體大小

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

### 3. 使用說明
1. 輸入 DUT IP 位址和使用者名稱
2. 點擊「測試連線」確認 SSH 連線
3. 載入指令檔案或手動輸入指令
4. 執行指令並查看回傳結果
5. 使用檔案複製功能下載 DUT 檔案

## 檔案結構
```
4CAM_DEBUG_TOOL/
├── main.py              # 主程式入口
├── ssh_client.py        # SSH 客戶端管理
├── build_exe.bat        # EXE 打包腳本
├── assets/              # 資源檔案
├── COMMANDS/            # 指令檔案目錄
├── REF/                 # 參考檔案目錄
└── dist/                # 打包輸出目錄
```

## 版本資訊
- **版本**：v1.1.0
- **更新日期**：2025-01-16
- **新增功能**：
  - 連線狀態指示器
  - GUI 設定保存
  - 檔案高亮顯示優化
  - 左右視窗可調整大小

## 開發者
- **作者**：AI 助手
- **GitHub**：https://github.com/JOVIANpega/4CAM_DEBUG_TOOL

## 授權
本專案採用 MIT 授權條款。

## 聯絡資訊
如有問題或建議，請透過 GitHub Issues 聯繫。
