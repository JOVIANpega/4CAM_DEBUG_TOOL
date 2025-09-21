# -*- coding: utf-8 -*-
"""
SSH 工作器模組
負責使用 SSH 執行指令
"""
import threading
import time
import subprocess
import paramiko
from typing import List, Callable, Optional
from core.error_handler import get_error_handler

error_handler = get_error_handler()
log_debug = error_handler.log_debug
log_info = error_handler.log_info
log_error = error_handler.log_error
log_warning = error_handler.log_warning


class SSHWorker(threading.Thread):
    """SSH 工作器 - 使用 SSH 執行指令"""
    
    def __init__(self, cmd_list: List[str], end_str: str, timeout: int,
                 host: str, port: int, username: str, password: str,
                 on_data: Callable[[str, str], None],
                 on_status: Callable[[bool], None],
                 on_progress: Callable[[int], None],
                 on_finish: Callable[[], None],
                 stop_event: threading.Event):
        """
        初始化 SSH 工作器
        
        Args:
            cmd_list: 要執行的指令列表
            end_str: 結束字串
            timeout: 超時時間（秒）
            host: SSH 主機地址
            port: SSH 埠號
            username: 使用者名稱
            password: 密碼
            on_data: 資料回調函數 (text, tag)
            on_status: 狀態回調函數 (connected)
            on_progress: 進度回調函數 (progress)
            on_finish: 完成回調函數
            stop_event: 停止事件
        """
        super().__init__(daemon=True)
        
        # SSH 參數
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        
        # 指令參數
        self.cmd_list = cmd_list
        self.end_str = end_str
        self.timeout = timeout
        
        # 回調函數
        self.on_data = on_data
        self.on_status = on_status
        self.on_progress = on_progress
        self.on_finish = on_finish
        self.stop_event = stop_event
        
        # SSH 連線
        self.ssh_client = None
        self.connected = False
        
        log_debug(f"SSHWorker 初始化: 主機={host}:{port}, 使用者={username}, 指令數={len(cmd_list)}, 超時={timeout}s")
    
    def connect_ssh(self):
        """建立 SSH 連線"""
        try:
            log_info(f"正在連線到 SSH 主機 {self.host}:{self.port}")
            self.on_status(False)  # 連線中
            
            # 建立 SSH 客戶端
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 連線參數 - 強制使用密碼認證，關閉金鑰和代理
            connect_kwargs = {
                "hostname": self.host,
                "port": self.port,
                "username": self.username,
                "password": self.password,  # 即使是空字串也要傳入
                "timeout": 30,
                "auth_timeout": 30,
                "banner_timeout": 30,
                "look_for_keys": False,  # 關閉金鑰查找
                "allow_agent": False,    # 關閉 SSH 代理
            }
            
            # 建立連線
            self.ssh_client.connect(**connect_kwargs)
            self.connected = True
            
            log_info(f"SSH 連線成功: {self.username}@{self.host}:{self.port}")
            self.on_status(True)  # 已連線
            
            return True
            
        except Exception as e:
            log_error(f"SSH 連線失敗: {e}")
            self.on_status(False)  # 連線失敗
            self.connected = False
            
            # 顯示錯誤訊息
            error_msg = f"SSH 連線失敗\n\n主機: {self.host}:{self.port}\n使用者: {self.username}\n\n錯誤: {str(e)}"
            self.on_data(f"\n[錯誤] {error_msg}\n", "error")
            
            return False
    
    def execute_ssh_command(self, command: str) -> tuple:
        """執行單個 SSH 指令"""
        try:
            if not self.connected or not self.ssh_client:
                return -1, "", "SSH 未連線"
            
            log_debug(f"執行 SSH 指令: {command}")
            
            # 執行指令
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=self.timeout)
            
            # 讀取輸出
            stdout_data = stdout.read().decode("utf-8", errors="ignore")
            stderr_data = stderr.read().decode("utf-8", errors="ignore")
            return_code = stdout.channel.recv_exit_status()
            
            return return_code, stdout_data, stderr_data
            
        except Exception as e:
            log_error(f"執行 SSH 指令失敗: {e}")
            return -1, "", str(e)
    
    def run(self):
        """執行 SSH 任務"""
        try:
            log_info("開始執行 SSH 任務")
            
            # 建立 SSH 連線
            if not self.connect_ssh():
                self.on_finish()
                return
            
            # 顯示開始訊息
            self.on_data(f"\n[SSH] 已連線到 {self.username}@{self.host}:{self.port}\n", "info")
            self.on_data(f"[SSH] 開始執行 {len(self.cmd_list)} 個指令\n", "info")
            
            # 執行指令列表
            for i, cmd in enumerate(self.cmd_list):
                if self.stop_event.is_set():
                    log_info("SSH 任務被停止")
                    self.on_data("\n[SSH] 任務被使用者停止\n", "warning")
                    break
                
                # 更新進度
                progress = int((i / len(self.cmd_list)) * 100)
                self.on_progress(progress)
                
                # 顯示發送的指令
                self.on_data(f"\n[SSH 發送] {cmd}\n", "send")
                
                # 執行 SSH 指令
                return_code, stdout_data, stderr_data = self.execute_ssh_command(cmd)
                
                # 處理輸出
                if stdout_data:
                    self.on_data(stdout_data, None)
                
                if stderr_data:
                    self.on_data(f"[錯誤] {stderr_data}", "error")
                
                if return_code != 0:
                    self.on_data(f"[警告] 指令返回碼: {return_code}\n", "warning")
                
                # 檢查結束字串
                if self.end_str and self.end_str in stdout_data:
                    log_debug(f"找到結束字串: {self.end_str}")
                    self.on_data(f"\n[SSH] 找到結束字串 \"{self.end_str}\"，停止執行\n", "end")
                    break
                
                # 指令間延遲
                if i < len(self.cmd_list) - 1:  # 不是最後一個指令
                    time.sleep(0.5)
            
            # 完成進度
            self.on_progress(100)
            self.on_data(f"\n[SSH] 所有指令已執行完成\n", "purple")
            
        except Exception as e:
            log_error(f"SSH 執行錯誤: {e}")
            self.on_data(f"\n[錯誤] SSH 執行時發生錯誤: {e}\n", "error")
        
        finally:
            # 關閉 SSH 連線
            if self.ssh_client:
                try:
                    self.ssh_client.close()
                    log_debug("SSH 連線已關閉")
                except:
                    pass
            
            self.connected = False
            self.on_status(False)
            self.on_finish()
            log_debug("SSHWorker 執行完成")
