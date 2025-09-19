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


# ---------------------------
# 全域持久連線狀態（預設開啟保持連線）
_persist_lock = threading.Lock()
_persist_client: Optional[paramiko.SSHClient] = None
_persist_connected: bool = False
_persist_last_used: float = 0.0
_persist_idle_timeout_sec: int = 600  # 閒置 10 分鐘自動斷線
_idle_monitor_started = False


def _start_idle_monitor():
    global _idle_monitor_started
    if _idle_monitor_started:
        return

    def _monitor():
        global _persist_client, _persist_connected, _persist_last_used
        while True:
            try:
                time.sleep(5)
                with _persist_lock:
                    if _persist_client and _persist_connected:
                        idle = time.time() - _persist_last_used
                        if idle >= _persist_idle_timeout_sec:
                            try:
                                _persist_client.close()
                            except Exception:
                                pass
                            _persist_client = None
                            _persist_connected = False
                            log_info("持久 SSH 連線因閒置超時已自動關閉")
            except Exception:
                # 監控執行緒不因例外終止
                pass

    t = threading.Thread(target=_monitor, daemon=True)
    t.start()
    _idle_monitor_started = True


def force_disconnect_persistent_session():
    """提供外部呼叫的 API：強制關閉持久 SSH 連線"""
    global _persist_client, _persist_connected
    with _persist_lock:
        if _persist_client:
            try:
                _persist_client.close()
            except Exception:
                pass
        _persist_client = None
        _persist_connected = False
        log_info("已手動關閉持久 SSH 連線")


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
        self.use_persistent = True  # 預設保持連線模式
        
        log_debug(f"SSHWorker 初始化: 主機={host}:{port}, 使用者={username}, 指令數={len(cmd_list)}, 超時={timeout}s")
    
    def connect_ssh(self):
        """建立 SSH 連線"""
        try:
            global _persist_client, _persist_connected, _persist_last_used
            log_info(f"正在連線到 SSH 主機 {self.host}:{self.port}")
            self.on_status(False)  # 連線中
            
            # 嘗試重用持久連線
            _start_idle_monitor()
            if self.use_persistent:
                with _persist_lock:
                    if _persist_client and _persist_connected:
                        # 驗證傳輸是否仍可用
                        transport = _persist_client.get_transport()
                        if transport and transport.is_active():
                            self.ssh_client = _persist_client
                            self.connected = True
                            _persist_last_used = time.time()
                            log_info("重用持久 SSH 連線")
                            self.on_status(True)
                            return True
                        else:
                            # 清理失效的持久連線
                            try:
                                _persist_client.close()
                            except Exception:
                                pass
                            _persist_client = None
                            _persist_connected = False
            
            # 建立新的 SSH 客戶端
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Keep-Alive 將在連線成功後設定
            
            # 連線參數 - 針對 Dropbear SSH 優化
            connect_kwargs = {
                "hostname": self.host,
                "port": self.port,
                "username": self.username,
                "timeout": 30,
                "auth_timeout": 30,      # 認證超時
                "banner_timeout": 30,    # banner 超時
                "look_for_keys": False,  # 關閉金鑰查找
                "allow_agent": False,    # 關閉 SSH 代理
                "gss_auth": False,       # 關閉 GSS 認證
                "gss_kex": False,        # 關閉 GSS 金鑰交換
                "disabled_algorithms": {'keys': ['rsa-sha2-256', 'rsa-sha2-512']},  # 某些舊版本相容性
                "sock": None,            # 確保使用新的 socket
            }

            # 退避重試（處理 banner 讀取/認證暫時失敗）
            backoffs = [2, 5, 10]
            last_error: Optional[Exception] = None

            for attempt, delay in enumerate(backoffs, start=1):
                # 添加延遲避免過於頻繁的嘗試
                time.sleep(delay)
                self.on_data(f"[提示] 裝置忙碌，{delay}s 後自動重試 (第{attempt}/3次)\n", "warning")

                try:
                    # 先嘗試不帶任何認證參數的連線
                    self.ssh_client.connect(**connect_kwargs)
                    self.connected = True
                except Exception as first_error:
                    last_error = first_error
                    log_debug(f"第一次連線嘗試失敗: {first_error}")

                    # 第二層：嘗試帶密碼（允許空密碼）
                    try:
                        connect_kwargs["password"] = self.password
                        self.ssh_client.connect(**connect_kwargs)
                        self.connected = True
                    except Exception as second_error:
                        last_error = second_error
                        log_debug(f"第二次連線嘗試失敗: {second_error}")

                        # 第三層：強制使用 none 認證
                        try:
                            # 重新建立客戶端
                            self.ssh_client.close()
                            self.ssh_client = paramiko.SSHClient()
                            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                            transport = paramiko.Transport((self.host, self.port))
                            transport.start_client(timeout=30)
                            transport.auth_none(self.username)

                            self.ssh_client._transport = transport
                            self.connected = True
                            log_info("使用 none 認證成功")
                        except Exception as third_error:
                            last_error = third_error
                            log_debug(f"第三次連線嘗試失敗: {third_error}")

                # 若已連線成功，跳出重試
                if self.connected:
                    break

                # 判斷是否繼續重試（banner/auth 類錯誤常為暫時性）
                err_text = str(last_error) if last_error else ""
                transient = (
                    "Error reading SSH protocol banner" in err_text or
                    "WinError 10054" in err_text or
                    "Authentication failed" in err_text or
                    "No authentication methods available" in err_text
                )
                if attempt < len(backoffs) and transient:
                    continue
                else:
                    break

            if not self.connected:
                if last_error:
                    raise last_error
                raise Exception("無法建立 SSH 連線")
            
            if not self.connected:
                raise Exception("無法建立 SSH 連線")
            
            log_info(f"SSH 連線成功: {self.username}@{self.host}:{self.port}")
            
            # 設定 Keep-Alive 以防止連線斷開
            transport = self.ssh_client.get_transport()
            if transport:
                transport.set_keepalive(30)  # 每 30 秒發送 keep-alive
                log_debug("已設定 SSH Keep-Alive (30秒)")
            
            # 建立/更新持久連線
            if self.use_persistent:
                with _persist_lock:
                    _persist_set = False
                    try:
                        _persist_client = self.ssh_client
                        _persist_connected = True
                        _persist_last_used = time.time()
                        _persist_set = True
                    finally:
                        if _persist_set:
                            log_debug("已建立持久 SSH 連線")
            
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
            # 背景執行支援：以 & 結尾的指令改為背景啟動並回傳 PID 與日誌路徑
            stripped = command.strip()
            is_background = stripped.endswith('&')
            if is_background:
                base_cmd = stripped[:-1].strip()
                if not base_cmd:
                    return -1, "", "背景指令為空"
                escaped_base = base_cmd.replace("'", "'\"'\"'")
                ts = int(time.time())
                log_file = f"/tmp/pega_bg_{ts}.log"
                pid_file = f"/tmp/pega_bg_{ts}.pid"
                # 使用登入殼層（sh -l -c）以載入環境變數，背景任務也保持相同行為
                wrapped_command = (
                    "sh -lc "
                    +
                    f"'{{ {escaped_base} >> {log_file} 2>&1 & pid=$!; echo PEGA_BG_STARTED:$pid; echo $pid > {pid_file}; echo PEGA_BG_LOG:{log_file}; }}' 2>&1"
                )
            else:
                # 使用登入 shell 執行指令（像 Teraterm 一樣）
                # 這樣可以載入完整的環境變數和 PATH 設定
                # 轉義單引號以避免指令注入
                escaped_command = command.replace("'", "'\"'\"'")
                # 使用登入殼層以載入完整環境（/etc/profile，/etc/shinit 等）
                wrapped_command = f"sh -lc '{escaped_command}' 2>&1"
            
            log_debug(f"包裝後的指令: {wrapped_command}")
            
            # 執行指令
            stdin, stdout, stderr = self.ssh_client.exec_command(wrapped_command, timeout=self.timeout)
            
            # 讀取輸出，加入硬逾時保護
            chan = stdout.channel
            try:
                chan.settimeout(1.0)
            except Exception:
                pass
            out_chunks = []
            err_chunks = []
            import time as _t
            start_ts = _t.time()
            while True:
                if self.timeout and self.timeout > 0 and (_t.time() - start_ts) > self.timeout:
                    try:
                        chan.close()
                    except Exception:
                        pass
                    return 124, ''.join(out_chunks), '命令逾時已中止'
                if chan.recv_ready():
                    try:
                        out_chunks.append(stdout.recv(4096).decode('utf-8', errors='ignore'))
                    except Exception:
                        pass
                if chan.recv_stderr_ready():
                    try:
                        err_chunks.append(stderr.recv(4096).decode('utf-8', errors='ignore'))
                    except Exception:
                        pass
                if chan.exit_status_ready():
                    break
                _t.sleep(0.05)

            return_code = chan.recv_exit_status()
            stdout_data = ''.join(out_chunks) if out_chunks else stdout.read().decode('utf-8', errors='ignore')
            stderr_data = ''.join(err_chunks) if err_chunks else stderr.read().decode('utf-8', errors='ignore')
            
            # 更新持久連線使用時間
            if self.use_persistent:
                with _persist_lock:
                    global _persist_last_used
                    _persist_last_used = time.time()
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
                
                # 攔截本機指令（不送到裝置）。目前支援：SHOW: 提示視窗/通知，DELAY/WAIT: 延遲
                local_cmd = cmd.strip()
                if local_cmd.lower().startswith("show:"):
                    msg = local_cmd[5:].strip()
                    if not msg:
                        msg = "(空白訊息)"
                    # 在輸出區顯示本機提示；上層可同時用通知區域顯示
                    self.on_data(f"\n[本機提示] {msg}\n", "info")
                    # 指令已處理，進入下一個
                    time.sleep(0.2)
                    continue

                lc = local_cmd.lower()
                if lc.startswith("delay ") or lc.startswith("delay:") or lc.startswith("wait ") or lc.startswith("wait:"):
                    # 支援格式：DELAY 5、DELAY:5、WAIT 500ms、WAIT:0.5s 等
                    import re
                    m = re.search(r"(?:delay|wait)[:\s]+([0-9]+(?:\.[0-9]+)?)(ms|s)?", lc)
                    if m:
                        val = float(m.group(1))
                        unit = m.group(2) or "s"
                        sleep_sec = val / 1000.0 if unit == "ms" else val
                        if sleep_sec < 0:
                            sleep_sec = 0
                        self.on_data(f"[本機等待] {sleep_sec:.3f}s\n", "info")
                        time.sleep(sleep_sec)
                        continue

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
            # 持久連線模式下，不做批次冷卻
            if not self.use_persistent:
                heavy_keywords = ["stream", "gst-launch", "ffmpeg", "play", "start_rtsp", "rtsp", "diag -g iv", "diag -s video", "diag -s ai", "diag -s audio play"]
                executed = "\n".join(self.cmd_list).lower()
                is_heavy = any(k in executed for k in heavy_keywords)
                cooldown = 10 if is_heavy else 5
                self.on_data(f"[提示] 裝置可能仍在釋放資源，{cooldown}s 後可再次執行\n", "warning")
                time.sleep(cooldown)
            
        except Exception as e:
            log_error(f"SSH 執行錯誤: {e}")
            self.on_data(f"\n[錯誤] SSH 執行時發生錯誤: {e}\n", "error")
        
        finally:
            # 持久連線模式下，保持連線不關閉；僅更新最後使用時間
            if self.use_persistent and self.ssh_client:
                with _persist_lock:
                    global _persist_last_used
                    _persist_last_used = time.time()
                # 維持 connected 狀態供上層顯示；透過通知列以 connected/disconnected 更新
                self.on_status(True)
            else:
                # 短連線模式：正常關閉
                if self.ssh_client:
                    try:
                        self.ssh_client.close()
                        log_debug("SSH 連線已關閉")
                    except Exception:
                        pass
                self.connected = False
                self.on_status(False)
        
            self.on_finish()
            log_debug("SSHWorker 執行完成")
