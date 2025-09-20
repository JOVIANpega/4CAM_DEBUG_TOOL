# 4CAM_DEBUG_TOOL 安裝指南

## 系統需求

- **作業系統**：Windows 10/11
- **Python 版本**：3.7 或以上
- **網路連線**：用於 SSH 連線到 DUT 設備

## 安裝方式

### 方式一：直接使用 EXE 檔案（推薦）

1. 下載最新版本的 `4CAM_DEBUG_TOOL_v1.2.0.exe`
2. 雙擊執行即可，無需安裝 Python

### 方式二：從原始碼執行

1. **安裝 Python**
   ```bash
   # 確認 Python 版本
   python --version
   ```

2. **下載專案**
   ```bash
   git clone https://github.com/JOVIANpega/4CAM_DEBUG_TOOL.git
   cd 4CAM_DEBUG_TOOL
   ```

3. **安裝依賴套件**
   ```bash
   pip install -r requirements.txt
   ```

4. **執行程式**
   ```bash
   python main.py
   ```

### 方式三：打包為 EXE

1. **安裝 PyInstaller**
   ```bash
   pip install pyinstaller
   ```

2. **執行打包腳本**
   ```bash
   # Windows
   build_exe.bat
   
   # 或手動執行
   pyinstaller --onefile --noconsole --icon=assets/icon.ico main.py
   ```

## 首次設定

### 1. 連線設定
- **DUT IP**：預設 `192.168.11.143`
- **PC IP**：預設 `192.168.11.142`（會自動偵測）
- **使用者名稱**：預設 `root`
- **密碼**：DUT 不需要密碼

### 2. 檔案路徑設定
- **指令檔**：`REF/Command.txt`
- **Linux 指令檔**：`COMMANDS/linux.txt`
- **目標資料夾**：`D:/VALO360/4CAM`

### 3. 建立必要資料夾
程式會自動建立以下資料夾：
- `LOG/` - 儲存執行日誌
- `D:/VALO360/` - 檔案傳輸目標根目錄

## 故障排除

### 常見問題

1. **SSH 連線失敗**
   - 檢查 DUT IP 位址是否正確
   - 確認 DUT 設備已開機且支援 SSH
   - 檢查網路連線

2. **Python 模組找不到**
   ```bash
   pip install paramiko
   ```

3. **權限問題**
   - 以系統管理員身分執行
   - 檢查目標資料夾寫入權限

4. **打包失敗**
   - 確認 PyInstaller 已正確安裝
   - 檢查圖示檔案是否存在

### 支援的指令格式

- **Command.txt 格式**：`指令名稱 = 完整指令`
- **Linux 指令檔格式**：`名稱 = 指令`
- **檔案傳輸**：支援萬用字元，如 `/mnt/usr/*.jpg`

## 聯絡資訊

如有問題，請透過 GitHub Issues 聯繫。
