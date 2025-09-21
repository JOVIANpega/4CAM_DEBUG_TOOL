#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
settings_manager.py - 4CAM DEBUG TOOL 設定管理模組

主要功能：
- JSON 設定檔讀取與儲存
- 設定值驗證與預設值處理
- 設定變更通知機制
- 設定備份與還原

作者：AI 助手
版本：1.0.0
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Callable
import shutil
from datetime import datetime


class SettingsManager:
    """設定管理器 - 處理應用程式設定的讀取、儲存與管理"""
    
    def __init__(self, settings_file: str = "settings.json"):
        self.settings_file = Path(settings_file)
        self.backup_dir = Path("BACKUP")
        self.backup_dir.mkdir(exist_ok=True)
        
        # 預設設定
        self.default_settings = {
            # 連線設定
            'dut_ip': '192.168.11.143',
            'username': 'root',
            'timeout': 30,
            
            # 字體設定
            'font_size': 12,
            'left_font_size': 10,
            'popup_font_size': 12,
            
            # UI 設定
            'clear_output': True,
            'window_geometry': '900x560',
            'window_state': 'normal',
            
            # 檔案路徑設定
            'command_file': 'COMMANDS/Command.txt',
            'linux_file': 'COMMANDS/linux.txt',
            'download_file': 'COMMANDS/download.txt',
            
            # 進階設定
            'auto_connect': False,
            'save_logs': True,
            'max_log_files': 10,
            'performance_monitoring': True,
            
            # 版本資訊
            'app_version': 'v1.2.1',
            'last_updated': None,
        }
        
        self.settings = {}
        self.change_callbacks = {}
        
        # 載入設定
        self.load_settings()
    
    def load_settings(self) -> bool:
        """載入設定檔"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                
                # 合併預設設定與載入的設定
                self.settings = self.default_settings.copy()
                self.settings.update(loaded_settings)
                
                # 驗證設定
                self._validate_settings()
                
                print(f"✅ 設定檔載入成功: {self.settings_file}")
                return True
            else:
                # 使用預設設定
                self.settings = self.default_settings.copy()
                self.save_settings()
                print(f"📝 建立預設設定檔: {self.settings_file}")
                return True
                
        except Exception as e:
            print(f"❌ 設定檔載入失敗: {e}")
            # 使用預設設定
            self.settings = self.default_settings.copy()
            return False
    
    def save_settings(self) -> bool:
        """儲存設定檔"""
        try:
            # 備份現有設定檔
            if self.settings_file.exists():
                self._backup_settings()
            
            # 更新最後修改時間
            self.settings['last_updated'] = datetime.now().isoformat()
            
            # 儲存設定
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            
            print(f"✅ 設定檔儲存成功: {self.settings_file}")
            return True
            
        except Exception as e:
            print(f"❌ 設定檔儲存失敗: {e}")
            return False
    
    def _backup_settings(self):
        """備份設定檔"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"settings_backup_{timestamp}.json"
            shutil.copy2(self.settings_file, backup_file)
            
            # 清理舊備份（保留最新 5 個）
            self._cleanup_old_backups()
            
        except Exception as e:
            print(f"⚠️ 設定檔備份失敗: {e}")
    
    def _cleanup_old_backups(self, keep_count: int = 5):
        """清理舊的備份檔案"""
        try:
            backup_files = list(self.backup_dir.glob("settings_backup_*.json"))
            if len(backup_files) > keep_count:
                # 按修改時間排序，刪除最舊的
                backup_files.sort(key=lambda x: x.stat().st_mtime)
                for old_backup in backup_files[:-keep_count]:
                    old_backup.unlink()
                    print(f"🗑️ 刪除舊備份: {old_backup.name}")
        except Exception as e:
            print(f"⚠️ 清理備份檔案失敗: {e}")
    
    def _validate_settings(self):
        """驗證設定值"""
        # 驗證數值範圍
        numeric_validations = {
            'timeout': (1, 300),
            'font_size': (8, 32),
            'left_font_size': (8, 32),
            'popup_font_size': (8, 32),
            'max_log_files': (1, 100),
        }
        
        for key, (min_val, max_val) in numeric_validations.items():
            if key in self.settings:
                value = self.settings[key]
                if not isinstance(value, (int, float)) or not (min_val <= value <= max_val):
                    print(f"⚠️ 設定值 {key} 無效，使用預設值")
                    self.settings[key] = self.default_settings[key]
        
        # 驗證 IP 位址格式
        if 'dut_ip' in self.settings:
            ip = self.settings['dut_ip']
            if not self._is_valid_ip(ip):
                print(f"⚠️ IP 位址格式無效，使用預設值")
                self.settings['dut_ip'] = self.default_settings['dut_ip']
    
    def _is_valid_ip(self, ip: str) -> bool:
        """驗證 IP 位址格式"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                if not (0 <= int(part) <= 255):
                    return False
            return True
        except:
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """取得設定值"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any, save: bool = True) -> bool:
        """設定值"""
        try:
            old_value = self.settings.get(key)
            self.settings[key] = value
            
            # 觸發變更回調
            if key in self.change_callbacks and old_value != value:
                for callback in self.change_callbacks[key]:
                    try:
                        callback(key, old_value, value)
                    except Exception as e:
                        print(f"⚠️ 設定變更回調失敗: {e}")
            
            # 自動儲存
            if save:
                return self.save_settings()
            return True
            
        except Exception as e:
            print(f"❌ 設定值設定失敗: {e}")
            return False
    
    def update(self, settings_dict: Dict[str, Any], save: bool = True) -> bool:
        """批次更新設定"""
        try:
            for key, value in settings_dict.items():
                self.set(key, value, save=False)
            
            if save:
                return self.save_settings()
            return True
            
        except Exception as e:
            print(f"❌ 批次設定更新失敗: {e}")
            return False
    
    def reset_to_default(self, keys: Optional[list] = None, save: bool = True) -> bool:
        """重置設定為預設值"""
        try:
            if keys is None:
                # 重置所有設定
                self.settings = self.default_settings.copy()
                print("🔄 所有設定已重置為預設值")
            else:
                # 重置指定設定
                for key in keys:
                    if key in self.default_settings:
                        self.settings[key] = self.default_settings[key]
                        print(f"🔄 設定 {key} 已重置為預設值")
            
            if save:
                return self.save_settings()
            return True
            
        except Exception as e:
            print(f"❌ 重置設定失敗: {e}")
            return False
    
    def add_change_callback(self, key: str, callback: Callable):
        """新增設定變更回調函數"""
        if key not in self.change_callbacks:
            self.change_callbacks[key] = []
        self.change_callbacks[key].append(callback)
    
    def remove_change_callback(self, key: str, callback: Callable):
        """移除設定變更回調函數"""
        if key in self.change_callbacks:
            try:
                self.change_callbacks[key].remove(callback)
                if not self.change_callbacks[key]:
                    del self.change_callbacks[key]
            except ValueError:
                pass
    
    def export_settings(self, export_file: str) -> bool:
        """匯出設定到檔案"""
        try:
            export_path = Path(export_file)
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            print(f"✅ 設定已匯出到: {export_path}")
            return True
        except Exception as e:
            print(f"❌ 設定匯出失敗: {e}")
            return False
    
    def import_settings(self, import_file: str, merge: bool = True) -> bool:
        """從檔案匯入設定"""
        try:
            import_path = Path(import_file)
            if not import_path.exists():
                print(f"❌ 匯入檔案不存在: {import_path}")
                return False
            
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_settings = json.load(f)
            
            if merge:
                # 合併設定
                self.settings.update(imported_settings)
            else:
                # 完全替換設定
                self.settings = imported_settings.copy()
                # 確保有所有必要的預設值
                for key, value in self.default_settings.items():
                    if key not in self.settings:
                        self.settings[key] = value
            
            # 驗證並儲存
            self._validate_settings()
            self.save_settings()
            
            print(f"✅ 設定已匯入自: {import_path}")
            return True
            
        except Exception as e:
            print(f"❌ 設定匯入失敗: {e}")
            return False
    
    def get_settings_info(self) -> Dict[str, Any]:
        """取得設定資訊摘要"""
        return {
            'settings_file': str(self.settings_file),
            'settings_count': len(self.settings),
            'last_updated': self.settings.get('last_updated'),
            'backup_count': len(list(self.backup_dir.glob("settings_backup_*.json"))),
            'file_size': self.settings_file.stat().st_size if self.settings_file.exists() else 0,
        }
    
    def __getitem__(self, key: str) -> Any:
        """支援字典式存取"""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any):
        """支援字典式設定"""
        self.set(key, value)
    
    def __contains__(self, key: str) -> bool:
        """支援 in 操作符"""
        return key in self.settings


if __name__ == "__main__":
    # 測試設定管理器
    settings = SettingsManager("test_settings.json")
    
    # 測試基本操作
    print(f"DUT IP: {settings.get('dut_ip')}")
    settings.set('dut_ip', '192.168.1.100')
    print(f"新的 DUT IP: {settings.get('dut_ip')}")
    
    # 測試回調
    def on_ip_change(key, old_val, new_val):
        print(f"IP 已變更: {old_val} -> {new_val}")
    
    settings.add_change_callback('dut_ip', on_ip_change)
    settings.set('dut_ip', '192.168.1.200')
    
    # 測試設定資訊
    info = settings.get_settings_info()
    print(f"設定資訊: {info}")
    
    # 清理測試檔案
    if Path("test_settings.json").exists():
        Path("test_settings.json").unlink()
    
    print("設定管理器測試完成")
