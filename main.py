#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4CAM_DEBUG_TOOL - 4攝影機 DUT SSH 控制工具

主要用途：
- 透過 SSH 對 DUT 下指令（從 Command.txt 載入或手動輸入）
- 由 DUT 複製檔案到本機（支援萬用字元，透過 SFTP 實作）

設計重點：
- Tkinter 單檔 GUI、固定視窗、左右區塊：左側控制、右側回傳
- 字體大小預設 12，提供 + / - 調整，聯動整體 UI 與訊息顯示
- 按鈕 callback 以 on_ 開頭；函式保持精簡，模組化
- 資源路徑透過 get_resource_path() 取得，支援 PyInstaller 打包後讀取

作者：AI 助手
版本：1.0.0
檔案角色：應用程式進入點（入口檔名 main.py）
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import logging
import json
from pathlib import Path

# 本地模組
from ssh_client import SSHClientManager
from command_loader import load_commands_from_file, CommandItem


class Tooltip:
    """創建 tooltip 的工具類別"""
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind('<Enter>', self.on_enter)
        self.widget.bind('<Leave>', self.on_leave)
        
    def on_enter(self, event=None):
        """當滑鼠進入時顯示 tooltip"""
        if len(self.widget.get()) > 30:  # 只有當文字超過30個字元時才顯示
            self.show_tooltip()
            
    def on_leave(self, event=None):
        """當滑鼠離開時隱藏 tooltip"""
        self.hide_tooltip()
        
    def show_tooltip(self):
        """顯示 tooltip"""
        if self.tooltip_window or not self.text:
            return
            
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                        background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                        font=("Consolas", 10), wraplength=400)
        label.pack(ipadx=1)
        
    def hide_tooltip(self):
        """隱藏 tooltip"""
        tw = self.tooltip_window
        self.tooltip_window = None
        if tw:
            tw.destroy()


