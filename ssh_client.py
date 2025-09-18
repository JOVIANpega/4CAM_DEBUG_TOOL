# -*- coding: utf-8 -*-
"""
SSH 客戶端管理模組
基於成功案例 ssh_worker.py 實現
"""
import paramiko
import time
from typing import Tuple, Optional


class SSHClientManager:
    def __init__(self) -> None:
        self._client: paramiko.SSHClient | None = None
        self._sftp: paramiko.SFTPClient | None = None
        self._connected: bool = False

    @property
    def is_connected(self) -> bool:
        if not self._connected or self._client is None:
            return False
        
        # 檢查 SSH 連線是否真的活躍
        try:
            transport = self._client.get_transport()
            if transport is None or not transport.is_active():
                # 連線已斷開，更新狀態
                self._connected = False
                return False
            return True
        except Exception:
            # 檢查失敗，假設連線已斷開
            self._connected = False
            return False

    def connect(self, hostname: str, username: str, password: str | None, timeout: int = 15) -> None:
        if self.is_connected:
            return
        
        # 先關閉現有連線
        self.close()
        
        try:
            # 建立新的 SSH 客戶端
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 連線參數 - 針對 Dropbear SSH 優化
            connect_kwargs = {
                "hostname": hostname,
                "port": 22,
                "username": username,
                "timeout": timeout,
                "auth_timeout": 30,
                "banner_timeout": 30,
                "look_for_keys": False,
                "allow_agent": False,
                "gss_auth": False,
                "gss_kex": False,
                "disabled_algorithms": {'keys': ['rsa-sha2-256', 'rsa-sha2-512']},
                "sock": None,
            }

            # 退避重試（處理 banner 讀取/認證暫時失敗）
            backoffs = [2, 5, 10]
            last_error: Optional[Exception] = None

            for attempt, delay in enumerate(backoffs, start=1):
                # 添加延遲避免過於頻繁的嘗試
                time.sleep(delay)

                try:
                    # 先嘗試不帶任何認證參數的連線
                    self._client.connect(**connect_kwargs)
                    self._connected = True
                except Exception as first_error:
                    last_error = first_error

                    # 第二層：嘗試帶密碼（允許空密碼）
                    try:
                        connect_kwargs["password"] = password or ""
                        self._client.connect(**connect_kwargs)
                        self._connected = True
                    except Exception as second_error:
                        last_error = second_error

                        # 第三層：強制使用 none 認證
                        try:
                            # 重新建立客戶端
                            self._client.close()
                            self._client = paramiko.SSHClient()
                            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                            transport = paramiko.Transport((hostname, 22))
                            transport.start_client(timeout=timeout)
                            transport.auth_none(username)

                            self._client._transport = transport
                            self._connected = True
                        except Exception as third_error:
                            last_error = third_error

                # 若已連線成功，跳出重試
                if self._connected:
                    break

                # 判斷是否繼續重試（banner/auth 類錯誤常為暫時性）
                err_text = str(last_error) if last_error else ""
                transient = (
                    "Error reading SSH protocol banner" in err_text or
                    "WinError 10054" in err_text or
                    "Authentication failed" in err_text or
                    "No authentication methods available" in err_text or
                    "EOF during negotiation" in err_text
                )
                if attempt < len(backoffs) and transient:
                    continue
                else:
                    break

            if not self._connected:
                if last_error:
                    raise last_error
                raise Exception("無法建立 SSH 連線")
            
            # 設定 Keep-Alive 以防止連線斷開
            transport = self._client.get_transport()
            if transport:
                transport.set_keepalive(30)  # 每 30 秒發送 keep-alive
            
            # 開啟 SFTP
            try:
                self._sftp = self._client.open_sftp()
            except Exception:
                self._sftp = None
                
        except Exception as e:
            self.close()
            raise Exception(f"SSH 連線失敗: {e}")

    def close(self) -> None:
        """關閉 SSH 與 SFTP，盡量快速且不阻塞。"""
        try:
            # 優先關閉 SFTP，避免阻塞在資料傳輸
            if self._sftp:
                try:
                    self._sftp.close()
                except Exception:
                    pass
        finally:
            if self._client:
                try:
                    transport = None
                    try:
                        transport = self._client.get_transport()
                    except Exception:
                        transport = None

                    # 降低 keepalive，嘗試讓通道快速結束
                    if transport:
                        try:
                            transport.set_keepalive(0)
                        except Exception:
                            pass

                    self._client.close()

                    # 額外嘗試關閉底層 socket（若可取得）
                    try:
                        if transport and hasattr(transport, 'sock') and transport.sock:
                            try:
                                transport.sock.settimeout(0.2)
                            except Exception:
                                pass
                            try:
                                transport.sock.shutdown(2)
                            except Exception:
                                pass
                            try:
                                transport.sock.close()
                            except Exception:
                                pass
                    except Exception:
                        pass
                except Exception:
                    pass

        self._sftp = None
        self._client = None
        self._connected = False

    def exec_command(self, command: str, timeout: int | None = 30) -> Tuple[int, str, str]:
        if not self.is_connected or not self._client:
            raise Exception('SSH 尚未連線')
        
        try:
            # 使用登入 shell 執行指令（像 Teraterm 一樣）
            # 這樣可以載入完整的環境變數和 PATH 設定
            # 轉義單引號以避免指令注入
            escaped_command = command.replace("'", "'\"'\"'")
            # 先嘗試 bash，如果沒有則使用 sh
            wrapped_command = f"bash -l -c '{escaped_command}' 2>&1 || sh -l -c '{escaped_command}' 2>&1"
            
            stdin, stdout, stderr = self._client.exec_command(wrapped_command, timeout=timeout)
            out = stdout.read().decode('utf-8', errors='ignore')
            err = stderr.read().decode('utf-8', errors='ignore')
            exit_code = stdout.channel.recv_exit_status()
            return exit_code, out, err
            
        except Exception as e:
            # 檢查是否是連線問題
            error_msg = str(e)
            if 'session not active' in error_msg or 'transport' in error_msg.lower():
                # 連線已斷開，更新狀態
                self._connected = False
                raise Exception(f'SSH 連線已斷開: {error_msg}')
            else:
                raise Exception(f'執行指令失敗: {e}')

    def scp_download_system(self, hostname: str, username: str, remote_path: str, local_dir: str) -> Tuple[int, str, str]:
        """使用系統 scp 命令下載檔案"""
        import subprocess
        import os
        from pathlib import Path
        
        try:
            local_dir = Path(local_dir)
            # 確保本地目錄存在
            local_dir.mkdir(parents=True, exist_ok=True)
            
            # 對於 glob 模式，需要特殊處理
            if '*' in remote_path or '?' in remote_path:
                # 使用通配符時，需要先建立臨時目錄
                import tempfile
                import shutil
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    
                    cmd = [
                        'scp',
                        '-O',  # 使用舊版協議，相容性更好
                        '-o', 'StrictHostKeyChecking=no',
                        '-o', 'UserKnownHostsFile=/dev/null',
                        '-o', 'BatchMode=yes',  # 非互動模式，自動覆蓋
                        f'{username}@{hostname}:{remote_path}',
                        str(temp_path)
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        # 移動檔案到目標目錄，覆蓋已存在的檔案
                        for file_path in temp_path.glob('*'):
                            if file_path.is_file():
                                dest_file = local_dir / file_path.name
                                if dest_file.exists():
                                    dest_file.unlink()  # 刪除已存在的檔案
                                shutil.move(str(file_path), str(local_dir))
                    
                    return result.returncode, result.stdout, result.stderr
            else:
                # 單一檔案下載
                cmd = [
                    'scp',
                    '-O',  # 使用舊版協議，相容性更好
                    '-o', 'StrictHostKeyChecking=no',
                    '-o', 'UserKnownHostsFile=/dev/null',
                    '-o', 'BatchMode=yes',  # 非互動模式，自動覆蓋
                    f'{username}@{hostname}:{remote_path}',
                    str(local_dir)
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                return result.returncode, result.stdout, result.stderr
                
        except subprocess.TimeoutExpired:
            return 1, "", "SCP command timed out"
        except Exception as e:
            return 1, "", str(e)