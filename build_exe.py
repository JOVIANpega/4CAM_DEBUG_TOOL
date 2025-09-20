#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4CAM_DEBUG_TOOL EXE 打包工具
"""

import os
import sys
import subprocess
import shutil
import re
from pathlib import Path

def run_command(cmd, check=True):
    """執行命令並返回結果"""
    print(f"執行: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"錯誤: {e}")
        if e.stderr:
            print(f"錯誤輸出: {e.stderr}")
        return False

def check_python():
    """檢查 Python 環境"""
    print("檢查 Python 環境...")
    try:
        result = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Python 版本: {result.stdout.strip()}")
            return True
    except Exception as e:
        print(f"Python 檢查失敗: {e}")
    return False

def check_pyinstaller():
    """檢查並安裝 PyInstaller"""
    print("檢查 PyInstaller...")
    try:
        import PyInstaller
        print("PyInstaller 已安裝")
        return True
    except ImportError:
        print("正在安裝 PyInstaller...")
        return run_command(f"{sys.executable} -m pip install pyinstaller")
    except Exception as e:
        print(f"PyInstaller 檢查失敗: {e}")
        return False

def create_version_info():
    """創建版本資訊檔案"""
    print("創建版本資訊檔案...")
    try:
        result = subprocess.run([sys.executable, "create_version_info.py"], 
                              capture_output=True, text=True, check=True)
        if os.path.exists("version_info.txt"):
            print("版本資訊檔案創建成功")
            return True
    except Exception as e:
        print(f"版本資訊創建失敗: {e}")
    return False

def get_version():
    """從版本資訊檔案取得版本號"""
    try:
        with open("version_info.txt", "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r"StringStruct\('FileVersion', '([^']+)'\)", content)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"讀取版本號失敗: {e}")
    return "v1.9.1"

def clean_old_files():
    """清理舊的建置檔案"""
    print("清理舊的建置檔案...")
    dirs_to_clean = ["build", "dist", "__pycache__"]
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"已刪除: {dir_name}")
            except Exception as e:
                print(f"刪除 {dir_name} 失敗: {e}")

def create_commands_dir():
    """創建 COMMANDS 目錄和預設檔案"""
    print("檢查 COMMANDS 目錄...")
    if not os.path.exists("COMMANDS"):
        os.makedirs("COMMANDS")
        print("已創建 COMMANDS 目錄")
    
    linux_txt = "COMMANDS/linux.txt"
    if not os.path.exists(linux_txt):
        print("創建預設 linux.txt...")
        content = """# 常用 LINUX 指令
