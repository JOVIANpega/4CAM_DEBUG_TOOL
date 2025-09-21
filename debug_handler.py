#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
debug_handler.py - 4CAM DEBUG TOOL 除錯處理模組

主要功能：
- 全域例外處理機制
- 詳細錯誤日誌記錄
- 使用者友善的錯誤提示
- 程式崩潰防護與恢復
- 效能監控與記憶體追蹤

作者：AI 助手
版本：1.0.0
"""

import os
import sys
import traceback
import logging
import threading
import time
import functools
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from datetime import datetime
from typing import Callable, Any, Optional
import psutil
import gc


class DebugHandler:
    """除錯處理器 - 提供全方位的錯誤處理與監控功能"""
    
    def __init__(self, app_name: str = "4CAM_DEBUG_TOOL"):
        self.app_name = app_name
        self.log_dir = Path("LOG")
        self.log_dir.mkdir(exist_ok=True)
        
        # 設定日誌
        self._setup_logging()
        
        # 錯誤統計
        self.error_count = 0
        self.warning_count = 0
        self.last_error_time = None
        
        # 效能監控
        self.performance_data = {
            'start_time': time.time(),
            'memory_usage': [],
            'cpu_usage': [],
        }
        
        # 啟動監控執行緒
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._performance_monitor, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info(f"=== {app_name} 除錯系統已啟動 ===")
        self.logger.info(f"Python 版本: {sys.version}")
        self.logger.info(f"系統: {os.name} - {sys.platform}")
    
    def _setup_logging(self):
        """設定日誌系統"""
        log_filename = self.log_dir / f"{datetime.now().strftime('%Y%m%d_%H%M')}_debug.log"
        
        # 設定日誌格式
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(threadName)-10s | %(funcName)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 檔案處理器
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # 主控台處理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # 設定 logger
        self.logger = logging.getLogger(self.app_name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()  # 清除預設處理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # 防止重複日誌
        self.logger.propagate = False
    
    def _performance_monitor(self):
        """效能監控執行緒"""
        while self.monitoring_active:
            try:
                # 記憶體使用量
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent()
                
                self.performance_data['memory_usage'].append(memory_mb)
                self.performance_data['cpu_usage'].append(cpu_percent)
                
                # 保持最近 100 筆記錄
                if len(self.performance_data['memory_usage']) > 100:
                    self.performance_data['memory_usage'].pop(0)
                    self.performance_data['cpu_usage'].pop(0)
                
                # 記憶體警告
                if memory_mb > 500:  # 超過 500MB
                    self.logger.warning(f"記憶體使用量過高: {memory_mb:.1f} MB")
                
                time.sleep(10)  # 每 10 秒監控一次
                
            except Exception as e:
                self.logger.error(f"效能監控錯誤: {e}")
                time.sleep(30)  # 錯誤後等待更長時間
    
    def exception_handler(self, exc_type, exc_value, exc_traceback):
        """全域例外處理器"""
        if issubclass(exc_type, KeyboardInterrupt):
            # 使用者中斷，正常退出
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        self.error_count += 1
        self.last_error_time = datetime.now()
        
        # 記錄詳細錯誤資訊
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        self.logger.critical(f"未捕獲的例外:\n{error_msg}")
        
        # 系統資訊
        self._log_system_info()
        
        # 顯示使用者友善的錯誤訊息
        self._show_user_error_dialog(exc_type.__name__, str(exc_value))
    
    def _log_system_info(self):
        """記錄系統資訊"""
        try:
            process = psutil.Process(os.getpid())
            self.logger.error(f"系統資訊 - 記憶體: {process.memory_info().rss / 1024 / 1024:.1f} MB")
            self.logger.error(f"系統資訊 - CPU: {process.cpu_percent():.1f}%")
            self.logger.error(f"系統資訊 - 執行緒數: {threading.active_count()}")
            self.logger.error(f"系統資訊 - GC 物件數: {len(gc.get_objects())}")
        except Exception as e:
            self.logger.error(f"無法取得系統資訊: {e}")
    
    def _show_user_error_dialog(self, error_type: str, error_msg: str):
        """顯示使用者友善的錯誤對話框"""
        try:
            # 建立簡化的錯誤訊息
            user_msg = self._simplify_error_message(error_type, error_msg)
            
            # 顯示錯誤對話框
            root = tk.Tk()
            root.withdraw()  # 隱藏主視窗
            
            result = messagebox.askyesno(
                "程式錯誤",
                f"程式遇到錯誤，但已自動處理：\n\n{user_msg}\n\n"
                f"是否要繼續執行程式？\n\n"
                f"詳細錯誤資訊已記錄到日誌檔案中。",
                icon='warning'
            )
            
            root.destroy()
            
            if not result:
                self.logger.info("使用者選擇結束程式")
                sys.exit(1)
                
        except Exception as e:
            self.logger.error(f"顯示錯誤對話框失敗: {e}")
    
    def _simplify_error_message(self, error_type: str, error_msg: str) -> str:
        """簡化錯誤訊息，讓使用者更容易理解"""
        error_translations = {
            'ConnectionError': '網路連線錯誤',
            'FileNotFoundError': '檔案不存在',
            'PermissionError': '權限不足',
            'TimeoutError': '連線逾時',
            'ValueError': '資料格式錯誤',
            'KeyError': '設定項目缺失',
            'ImportError': '模組載入失敗',
            'MemoryError': '記憶體不足',
        }
        
        simplified_type = error_translations.get(error_type, error_type)
        
        # 截取錯誤訊息前 100 個字元
        simplified_msg = error_msg[:100] + "..." if len(error_msg) > 100 else error_msg
        
        return f"{simplified_type}: {simplified_msg}"
    
    def safe_execute(self, func: Callable, *args, **kwargs) -> Any:
        """安全執行函數，自動捕獲並處理例外"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"函數 {func.__name__} 執行失敗: {e}")
            self.logger.debug(f"詳細錯誤: {traceback.format_exc()}")
            return None
    
    def safe_decorator(self, show_error: bool = False):
        """安全執行裝飾器"""
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    self.logger.error(f"函數 {func.__name__} 執行失敗: {e}")
                    self.logger.debug(f"詳細錯誤: {traceback.format_exc()}")
                    
                    if show_error:
                        try:
                            messagebox.showerror("執行錯誤", f"操作失敗: {str(e)}")
                        except:
                            pass
                    
                    return None
            return wrapper
        return decorator
    
    def log_performance_summary(self):
        """記錄效能摘要"""
        if not self.performance_data['memory_usage']:
            return
        
        runtime = time.time() - self.performance_data['start_time']
        avg_memory = sum(self.performance_data['memory_usage']) / len(self.performance_data['memory_usage'])
        max_memory = max(self.performance_data['memory_usage'])
        avg_cpu = sum(self.performance_data['cpu_usage']) / len(self.performance_data['cpu_usage'])
        
        self.logger.info(f"=== 效能摘要 ===")
        self.logger.info(f"執行時間: {runtime:.1f} 秒")
        self.logger.info(f"平均記憶體: {avg_memory:.1f} MB")
        self.logger.info(f"最大記憶體: {max_memory:.1f} MB")
        self.logger.info(f"平均 CPU: {avg_cpu:.1f}%")
        self.logger.info(f"錯誤次數: {self.error_count}")
        self.logger.info(f"警告次數: {self.warning_count}")
    
    def cleanup(self):
        """清理資源"""
        self.monitoring_active = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        self.log_performance_summary()
        self.logger.info(f"=== {self.app_name} 除錯系統已關閉 ===")


# 全域除錯處理器實例
debug_handler = DebugHandler()

# 設定全域例外處理器
sys.excepthook = debug_handler.exception_handler

# 提供便利的裝飾器
safe_execute = debug_handler.safe_decorator()
safe_execute_with_error = debug_handler.safe_decorator(show_error=True)


def setup_debug_for_app():
    """為應用程式設定除錯機制"""
    import atexit
    atexit.register(debug_handler.cleanup)
    
    debug_handler.logger.info("應用程式除錯機制已設定完成")


if __name__ == "__main__":
    # 測試除錯處理器
    setup_debug_for_app()
    
    @safe_execute
    def test_function():
        raise ValueError("測試錯誤")
    
    test_function()
    print("除錯處理器測試完成")