# ------------------------------
# Logging
# ------------------------------
def _setup_logging() -> None:
    log_path = Path('tool.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


_setup_logging()


# ------------------------------
# 工具函式
# ------------------------------
def get_resource_path(relative_path: str) -> str:
    """取得資源檔路徑，支援 PyInstaller。"""
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath('.')
    return os.path.join(base_path, relative_path)


# ------------------------------
# GUI 主視窗
# ------------------------------
class FourCamDebugTool:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title('4CAM_DEBUG_TOOL v1.0.0')
        self.root.geometry('900x560')
        self.root.resizable(True, True)
        self.root.minsize(800, 500)

        # 狀態
        self.font_size = 12
        self.current_commands: list[CommandItem] = []
        self.ssh = SSHClientManager()
        self.settings_file = Path('settings.json')
        self.connection_status = 'disconnected'  # disconnected, connecting, connected

        # 預設設定
        self.var_dut_ip = tk.StringVar(value='192.168.11.143')
        self.var_pc_ip = tk.StringVar(value='192.168.11.142')
        self.var_timeout = tk.StringVar(value='15')
        self.var_username = tk.StringVar(value='root')
        self.var_password = tk.StringVar(value='')  # 保留但不使用

        # 指令相關
        self.var_command_file = tk.StringVar(value=str(Path('REF') / 'Command.txt'))
        self.var_command_choice = tk.StringVar()

        # 檔案傳輸
        self.var_src_glob = tk.StringVar(value='/mnt/usr/*.jpg')
        self.var_dst_dir = tk.StringVar(value=str(Path('D:/VALO360/4CAM')))
        self.var_common_path = tk.StringVar(value='選擇常用路徑...')

        # 載入設定
        self._load_settings()
        
        self._build_layout()
        self._load_commands_initial()
        
        # 綁定視窗關閉事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # 自動嘗試連線
        self.root.after(1000, self._auto_connect)

    def _auto_connect(self) -> None:
        """自動嘗試連線"""
        try:
            # 檢查是否有有效的連線設定
            if not self.var_dut_ip.get().strip() or not self.var_username.get().strip():
                return
            
            self._append_output('程式啟動，自動嘗試連線...')
            self._run_bg(self._task_test_connection)
            
        except Exception:
            pass  # 靜默失敗，不影響程式啟動

    # ---------- 版面 ----------
    def _build_layout(self) -> None:
        left = ttk.Frame(self.root, padding=10)
        right = ttk.Frame(self.root, padding=10)
        left.pack(side=tk.LEFT, fill=tk.BOTH)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._build_left(left)
        self._build_right(right)

    def _build_left(self, parent: ttk.Frame) -> None:
        # 標題 + 字體
        top = ttk.Frame(parent)
        top.pack(fill=tk.X)
        ttk.Label(top, text='4CAM_DEBUG_TOOL', font=('Microsoft JhengHei', 14, 'bold')).pack(side=tk.LEFT)
        ttk.Button(top, text='+', width=3, command=self.on_font_plus).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(top, text='-', width=3, command=self.on_font_minus).pack(side=tk.RIGHT)

        # 連線設定
        lf_conn = ttk.LabelFrame(parent, text='連線設定', padding=8)
        lf_conn.pack(fill=tk.X, pady=(10, 6))
        self._add_labeled_entry(lf_conn, 'DUT IP', self.var_dut_ip, 0)
        self._add_labeled_entry(lf_conn, 'PC IP', self.var_pc_ip, 1)
        self._add_labeled_entry(lf_conn, 'Username', self.var_username, 2)
        # 移除密碼欄位，因為 DUT 不需要密碼
        self._add_labeled_entry(lf_conn, 'Timeout(sec)', self.var_timeout, 3)
        btns = ttk.Frame(lf_conn)
        btns.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))
        ttk.Button(btns, text='測試連線', command=self.on_test_connection).pack(side=tk.LEFT)
        ttk.Button(btns, text='重新載入指令', command=self.on_reload_commands).pack(side=tk.LEFT, padx=6)

        # 指令控制
        lf_cmd = ttk.LabelFrame(parent, text='指令控制（Command.txt）', padding=8)
        lf_cmd.pack(fill=tk.X, pady=(6, 6))
        ttk.Label(lf_cmd, text='指令檔').grid(row=0, column=0, sticky=tk.W)
        ent_cmdfile = ttk.Entry(lf_cmd, textvariable=self.var_command_file, width=42)
        ent_cmdfile.grid(row=0, column=1, sticky=tk.W, padx=(6, 0))
        ttk.Button(lf_cmd, text='選擇', command=self.on_pick_command_file).grid(row=0, column=2, padx=(6, 0))

        ttk.Label(lf_cmd, text='指令選擇').grid(row=1, column=0, sticky=tk.W, pady=(6, 0))
        self.cbo_commands = ttk.Combobox(lf_cmd, textvariable=self.var_command_choice, width=50, state='readonly')
        self.cbo_commands.grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=(6, 0), pady=(6, 0))
        self.cbo_commands.bind('<<ComboboxSelected>>', self.on_command_selected)
        ttk.Button(lf_cmd, text='執行指令', command=self.on_execute_selected_command).grid(row=2, column=2, sticky=tk.E, pady=(6, 0))

        # 常用 Linux 指令
        lf_manual = ttk.LabelFrame(parent, text='常用 Linux 指令', padding=8)
        lf_manual.pack(fill=tk.X)
        
        # 常用 Linux 指令列表（含說明）
        self.linux_commands = [
            'ls -la - 列出詳細檔案資訊',
            'ls -la / - 列出根目錄詳細資訊', 
            'ls -la /tmp - 列出臨時目錄檔案',
            'ls -la /mnt/usr - 列出使用者目錄檔案',
            'pwd - 顯示當前工作目錄',
            'whoami - 顯示當前使用者',
            'uname -a - 顯示系統資訊',
            'df -h - 顯示磁碟使用量',
            'free -h - 顯示記憶體使用量',
            'ps aux - 顯示所有執行程序',
            'top - 即時系統監控',
            'netstat -an - 顯示網路連線',
            'ifconfig - 顯示網路介面',
            'route -n - 顯示路由表',
            'cat /proc/version - 顯示核心版本',
            'cat /proc/cpuinfo - 顯示 CPU 資訊',
            'cat /proc/meminfo - 顯示記憶體資訊',
            'uptime - 顯示系統運行時間',
            'date - 顯示系統時間',
            'hwclock - 顯示硬體時鐘',
            'mount - 顯示掛載點',
            'umount - 卸載檔案系統',
            'find / -name "*.log" 2>/dev/null - 搜尋日誌檔案',
            'grep -r "error" /var/log 2>/dev/null - 搜尋錯誤訊息',
            'tail -f /var/log/messages - 即時監控系統訊息',
            'dmesg | tail -20 - 顯示最近核心訊息',
            'lsmod - 顯示已載入模組',
            'lsusb - 顯示 USB 設備',
            'lspci - 顯示 PCI 設備',
            'i2cdetect -y 0 - 偵測 I2C 匯流排 0',
            'i2cdetect -y 1 - 偵測 I2C 匯流排 1'
        ]
        
        self.var_manual = tk.StringVar(value=self.linux_commands[0])
        cbo_manual = ttk.Combobox(lf_manual, textvariable=self.var_manual, values=self.linux_commands, width=47, state='readonly')
        cbo_manual.grid(row=0, column=0, padx=(0, 6))
        ttk.Button(lf_manual, text='執行', command=self.on_execute_manual).grid(row=0, column=1)

        # 檔案傳輸
        lf_copy = ttk.LabelFrame(parent, text='檔案傳輸（DUT → PC）', padding=8)
        lf_copy.pack(fill=tk.X, pady=(6, 0))
        
        # 常用檔案路徑下拉選單
        ttk.Label(lf_copy, text='常用路徑').grid(row=0, column=0, sticky=tk.W)
        self.var_common_path = tk.StringVar()
        self.common_paths = [
            '選擇常用路徑...',
            '/mnt/usr/*.jpg - JPG 圖片檔案',
            '/mnt/usr/*.yuv - YUV 影像檔案', 
            '/mnt/usr/*.bin - BIN 二進位檔案',
            '/mnt/usr/*.yml - YML 設定檔案',
            '/mnt/usr/*.log - LOG 日誌檔案',
            '/tmp/*.jpg - 臨時 JPG 檔案',
            '/tmp/*.yuv - 臨時 YUV 檔案',
            '/tmp/*.bin - 臨時 BIN 檔案',
            '/var/vsp/*.bin - VSP 二進位檔案',
            '/var/vsp/*.yml - VSP 設定檔案'
        ]
        cbo_common = ttk.Combobox(lf_copy, textvariable=self.var_common_path, values=self.common_paths, 
                                 width=45, state='readonly')
        cbo_common.grid(row=0, column=1, sticky=tk.W, padx=(6, 0))
        cbo_common.bind('<<ComboboxSelected>>', self.on_common_path_selected)
        
        self._add_labeled_entry(lf_copy, '來源（DUT glob）', self.var_src_glob, 1, width=42)
        
        # 目標資料夾輸入欄和開啟按鍵
        ttk.Label(lf_copy, text='目標（PC 資料夾）').grid(row=2, column=0, sticky=tk.W)
        entry_frame = ttk.Frame(lf_copy)
        entry_frame.grid(row=2, column=1, sticky=tk.W, padx=(6, 0))
        ent_dst = ttk.Entry(entry_frame, textvariable=self.var_dst_dir, width=42)
        ent_dst.pack(side=tk.LEFT)
        ttk.Button(entry_frame, text='📁', command=self.on_open_destination_folder, width=3).pack(side=tk.LEFT, padx=(6, 0))
        
        btns2 = ttk.Frame(lf_copy)
        btns2.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))
        ttk.Button(btns2, text='使用說明', command=self.on_show_help).pack(side=tk.LEFT)
        ttk.Button(btns2, text='開始傳輸', command=self.on_copy_from_dut).pack(side=tk.LEFT, padx=6)

        for child in lf_conn.winfo_children() + lf_cmd.winfo_children() + lf_manual.winfo_children() + lf_copy.winfo_children():
            try:
                child.configure(font=('Microsoft JhengHei', self.font_size))
            except Exception:
                pass

    def _build_right(self, parent: ttk.Frame) -> None:
        # 標題 + 連線狀態指示器
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=tk.X)
        ttk.Label(top_frame, text='回傳內容', font=('Microsoft JhengHei', 12, 'bold')).pack(side=tk.LEFT)
        
        # 連線狀態指示器
        self.status_indicator = tk.Canvas(top_frame, width=20, height=20, highlightthickness=0)
        self.status_indicator.pack(side=tk.RIGHT, padx=(10, 0))
        self._update_connection_status('disconnected')
        
        self.txt_output = ScrolledText(parent, width=50, height=30, font=('Consolas', self.font_size))
        self.txt_output.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        
        # 設定文字標籤顏色
        self.txt_output.tag_configure("success", foreground="green", font=('Consolas', self.font_size, 'bold'))
        self.txt_output.tag_configure("error", foreground="red", font=('Consolas', self.font_size, 'bold'))
        self.txt_output.tag_configure("warning", foreground="orange", font=('Consolas', self.font_size, 'bold'))
        self.txt_output.tag_configure("info", foreground="blue", font=('Consolas', self.font_size, 'bold'))
        self.txt_output.tag_configure("file", foreground="purple", font=('Consolas', self.font_size, 'bold'))
        self.txt_output.tag_configure("path", foreground="darkgreen", font=('Consolas', self.font_size, 'bold'))
        
        # 檔案高亮標籤 - 移除背景色，JPG和YUV使用綠色
        self.txt_output.tag_configure("file_yuv", foreground="green", font=('Consolas', self.font_size, 'bold'))
        self.txt_output.tag_configure("file_jpg", foreground="green", font=('Consolas', self.font_size, 'bold'))
        self.txt_output.tag_configure("file_bin", foreground="darkgreen", font=('Consolas', self.font_size, 'bold'))
        self.txt_output.tag_configure("file_log", foreground="darkorange", font=('Consolas', self.font_size, 'bold'))
        self.txt_output.tag_configure("file_yml", foreground="darkmagenta", font=('Consolas', self.font_size, 'bold'))
        self.txt_output.tag_configure("file_other", foreground="black", font=('Consolas', self.font_size, 'bold'))
        
        # 特殊指令標籤
        self.txt_output.tag_configure("diag_sn", foreground="purple", font=('Consolas', self.font_size, 'bold'))

    def _update_connection_status(self, status: str) -> None:
        """更新連線狀態指示器"""
        self.connection_status = status
        self.status_indicator.delete("all")
        
        if status == 'connected':
            color = 'green'
        elif status == 'connecting':
            color = 'yellow'
        else:  # disconnected
            color = 'black'
        
        # 繪製圓圈
        self.status_indicator.create_oval(2, 2, 18, 18, fill=color, outline='gray', width=1)
        
        # 添加 tooltip
        tooltip_text = {
            'connected': 'SSH 連線成功',
            'connecting': 'SSH 連線中...',
            'disconnected': 'SSH 未連線'
        }
        
        # 綁定 tooltip
        self.status_indicator.bind('<Enter>', lambda e: self._show_status_tooltip(tooltip_text[status]))
        self.status_indicator.bind('<Leave>', lambda e: self._hide_status_tooltip())

    def _show_status_tooltip(self, text: str) -> None:
        """顯示狀態 tooltip"""
        x = self.status_indicator.winfo_rootx() + 10
        y = self.status_indicator.winfo_rooty() - 30
        self.status_tooltip = tw = tk.Toplevel(self.status_indicator)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=text, justify=tk.LEFT,
                        background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                        font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def _hide_status_tooltip(self) -> None:
        """隱藏狀態 tooltip"""
        if hasattr(self, 'status_tooltip'):
            self.status_tooltip.destroy()
            delattr(self, 'status_tooltip')

    def _add_labeled_entry(self, parent: ttk.Frame, label: str, var: tk.StringVar, row: int, width: int = 24, show: str = None) -> ttk.Entry:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=2)
        ent = ttk.Entry(parent, textvariable=var, width=width, show=show)
        ent.grid(row=row, column=1, sticky=tk.W, padx=(6, 0), pady=2)
        
        # 添加 Tooltip，並設定動態更新
        tooltip = Tooltip(ent, var.get() if var.get() else f"{label} 輸入欄位")
        
        # 當變數值改變時，更新 Tooltip 文字
        def update_tooltip(*args):
            new_text = var.get() if var.get() else f"{label} 輸入欄位"
            tooltip.text = new_text
        
        var.trace('w', update_tooltip)
        return ent

    # ---------- 指令載入 ----------
    def _load_commands_initial(self) -> None:
        path = Path(self.var_command_file.get())
        self._load_commands_from(path)

    # ---------- 設定檔案 ----------
    def _load_settings(self) -> None:
        """載入設定檔案"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # 載入視窗設定
                if 'window' in settings:
                    geom = settings['window'].get('geometry', '900x560')
                    self.root.geometry(geom)
                
                # 載入連線設定
                if 'connection' in settings:
                    conn = settings['connection']
                    self.var_dut_ip.set(conn.get('dut_ip', '192.168.11.143'))
                    self.var_pc_ip.set(conn.get('pc_ip', '192.168.11.142'))
                    self.var_username.set(conn.get('username', 'root'))
                    self.var_password.set(conn.get('password', ''))
                    self.var_timeout.set(str(conn.get('timeout', 15)))
                
                # 載入檔案設定
                if 'files' in settings:
                    files = settings['files']
                    self.var_command_file.set(files.get('command_file', str(Path('REF') / 'Command.txt')))
                    self.var_src_glob.set(files.get('src_glob', '/mnt/usr/*.jpg'))
                    self.var_dst_dir.set(files.get('dst_dir', str(Path('D:/VALO360/4CAM'))))
                
                # 載入字體設定
                if 'ui' in settings:
                    self.font_size = settings['ui'].get('font_size', 12)
                    
        except Exception as e:
            logging.error(f"載入設定失敗: {e}")

    def _save_settings(self) -> None:
        """儲存設定檔案"""
        try:
            settings = {
                'window': {
                    'geometry': self.root.geometry()
                },
                'connection': {
                    'dut_ip': self.var_dut_ip.get(),
                    'pc_ip': self.var_pc_ip.get(),
                    'username': self.var_username.get(),
                    'password': self.var_password.get(),
                    'timeout': int(self.var_timeout.get() or '15')
                },
                'files': {
                    'command_file': self.var_command_file.get(),
                    'src_glob': self.var_src_glob.get(),
                    'dst_dir': self.var_dst_dir.get()
                },
                'ui': {
                    'font_size': self.font_size
                }
            }
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logging.error(f"儲存設定失敗: {e}")

    def _load_commands_from(self, path: Path) -> None:
        try:
            self.current_commands = load_commands_from_file(path)
            display_items = [f"{c.name} = {c.command}" for c in self.current_commands]
            self.cbo_commands["values"] = display_items
            if display_items:
                self.cbo_commands.current(0)
                self.var_command_choice.set(display_items[0])
            self._append_output(f"已載入指令：{len(self.current_commands)} 項，來源 {path}")
        except Exception as exc:
            messagebox.showerror('錯誤', f'載入指令失敗：{exc}')

    # ---------- 事件 ----------
    def on_font_plus(self) -> None:
        if self.font_size < 20:
            self.font_size += 1
            self._apply_font_size()

    def on_font_minus(self) -> None:
        if self.font_size > 10:
            self.font_size -= 1
            self._apply_font_size()

    def on_pick_command_file(self) -> None:
        file_path = filedialog.askopenfilename(title='選擇 Command.txt', filetypes=[('Text', '*.txt'), ('All', '*.*')])
        if file_path:
            self.var_command_file.set(file_path)
            self._load_commands_from(Path(file_path))

    def on_reload_commands(self, *_args) -> None:
        self._load_commands_from(Path(self.var_command_file.get()))

    def on_command_selected(self, _evt) -> None:
        idx = self.cbo_commands.current()
        if 0 <= idx < len(self.current_commands):
            pass  # 不需要做任何事，因為指令選擇已經在下拉選單中顯示

    def on_test_connection(self) -> None:
        self._run_bg(self._task_test_connection)

    def on_execute_selected_command(self) -> None:
        idx = self.cbo_commands.current()
        if 0 <= idx < len(self.current_commands):
            cmd = self.current_commands[idx].command
            self._run_bg(lambda: self._task_exec_command(cmd))
        else:
            messagebox.showwarning('提醒', '沒有指令可執行')

    def on_execute_manual(self) -> None:
        selected = self.var_manual.get().strip()
        if not selected:
            messagebox.showwarning('提醒', '請選擇指令')
            return
        
        # 從選擇的文字中提取指令部分（去掉說明）
        if ' - ' in selected:
            cmd = selected.split(' - ')[0].strip()
        else:
            cmd = selected
            
        self._run_bg(lambda: self._task_exec_command(cmd))

    def on_show_help(self) -> None:
        """產生並開啟 HTML 使用說明文件"""
        try:
            html_content = self._generate_help_html()
            
            # 儲存 HTML 檔案
            help_file = Path('4CAM_DEBUG_TOOL_使用說明.html')
            with open(help_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # 使用預設瀏覽器開啟
            import webbrowser
            import os
            webbrowser.open(f'file://{os.path.abspath(help_file)}')
            
            self._append_output(f'已產生使用說明：{help_file.absolute()}')
            
        except Exception as exc:
            messagebox.showerror('錯誤', f'產生說明文件失敗：{exc}')

    def _generate_help_html(self) -> str:
        """產生 HTML 使用說明文件"""
        import datetime
        
        html_content = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>4CAM_DEBUG_TOOL 使用說明</title>
    <style>
        body {{
            font-family: 'Microsoft JhengHei', Arial, sans-serif;
            line-height: 1.6;
            margin: 40px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }}
        h3 {{
            color: #2980b9;
            margin-top: 20px;
        }}
        .section {{
            margin: 20px 0;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 5px;
        }}
        .code {{
            background: #2c3e50;
            color: #ecf0f1;
            padding: 10px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            margin: 10px 0;
            overflow-x: auto;
        }}
        .highlight {{
            background: #fff3cd;
            padding: 10px;
            border-left: 4px solid #ffc107;
            margin: 10px 0;
        }}
        .warning {{
            background: #f8d7da;
            padding: 10px;
            border-left: 4px solid #dc3545;
            margin: 10px 0;
        }}
        ul, ol {{
            margin: 10px 0;
            padding-left: 30px;
        }}
        li {{
            margin: 5px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #7f8c8d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>4CAM_DEBUG_TOOL 使用說明</h1>
        
        <div class="section">
            <h2>📋 工具概述</h2>
            <p><strong>4CAM_DEBUG_TOOL</strong> 是一個專為 4 攝影機 DUT（Device Under Test）設計的 SSH 控制工具，提供直觀的圖形介面來執行遠端指令和檔案傳輸。</p>
        </div>

        <div class="section">
            <h2>🔧 主要功能</h2>
            <ul>
                <li><strong>SSH 連線管理</strong>：自動連線到 DUT 設備</li>
                <li><strong>指令執行</strong>：支援預設指令和常用 Linux 指令</li>
                <li><strong>檔案傳輸</strong>：使用 SCP 從 DUT 下載檔案到 PC</li>
                <li><strong>設定保存</strong>：自動保存和載入使用者設定</li>
                <li><strong>字體調整</strong>：可調整介面字體大小</li>
            </ul>
        </div>

        <div class="section">
            <h2>🚀 快速開始</h2>
            <ol>
                <li><strong>啟動程式</strong>：執行 <code>python main.py</code> 或雙擊 EXE 檔案</li>
                <li><strong>檢查連線</strong>：程式會自動嘗試連線到 DUT</li>
                <li><strong>執行指令</strong>：選擇指令並點擊「執行指令」</li>
                <li><strong>檔案傳輸</strong>：設定來源和目標路徑，點擊「開始傳輸」</li>
            </ol>
        </div>

        <div class="section">
            <h2>⚙️ 連線設定</h2>
            <table>
                <tr><th>參數</th><th>預設值</th><th>說明</th></tr>
                <tr><td>DUT IP</td><td>192.168.11.143</td><td>DUT 設備的 IP 位址</td></tr>
                <tr><td>PC IP</td><td>192.168.11.142</td><td>本機 PC 的 IP 位址</td></tr>
                <tr><td>使用者名稱</td><td>root</td><td>SSH 登入帳號</td></tr>
                <tr><td>密碼</td><td>（空）</td><td>DUT 不需要密碼</td></tr>
                <tr><td>超時時間</td><td>30 秒</td><td>指令執行超時時間</td></tr>
            </table>
        </div>

        <div class="section">
            <h2>📁 檔案傳輸</h2>
            <h3>支援的來源格式：</h3>
            <ul>
                <li><strong>單一檔案</strong>：<code>/mnt/usr/image.jpg</code></li>
                <li><strong>Glob 模式</strong>：<code>/mnt/usr/*.jpg</code></li>
                <li><strong>多個檔案</strong>：<code>/mnt/usr/test_*.log</code></li>
            </ul>
            
            <h3>目標目錄：</h3>
            <ul>
                <li>支援 Windows 路徑格式：<code>D:\VALO360\4CAM</code></li>
                <li>如果目錄不存在，會自動建立</li>
                <li>已存在的檔案會被覆蓋</li>
            </ul>
            
            <div class="highlight">
                <strong>💡 提示：</strong>檔案傳輸使用 SCP 協議，確保網路連線穩定。
            </div>
        </div>

        <div class="section">
            <h2>⌨️ 指令操作</h2>
            <h3>預設指令（Command.txt）：</h3>
            <ul>
                <li>從 <code>REF/Command.txt</code> 載入預設指令</li>
                <li>支援下拉選單選擇</li>
                <li>指令格式：<code>指令名稱 = 完整指令</code></li>
            </ul>
            
            <h3>常用 Linux 指令：</h3>
            <ul>
                <li><code>ls -la</code>：列出檔案詳細資訊</li>
                <li><code>ps aux</code>：顯示執行中的程序</li>
                <li><code>df -h</code>：顯示磁碟使用量</li>
                <li><code>free -h</code>：顯示記憶體使用量</li>
                <li><code>top</code>：即時系統監控</li>
                <li><code>netstat -an</code>：顯示網路連線</li>
            </ul>
        </div>

        <div class="section">
            <h2>🎛️ 介面操作</h2>
            <h3>左側控制面板：</h3>
            <ul>
                <li><strong>連線設定</strong>：設定 DUT 和 PC 的 IP 位址</li>
                <li><strong>指令控制</strong>：載入和執行預設指令</li>
                <li><strong>常用指令</strong>：快速執行 Linux 指令</li>
                <li><strong>檔案傳輸</strong>：設定來源和目標路徑</li>
            </ul>
            
            <h3>右側輸出面板：</h3>
            <ul>
                <li>顯示指令執行結果</li>
                <li>顯示檔案傳輸狀態</li>
                <li>顯示錯誤訊息和除錯資訊</li>
                <li>支援「清空輸出」功能</li>
            </ul>
        </div>

        <div class="section">
            <h2>🔍 故障排除</h2>
            <h3>常見問題：</h3>
            <ol>
                <li><strong>SSH 連線失敗</strong>：
                    <ul>
                        <li>檢查 DUT IP 位址是否正確</li>
                        <li>確認 DUT 已開機且支援 SSH</li>
                        <li>檢查網路連線</li>
                    </ul>
                </li>
                <li><strong>指令執行失敗</strong>：
                    <ul>
                        <li>確認指令格式正確</li>
                        <li>檢查 DUT 環境變數</li>
                        <li>某些指令需要特定環境設定</li>
                    </ul>
                </li>
                <li><strong>檔案傳輸失敗</strong>：
                    <ul>
                        <li>檢查來源路徑是否存在</li>
                        <li>確認目標目錄權限</li>
                        <li>檢查磁碟空間</li>
                    </ul>
                </li>
            </ol>
        </div>

        <div class="warning">
            <strong>⚠️ 注意事項：</strong>
            <ul>
                <li>請確保 DUT 設備已正確設定網路連線</li>
                <li>某些 DUT 專用指令（如 diag）需要特定的環境變數</li>
                <li>檔案傳輸時請確保目標磁碟有足夠空間</li>
                <li>建議在執行重要操作前先測試連線</li>
            </ul>
        </div>

        <div class="section">
            <h2>📞 技術支援</h2>
            <p>如遇到問題，請檢查：</p>
            <ul>
                <li>程式輸出的錯誤訊息</li>
                <li>DUT 設備的狀態指示燈</li>
                <li>網路連線狀態</li>
                <li>防火牆設定</li>
            </ul>
        </div>

        <div class="footer">
            <p><strong>4CAM_DEBUG_TOOL</strong> - 版本 1.0.0</p>
            <p>專為 4 攝影機 DUT 設計的 SSH 控制工具</p>
            <p>生成時間：{}</p>
        </div>
    </div>
</body>
</html>"""
        
        return html_content.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    def on_copy_from_dut(self) -> None:
        """開始檔案傳輸"""
        src = self.var_src_glob.get().strip()
        dst = self.var_dst_dir.get().strip()
        if not src or not dst:
            messagebox.showwarning('提醒', '請輸入來源與目標路徑')
            return
        self._run_bg(lambda: self._task_copy_from_dut(src, dst))

    def on_common_path_selected(self, event=None) -> None:
        """處理常用路徑選擇"""
        selected = self.var_common_path.get()
        if selected and selected != '選擇常用路徑...':
            # 從選擇的文字中提取路徑部分（去掉說明）
            path = selected.split(' - ')[0]
            self.var_src_glob.set(path)
            
            # 根據檔案類型建議目標資料夾
            if '.jpg' in selected.lower():
                suggested_dst = r'D:\VALO360\4CAM\JPG'
            elif '.yuv' in selected.lower():
                suggested_dst = r'D:\VALO360\4CAM\YUV'
            elif '.bin' in selected.lower():
                suggested_dst = r'D:\VALO360\4CAM\BIN'
            elif '.yml' in selected.lower():
                suggested_dst = r'D:\VALO360\4CAM\CONFIG'
            elif '.log' in selected.lower():
                suggested_dst = r'D:\VALO360\4CAM\LOG'
            else:
                suggested_dst = r'D:\VALO360\4CAM'
            
            self.var_dst_dir.set(suggested_dst)
            self._append_output(f'已選擇：{selected}')
            self._append_output(f'來源路徑：{path}')
            self._append_output(f'建議目標：{suggested_dst}')
            
            # 檢查 DUT 上的檔案並顯示資訊
            self._run_bg(lambda: self._task_check_files_and_show_info(path))

    def on_open_destination_folder(self) -> None:
        """開啟目標資料夾"""
        try:
            dst_path = self.var_dst_dir.get().strip()
            if not dst_path:
                messagebox.showwarning('提醒', '請先輸入目標資料夾路徑')
                return
            
            from pathlib import Path
            import os
            
            dst = Path(dst_path)
            
            # 如果資料夾不存在，先建立
            if not dst.exists():
                try:
                    dst.mkdir(parents=True, exist_ok=True)
                    self._append_output(f'已建立資料夾：{dst}')
                except Exception as e:
                    messagebox.showerror('錯誤', f'無法建立資料夾：{e}')
                    return
            
            # 使用系統預設程式開啟資料夾
            if os.name == 'nt':  # Windows
                os.startfile(str(dst))
            elif os.name == 'posix':  # macOS and Linux
                os.system(f'open "{dst}"' if os.uname().sysname == 'Darwin' else f'xdg-open "{dst}"')
            
            self._append_output(f'已開啟資料夾：{dst}')
            
        except Exception as exc:
            messagebox.showerror('錯誤', f'開啟資料夾失敗：{exc}')

    def on_clear_output(self) -> None:
        """清空輸出內容"""
        self.txt_output.delete(1.0, tk.END)

    def _on_closing(self) -> None:
        """視窗關閉時的處理"""
        self._save_settings()
        self.ssh.close()
        self.root.destroy()

    # ---------- 背景任務 ----------
    def _task_test_connection(self) -> None:
        """測試連線任務"""
        self._update_connection_status('connecting')
        self._append_output('正在測試 SSH 連線...')
        
        try:
            self._append_output(f'目標：{self.var_dut_ip.get()}@{self.var_username.get()}')
            
            # 檢查輸入
            if not self.var_dut_ip.get().strip():
                raise Exception("請輸入 DUT IP 位址")
            if not self.var_username.get().strip():
                raise Exception("請輸入使用者名稱")
            
            # 使用 Paramiko 連線
            self._append_output('使用 Paramiko 測試...')
            self.ssh.connect(
                hostname=self.var_dut_ip.get().strip(),
                username=self.var_username.get().strip(),
                password=None,  # DUT 不需要密碼
                timeout=30
            )
            
            # 連線成功
            self._update_connection_status('connected')
            self._append_output('✅ SSH 連線成功！', 'success')
            self._append_output('可以開始執行 DUT 指令')
            
        except Exception as exc:
            self._update_connection_status('disconnected')
            self._append_output(f'❌ 連線測試失敗：{exc}', 'error')
            self._append_output('請檢查：')
            self._append_output('1. DUT IP 位址是否正確')
            self._append_output('2. 使用者名稱是否正確')
            self._append_output('3. DUT 是否支援 SSH 連線')
            
            # 顯示提醒視窗
            self._show_connection_failed_dialog()

    def _show_connection_failed_dialog(self) -> None:
        """顯示連線失敗提醒視窗"""
        import tkinter.messagebox as msgbox
        
        result = msgbox.askyesno(
            "SSH 連線失敗",
            "無法連線到 DUT 裝置。\n\n"
            "請檢查：\n"
            "• DUT IP 位址是否正確\n"
            "• 使用者名稱是否正確\n"
            "• DUT 是否支援 SSH 連線\n\n"
            "是否要手動測試連線？"
        )
        
        if result:
            self._run_bg(self._task_test_connection)

    def _task_exec_command(self, command: str) -> None:
        try:
            self._append_output(f'$ {command}')
            
            # 確保 SSH 連線正常
            try:
                code, out, err = self.ssh.exec_command(command, timeout=30)
            except Exception as e:
                if 'SSH 連線已斷開' in str(e):
                    self._append_output('檢測到 SSH 連線斷開，嘗試重新連線...')
                    self._ensure_ssh()
                    code, out, err = self.ssh.exec_command(command, timeout=30)
                else:
                    raise e
            if out:
                self._append_output(out)
            if err and 'Warning:' not in err:
                self._append_output(err)
            
            if code == 127:
                self._append_output(f'[警告] Exit code: {code} - 指令未找到')
                self._append_output('嘗試使用完整路徑...')
                # 嘗試常見的 diag 指令路徑
                if command.startswith('diag'):
                    alt_commands = [
                        f'/usr/bin/{command}',
                        f'/bin/{command}',
                        f'/sbin/{command}',
                        f'/usr/sbin/{command}'
                    ]
                    for alt_cmd in alt_commands:
                        self._append_output(f'嘗試: {alt_cmd}')
                        code2, out2, err2 = self.ssh.exec_command(alt_cmd, timeout=30)
                        if code2 != 127:
                            if out2:
                                self._append_output(out2)
                            if err2 and 'Warning:' not in err2:
                                self._append_output(err2)
                            self._append_output(f'成功！Exit code: {code2}')
                            break
                        else:
                            self._append_output(f'失敗 (Exit code: {code2})')
                else:
                    self._append_output(f'Exit code: {code}')
            else:
                self._append_output(f'Exit code: {code}')
            
            # 顯示指令完畢標記
            self._append_output('===指令完畢===', 'info')
                
        except Exception as exc:
            self._append_output(f'[錯誤] 執行失敗：{exc}')
            # 即使出錯也顯示指令完畢標記
            self._append_output('===指令完畢===', 'info')

    def _task_copy_from_dut(self, src_glob: str, dst_dir: str) -> None:
        try:
            self._append_output(f'開始傳輸：{src_glob} -> {dst_dir}')
            dst = Path(dst_dir)
            
            # 確保目標目錄存在
            if not dst.exists():
                self._append_output(f'建立目標目錄：{dst}')
                dst.mkdir(parents=True, exist_ok=True)
            
            # 先檢查 DUT 上是否有匹配的檔案
            self._append_output('檢查 DUT 上的檔案...')
            check_cmd = f"ls {src_glob} 2>/dev/null || echo 'NO_FILES_FOUND'"
            exit_code, stdout, stderr = self.ssh.exec_command(check_cmd, timeout=10)
            
            if exit_code == 0 and stdout and 'NO_FILES_FOUND' not in stdout:
                # 過濾掉非檔案路徑的輸出
                files_found = []
                for line in stdout.strip().split('\n'):
                    line = line.strip()
                    if line and not line.startswith('sh:') and not line.startswith('NOKIA') and line.startswith('/'):
                        files_found.append(line)
                
                if files_found:
                    self._append_output(f'找到 {len(files_found)} 個檔案：')
                    for f in files_found:
                        self._append_output(f'  - {f}')
                else:
                    # 沒有找到有效的檔案路徑
                    self._append_output(f'⚠️ DUT 上沒有找到匹配的檔案：{src_glob}')
                    self._append_output('可能的原因：')
                    self._append_output('  - 檔案尚未產生')
                    self._append_output('  - 路徑不正確')
                    self._append_output('  - 檔案已被刪除')
                    self._append_output('建議：')
                    self._append_output('  - 先執行相關指令產生檔案')
                    self._append_output('  - 檢查路徑是否正確')
                    self._append_output('  - 使用 ls 指令確認檔案存在')
                    return
                
                # 使用系統 SCP 命令
                code, out, err = self.ssh.scp_download_system(
                    self.var_dut_ip.get().strip(),
                    self.var_username.get().strip(),
                    src_glob, 
                    str(dst)
                )
                
                if code == 0:
                    self._append_output(f'傳輸成功！')
                    if out:
                        self._append_output(out)
                    
                    # 列出傳輸的檔案
                    try:
                        files = list(dst.glob('*'))
                        if files:
                            self._append_output(f'傳輸的檔案：')
                            for f in files:
                                if f.is_file():
                                    self._append_output(f'  - {f.name}')
                    except Exception:
                        pass
                else:
                    self._append_output(f'傳輸失敗，Exit code: {code}')
                    if err:
                        self._append_output(f'錯誤：{err}')
                    if out:
                        self._append_output(f'輸出：{out}')
            else:
                # 沒有找到匹配的檔案
                self._append_output(f'⚠️ DUT 上沒有找到匹配的檔案：{src_glob}')
                self._append_output('可能的原因：')
                self._append_output('  - 檔案尚未產生')
                self._append_output('  - 路徑不正確')
                self._append_output('  - 檔案已被刪除')
                self._append_output('建議：')
                self._append_output('  - 先執行相關指令產生檔案')
                self._append_output('  - 檢查路徑是否正確')
                self._append_output('  - 使用 ls 指令確認檔案存在')
            
            # 顯示指令完畢標記
            self._append_output('===指令完畢===', 'info')
                    
        except Exception as exc:
            self._append_output(f'[錯誤] 傳輸失敗：{exc}')
            # 即使出錯也顯示指令完畢標記
            self._append_output('===指令完畢===', 'info')

    def _task_check_files_and_show_info(self, path: str) -> None:
        """檢查檔案並顯示資訊"""
        try:
            self._append_output('🔍 檢查檔案中...')
            
            # 檢查 DUT 上的檔案
            check_cmd = f"ls {path} 2>/dev/null || echo 'NO_FILES_FOUND'"
            exit_code, stdout, stderr = self.ssh.exec_command(check_cmd, timeout=10)
            
            if exit_code == 0 and stdout and 'NO_FILES_FOUND' not in stdout:
                # 過濾掉非檔案路徑的輸出
                files_found = []
                for line in stdout.strip().split('\n'):
                    line = line.strip()
                    if line and not line.startswith('sh:') and not line.startswith('NOKIA') and line.startswith('/'):
                        files_found.append(line)
                
                if files_found:
                    file_count = len(files_found)
                    if file_count <= 10:
                        # 檔案少於等於10個，顯示所有檔案
                        self._append_output(f'📁 找到 {file_count} 個檔案：')
                        for f in files_found:
                            # 只顯示檔案名稱，不顯示完整路徑
                            filename = f.split('/')[-1]
                            self._append_output(f'  - {filename}')
                    else:
                        # 檔案超過10個，只顯示數量
                        self._append_output(f'📁 找到 {file_count} 個檔案')
                        self._append_output('💡 檔案數量較多，點擊「開始傳輸」查看詳細清單')
                else:
                    # 沒有找到有效的檔案路徑
                    self._append_output('⚠️ 沒有找到匹配的檔案')
            else:
                # 沒有找到匹配的檔案
                self._append_output('⚠️ 沒有找到匹配的檔案')
            
            self._append_output('💡 點擊「開始傳輸」按鍵開始複製檔案')
            
            # 顯示指令完畢標記
            self._append_output('===指令完畢===', 'info')
                    
        except Exception as exc:
            self._append_output(f'[錯誤] 檢查檔案失敗：{exc}')
            # 即使出錯也顯示指令完畢標記
            self._append_output('===指令完畢===', 'info')

    # ---------- 共用 ----------
    def _ensure_ssh(self) -> None:
        if not self.ssh.is_connected:
            timeout = int(self.var_timeout.get() or '15')
            username = self.var_username.get().strip()
            hostname = self.var_dut_ip.get().strip()
            
            # 輸入驗證
            if not hostname:
                raise Exception("DUT IP 位址不能為空")
            if not username:
                raise Exception("使用者名稱不能為空")
            
            # DUT 不需要密碼，傳入 None
            self.ssh.connect(hostname=hostname, username=username, password=None, timeout=timeout)

    def _run_bg(self, target) -> None:
        th = threading.Thread(target=target, daemon=True)
        th.start()

    def _apply_font_size(self) -> None:
        try:
            self.txt_output.configure(font=('Consolas', self.font_size))
        except Exception:
            pass

    def _append_output(self, text: str, tag: str = None) -> None:
        """添加輸出到右側文字區域，支援彩色標籤"""
        self.txt_output.insert(tk.END, text.rstrip() + '\n')
        
        # 如果指定了標籤，應用顏色
        if tag:
            # 找到剛插入的文字位置
            start_line = self.txt_output.index(tk.END + '-2l')
            end_line = self.txt_output.index(tk.END + '-1l')
            self.txt_output.tag_add(tag, start_line, end_line)
        
        # 自動應用常用字串的顏色
        self._apply_auto_colors(text)
        
        self.txt_output.see(tk.END)
        self.root.update_idletasks()
    
    def _apply_auto_colors(self, text: str) -> None:
        """自動應用常用字串的顏色"""
        import re
        
        # 找到剛插入的文字位置
        start_line = self.txt_output.index(tk.END + '-2l')
        end_line = self.txt_output.index(tk.END + '-1l')
        
        # 成功相關字串
        success_patterns = [
            r'傳輸成功', r'連線成功', r'執行成功', r'找到 \d+ 個檔案',
            r'Exit code: 0', r'✓', r'✅'
        ]
        
        # 錯誤相關字串
        error_patterns = [
            r'錯誤', r'失敗', r'Exit code: [1-9]', r'No such file',
            r'連線失敗', r'傳輸失敗', r'執行失敗', r'❌'
        ]
        
        # 警告相關字串
        warning_patterns = [
            r'Warning', r'警告', r'注意', r'提醒', r'⚠️'
        ]
        
        # 檔案相關字串 - 高亮整行
        file_highlight_patterns = {
            r'\.yuv': "file_yuv",
            r'\.jpg': "file_jpg", 
            r'\.bin': "file_bin",
            r'\.log': "file_log",
            r'\.yml': "file_yml",
            r'\.txt': "file_other"
        }
        
        # 路徑相關字串
        path_patterns = [
            r'/mnt/', r'/tmp/', r'/var/', r'D:\\', r'C:\\'
        ]
        
        # 一般檔案相關字串
        file_patterns = [
            r'\.jpg', r'\.yuv', r'\.bin', r'\.yml', r'\.log', r'\.txt'
        ]
        
        # 優先檢查檔案高亮
        file_highlighted = False
        for pattern, tag in file_highlight_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                self.txt_output.tag_add(tag, start_line, end_line)
                file_highlighted = True
                break
        
        # 如果沒有檔案高亮，才應用其他顏色標籤
        if not file_highlighted:
            for pattern in success_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    self.txt_output.tag_add("success", start_line, end_line)
                    break
            
            for pattern in error_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    self.txt_output.tag_add("error", start_line, end_line)
                    break
                    
            for pattern in warning_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    self.txt_output.tag_add("warning", start_line, end_line)
                    break
                    
            for pattern in file_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    self.txt_output.tag_add("file", start_line, end_line)
                    break
                    
            for pattern in path_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    self.txt_output.tag_add("path", start_line, end_line)
                    break

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = FourCamDebugTool()
    app.run()


if __name__ == '__main__':
    main()