列出 /mnt/usr/ 所有檔案 = ls -la /mnt/usr/
刪除 /mnt/usr/ JPG 檔 = rm -f /mnt/usr/*.jpg
刪除 /mnt/usr/ YUV 檔 = rm -f /mnt/usr/*.yuv
刪除 /var/vsp/ JPG 檔 = rm -f /var/vsp/*.jpg
刪除 /var/vsp/ YUV 檔 = rm -f /var/vsp/*.yuv
顯示系統資訊 = uname -a
顯示磁碟使用量 = df -h
顯示記憶體使用量 = free -h
顯示目前目錄詳細檔案 = ls -la
列出根目錄檔案 = ls -la /
列出臨時目錄檔案 = ls -la /tmp
列出使用者目錄檔案 = ls -la /mnt/usr
網路連線 = netstat -an
網路介面 = ifconfig
路由表 = route -n
核心版本 = cat /proc/version
CPU 資訊 = cat /proc/cpuinfo
記憶體資訊 = cat /proc/meminfo
系統運行時間 = uptime
系統時間 = date
硬體時鐘 = hwclock
掛載點 = mount
已載入模組 = lsmod
USB 設備 = lsusb
PCI 設備 = lspci
I2C 匯流排 0 = i2cdetect -y 0
I2C 匯流排 1 = i2cdetect -y 1
最近核心訊息 = dmesg | tail -20
錯誤訊息過濾 = dmesg | grep -i error
攝影機訊息過濾 = dmesg | grep -i camera
VSP 目錄 = ls -la /var/vsp
TMP TAR 目錄 = ls -la /tmp/tar
檢查錄影程序 = ps aux | grep hd_video
檢查診斷程序 = ps aux | grep diag
停止錄影程序 = killall hd_video_record_with_vsp_4dev_smart2_pega_dre
檢查 /tmp 空間 = df -h /tmp
檢查 /var/vsp 空間 = df -h /var/vsp
檢查 /mnt/usr 空間 = df -h /mnt/usr
系統負載 = cat /proc/loadavg"""
        
        with open(linux_txt, "w", encoding="utf-8") as f:
            f.write(content)
        print("已創建 linux.txt")

def build_exe():
    """建置 EXE 檔案"""
    print("=" * 50)
    print("4CAM_DEBUG_TOOL EXE 打包工具")
    print("=" * 50)
    
    # 檢查環境
    if not check_python():
        print("Python 環境檢查失敗")
        return False
    
    if not check_pyinstaller():
        print("PyInstaller 檢查失敗")
        return False
    
    # 清理舊檔案
    clean_old_files()
    
    # 創建版本資訊
    if not create_version_info():
        print("版本資訊創建失敗")
        return False
    
    # 取得版本號
    version = get_version()
    exe_name = f"4CAM_DEBUG_TOOL_{version}"
    print(f"版本: {version}")
    print(f"EXE 名稱: {exe_name}")
    
    # 創建 COMMANDS 目錄
    create_commands_dir()
    
    # 建置命令
    cmd_parts = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconsole",
        "--version-file", "version_info.txt",
        "--add-data", "COMMANDS;COMMANDS",
        "--add-data", "REF;REF",
        "--add-data", "settings.json;.",
        "--name", exe_name,
        "main.py"
    ]
    
    # 如果有圖示檔案，加入圖示參數
    if os.path.exists("assets/icon.ico"):
        cmd_parts.insert(-2, "--icon=assets/icon.ico")
        print("使用自訂圖示打包...")
    else:
        print("未找到圖示檔案，使用預設圖示打包...")
    
    # 執行建置
    print("開始打包...")
    if not run_command(" ".join(cmd_parts), check=False):
        print("打包失敗！")
        return False
    
    # 檢查結果
    exe_path = f"dist/{exe_name}.exe"
    if os.path.exists(exe_path):
        print("=" * 50)
        print("打包成功！")
        print(f"檔案位置: {exe_path}")
        print("=" * 50)
        
        # 複製資源目錄
        copy_resources()
        
        # 顯示檔案資訊
        show_file_info(exe_path)
        
        return True
    else:
        print("EXE 檔案未成功生成！")
        return False

def copy_resources():
    """複製資源目錄到 dist"""
    print("複製資源目錄...")
    
    resources = ["COMMANDS", "REF", "assets"]
    for resource in resources:
        if os.path.exists(resource):
            dest = f"dist/{resource}"
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(resource, dest)
            print(f"- {resource} 目錄已複製")
    
    # 複製設定檔
    if os.path.exists("settings.json"):
        shutil.copy2("settings.json", "dist/settings.json")
        print("- settings.json 已複製")

def show_file_info(exe_path):
    """顯示檔案資訊"""
    print("\n檔案資訊:")
    try:
        stat = os.stat(exe_path)
        size_mb = stat.st_size / (1024 * 1024)
        print(f"檔案大小: {size_mb:.2f} MB")
        print(f"檔案路徑: {os.path.abspath(exe_path)}")
    except Exception as e:
        print(f"無法取得檔案資訊: {e}")
    
    print("\ndist 目錄內容:")
    try:
        for item in os.listdir("dist"):
            print(f"  {item}")
    except Exception as e:
        print(f"無法列出目錄內容: {e}")

def main():
    """主函數"""
    try:
        success = build_exe()
        if success:
            print("\n打包完成！")
            choice = input("是否開啟 dist 資料夾？(Y/N): ").upper()
            if choice == 'Y':
                os.startfile("dist")
        else:
            print("\n打包失敗！")
    except KeyboardInterrupt:
        print("\n\n用戶中斷操作")
    except Exception as e:
        print(f"\n發生錯誤: {e}")
    
    input("\n按 Enter 鍵結束...")

if __name__ == "__main__":
    main()
