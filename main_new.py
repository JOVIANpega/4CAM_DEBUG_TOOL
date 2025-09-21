#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4CAM_DEBUG_TOOL - 4攝影機 DUT SSH 控制工具 (重構版)

主要用途：
- 透過 SSH 對 DUT 下指令（從 Command.txt 載入或手動輸入）
- 由 DUT 複製檔案到本機（支援萬用字元，透過 SFTP 實作）

設計重點：
- 模組化設計，拆分為多個專門模組
- 完整的除錯機制與錯誤處理
- Windows 11 風格 GUI
- 支援 PyInstaller 打包

作者：AI 助手
版本：1.2.1
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
import socket
import datetime

# 導入除錯機制
from debug_handler import setup_debug_for_app, safe_execute, safe_execute_with_error
from gui_tools import setup_gui_tools, Tooltip
from settings_manager import SettingsManager

# 本地模組
from ssh_client import SSHClientManager
from command_loader import load_commands_from_file, CommandItem


def get_resource_path(relative_path: str) -> str:
    """取得資源檔案的絕對路徑（支援 PyInstaller 打包後的路徑）"""
    try:
        # PyInstaller 建立的臨時資料夾路徑
        base_path = sys._MEIPASS
    except AttributeError:
        # 一般 Python 執行環境
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


def _safe_makedirs(path: Path) -> None:
    """安全地建立目錄"""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


class FourCamDebugTool:
    """4CAM 除錯工具主類別"""
    
    def __init__(self) -> None:
        # 設定除錯機制
        setup_debug_for_app()
        
        # 初始化設定管理器
        self.settings = SettingsManager()
        
        # 建立主視窗
        self.root = tk.Tk()
        self.root.title(f'4CAM_DEBUG_TOOL {self.settings.get("app_version")}')
        self.root.geometry(self.settings.get('window_geometry', '900x560'))
        self.root.resizable(True, True)
        self.root.minsize(800, 500)
        
        # 設定 GUI 工具
        self.font_manager, self.style_manager, self.keyboard_manager = setup_gui_tools(self.root)
        
        # 字體設定
        self.font_size = self.settings.get('font_size', 12)
        self.left_font_size = self.settings.get('left_font_size', 10)
        self.popup_font_size = self.settings.get('popup_font_size', 12)
        
        # 設定主要字體
        self.primary_font = self.font_manager.primary_font
        self.root.popup_font_size = self.popup_font_size
        
        # 應用程式狀態
        self.current_commands: list[CommandItem] = []
        self.ssh = SSHClientManager()
        self.connection_status = 'disconnected'
        
        # UI 變數
        self._init_ui_variables()
        
        # 建立 UI
        self._build_layout()
        
        # 載入初始設定
        self._load_initial_settings()
        
        # 設定鍵盤快捷鍵
        self._setup_keyboard_shortcuts()
        
        # 設定關閉處理
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    @safe_execute
    def _init_ui_variables(self):
        """初始化 UI 變數"""
        # 連線設定變數
        self.var_dut_ip = tk.StringVar(value=self.settings.get('dut_ip', '192.168.11.143'))
        self.var_username = tk.StringVar(value=self.settings.get('username', 'root'))
        self.var_timeout = tk.IntVar(value=self.settings.get('timeout', 30))
        
        # UI 控制變數
        self.var_clear_output = tk.BooleanVar(value=self.settings.get('clear_output', True))
        self.var_search_text = tk.StringVar()
        self.var_manual_input = tk.StringVar()
        self.var_src_path = tk.StringVar()
        self.var_dest_path = tk.StringVar()
        
        # 檔案傳輸變數
        self.var_src_glob = tk.StringVar(value='/mnt/usr/*.jpg')
        self.var_dst_dir = tk.StringVar(value=str(Path('D:/VALO360/4CAM')))
        self.var_common_path = tk.StringVar(value='選擇常用路徑...')
        
        # 字體大小變數
        self.var_font_size = tk.IntVar(value=self.font_size)
        self.var_left_font_size = tk.IntVar(value=self.left_font_size)
        self.var_popup_font_size = tk.IntVar(value=self.popup_font_size)
    
    @safe_execute
    def _build_layout(self):
        """建立主要 UI 布局"""
        # 建立主要 PanedWindow（與原版一致）
        self._paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self._paned.pack(fill=tk.BOTH, expand=True)
        
        # 設定分隔條樣式（更粗，紅色）
        style = ttk.Style()
        style.configure('TPanedwindow', sashwidth=8, sashrelief=tk.RAISED)
        style.map('TPanedwindow', sashcolor=[('active', '#FF0000'), ('!active', '#FF0000')])
        
        # 配置基本樣式（讓按鍵更明顯）
        self._configure_styles(style)

        # 左右框架（與原版一致）
        left = ttk.Frame(self._paned, padding=10)
        right = ttk.Frame(self._paned, padding=10)
        self._paned.add(left, weight=2)
        self._paned.add(right, weight=3)

        # 建立左右面板
        self._build_left_panel(left)
        self._build_right_panel(right)

        # 若有保存的分隔條位置，套用（延後讓視窗初始化完成）
        def _apply_saved_sash():
            try:
                if hasattr(self, 'settings') and 'sash_pos' in self.settings.settings:
                    pos = self.settings.get('sash_pos', 400)
                    self._paned.sashpos(0, pos)
            except Exception:
                pass
        
        self.root.after(100, _apply_saved_sash)
    
    @safe_execute
    def _configure_styles(self, style):
        """配置 GUI 樣式"""
        # 基本按鍵樣式（更明顯的顏色）
        style.configure('TButton', 
                       background='#e1e1e1', 
                       foreground='#000000',
                       font=(self.primary_font, 10),
                       padding=(10, 8),
                       relief='raised',
                       borderwidth=2)
        
        style.map('TButton',
                 background=[('active', '#d0d0d0'),
                           ('pressed', '#c0c0c0')],
                 relief=[('pressed', 'sunken'),
                        ('active', 'raised')])
        
        # 控制按鈕樣式（彩色）
        style.configure('Green.TButton',
                       background='#90EE90',
                       foreground='#000000',
                       font=(self.primary_font, 10, 'bold'),
                       padding=(12, 10),
                       relief='flat',
                       borderwidth=0)
        
        style.configure('Blue.TButton',
                       background='#87CEEB',
                       foreground='#000000',
                       font=(self.primary_font, 10, 'bold'),
                       padding=(12, 10),
                       relief='flat',
                       borderwidth=0)
        
        style.configure('Orange.TButton',
                       background='#FFB366',
                       foreground='#000000',
                       font=(self.primary_font, 10, 'bold'),
                       padding=(12, 10),
                       relief='flat',
                       borderwidth=0)
        
        style.configure('Purple.TButton',
                       background='#DDA0DD',
                       foreground='#000000',
                       font=(self.primary_font, 10, 'bold'),
                       padding=(12, 10),
                       relief='flat',
                       borderwidth=0)
        
        style.configure('Red.TButton',
                       background='#FFB6C1',
                       foreground='#000000',
                       font=(self.primary_font, 10, 'bold'),
                       padding=(12, 10),
                       relief='flat',
                       borderwidth=0)
        
        # 輸入框樣式
        style.configure('TEntry',
                       background='#ffffff',
                       foreground='#000000',
                       font=(self.primary_font, 10),
                       fieldbackground='#ffffff')
        
        style.configure('Highlight.TEntry',
                       background='#ffffe0',
                       foreground='#000000')
        
        # 標籤頁樣式（棕色主題）
        style.configure('TNotebook.Tab',
                       background='#D2B48C',  # 淺棕色
                       foreground='#000000',
                       font=(self.primary_font, 10),
                       padding=(12, 8))
        
        style.map('TNotebook.Tab',
                 background=[('selected', '#DEB887'),  # 較深的棕色
                           ('active', '#F4E4BC')],    # 更淺的棕色
                 foreground=[('selected', '#000000'),
                           ('active', '#000000')])
        
        # 框架樣式
        style.configure('TFrame',
                       background='#f5f5f5')
        
        style.configure('TLabelframe',
                       background='#f5f5f5')
        
        style.configure('TLabelframe.Label',
                       background='#f5f5f5',
                       foreground='#000000',
                       font=(self.primary_font, 10))
        
        # 核取方塊樣式
        style.configure('TCheckbutton',
                       background='#f5f5f5',
                       foreground='#000000',
                       font=(self.primary_font, 10))
    
    @safe_execute
    def _build_left_panel(self, parent):
        """建立左側控制面板"""
        
        # 標題區域
        self._build_title_section(parent)
        
        # 標籤頁區域
        self._build_notebook_section(parent)
        
        # 控制按鈕區域
        self._build_control_buttons_section(parent)
    
    @safe_execute
    def _build_title_section(self, parent):
        """建立標題區域"""
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill='x', pady=(0, 10))
        
        # 主標題
        title_label = ttk.Label(
            title_frame,
            text='4CAM DEBUG TOOL',
            font=self.font_manager.get_font_tuple(22, 'bold'),
            foreground='#323130'
        )
        title_label.pack(side=tk.LEFT)
        
        # 右側按鈕（字體調整等）
        self._build_title_buttons(title_frame)
    
    @safe_execute
    def _build_title_buttons(self, parent):
        """建立標題區域的按鈕"""
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(side=tk.RIGHT)
        
        # 字體調整按鈕
        ttk.Button(btn_frame, text='+', width=3,
                  command=self.on_font_increase).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='-', width=3,
                  command=self.on_font_decrease).pack(side=tk.LEFT, padx=2)
    
    @safe_execute
    def _build_notebook_section(self, parent):
        """建立標籤頁區域"""
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill='both', expand=True, pady=(0, 10))
        
        # 建立各個標籤頁
        self._build_connection_tab()
        self._build_dut_command_tab()
        self._build_linux_command_tab()
        self._build_manual_command_tab()
        self._build_file_transfer_tab()
        self._build_command_list_tab()
        self._build_settings_tab()
    
    @safe_execute_with_error
    def _build_connection_tab(self):
        """建立連線設定標籤頁"""
        tab_conn = ttk.Frame(self.notebook)
        self.notebook.add(tab_conn, text='連線')
        
        # 連線設定框架
        conn_frame = ttk.LabelFrame(tab_conn, text='SSH 連線設定')
        conn_frame.pack(fill='x', padx=5, pady=5)
        
        # DUT IP
        ttk.Label(conn_frame, text='DUT IP:').grid(row=0, column=0, sticky='w', padx=5, pady=2)
        ttk.Entry(conn_frame, textvariable=self.var_dut_ip, width=20).grid(row=0, column=1, padx=5, pady=2)
        
        # 使用者名稱
        ttk.Label(conn_frame, text='使用者名稱:').grid(row=1, column=0, sticky='w', padx=5, pady=2)
        ttk.Entry(conn_frame, textvariable=self.var_username, width=20).grid(row=1, column=1, padx=5, pady=2)
        
        # 連線狀態指示器
        self.status_indicator = ttk.Label(conn_frame, text='● 未連線', foreground='red')
        self.status_indicator.grid(row=2, column=0, columnspan=2, pady=10)
        
        Tooltip(self.status_indicator, "顯示目前的 SSH 連線狀態")
    
    @safe_execute
    def _build_dut_command_tab(self):
        """建立 DUT 指令標籤頁"""
        tab_cmd = ttk.Frame(self.notebook)
        self.notebook.add(tab_cmd, text='DUT指令')
        
        # 指令選擇框架
        cmd_frame = ttk.LabelFrame(tab_cmd, text='指令控制（COMMANDS/Command.txt）')
        cmd_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 指令下拉選單
        self.cbo_commands = ttk.Combobox(cmd_frame, state='readonly', width=50)
        self.cbo_commands.pack(pady=5)
        self.cbo_commands.bind('<<ComboboxSelected>>', self.on_command_selected)
        
        # 執行按鈕
        ttk.Button(cmd_frame, text='執行指令', 
                  command=self.on_execute_selected_command).pack(pady=5)
        
        # 開啟檔案按鈕
    
    @safe_execute
    def _build_linux_command_tab(self):
        """建立 Linux 指令標籤頁"""
        tab_linux = ttk.Frame(self.notebook)
        self.notebook.add(tab_linux, text='LINUX指令')
        
        # Linux 指令框架
        linux_frame = ttk.LabelFrame(tab_linux, text='Linux 指令控制（COMMANDS/linux.txt）')
        linux_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Linux 指令下拉選單
        self.cbo_linux = ttk.Combobox(linux_frame, state='readonly', width=50)
        self.cbo_linux.pack(pady=5)
        
        # 開啟檔案按鈕
        
        # 執行按鈕
        ttk.Button(linux_frame, text='執行 Linux 指令', 
                  command=self.on_execute_linux_command).pack(pady=5)
    
    @safe_execute
    def _build_manual_command_tab(self):
        """建立手動指令標籤頁"""
        tab_manual = ttk.Frame(self.notebook)
        self.notebook.add(tab_manual, text='手動指令')
        
        # 手動指令框架
        manual_frame = ttk.LabelFrame(tab_manual, text='手動指令輸入')
        manual_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 指令輸入框
        self.ent_manual_input = ttk.Entry(manual_frame, textvariable=self.var_manual_input, width=50)
        self.ent_manual_input.pack(pady=5)
        self.ent_manual_input.bind('<Return>', self.on_execute_manual_command)
        
        # 執行按鈕
        ttk.Button(manual_frame, text='執行手動指令', 
                  command=self.on_execute_manual_command).pack(pady=5)
    
    @safe_execute
    def _build_file_transfer_tab(self):
        """建立檔案傳輸標籤頁（還原原版樣式）"""
        tab_transfer = ttk.Frame(self.notebook)
        self.notebook.add(tab_transfer, text='檔案傳輸')
        
        # 檔案傳輸框架（還原原版樣式）
        lf_copy = ttk.LabelFrame(tab_transfer, text='檔案傳輸（DUT → PC）', padding=8)
        lf_copy.pack(fill='x', pady=(6, 0))
        
        # 常用路徑下拉選單
        ttk.Label(lf_copy, text='常用路徑', font=(self.primary_font, 10)).grid(row=0, column=0, sticky='w')
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
        self.cbo_common = ttk.Combobox(lf_copy, textvariable=self.var_common_path, values=self.common_paths, 
                                 width=45, state='readonly', font=(self.primary_font, 10))
        self.cbo_common.grid(row=0, column=1, sticky='w', padx=(6, 0))
        self.cbo_common.bind('<<ComboboxSelected>>', self.on_common_path_selected)
        
        # 來源路徑
        ttk.Label(lf_copy, text='來源（DUT glob）', font=(self.primary_font, 10)).grid(row=1, column=0, sticky='w')
        self.ent_src = ttk.Entry(lf_copy, textvariable=self.var_src_glob, width=42, font=(self.primary_font, 10))
        self.ent_src.grid(row=1, column=1, sticky='w', padx=(6, 0))
        
        # 目標路徑
        ttk.Label(lf_copy, text='目標（PC 資料夾）', font=(self.primary_font, 10)).grid(row=2, column=0, sticky='w')
        entry_frame = ttk.Frame(lf_copy)
        entry_frame.grid(row=2, column=1, sticky='w', padx=(6, 0))
        self.ent_dst = ttk.Entry(entry_frame, textvariable=self.var_dst_dir, width=42, font=(self.primary_font, 10))
        self.ent_dst.pack(side='left')
        btn_open_dst = ttk.Button(entry_frame, text='開啟目標資料夾', command=self.on_open_destination_folder, width=12)
        btn_open_dst.pack(side='left', padx=(5, 0))
        
        # 執行按鈕
        btn_frame = ttk.Frame(lf_copy)
        btn_frame.grid(row=3, column=0, columnspan=2, sticky='e', pady=(6, 0))
        btn_copy = ttk.Button(btn_frame, text='開始傳輸', command=self.on_start_copy)
        btn_copy.pack(side='right')
    
    @safe_execute
    def _build_command_list_tab(self):
        """建立指令表標籤頁"""
        tab_files = ttk.Frame(self.notebook)
        self.notebook.add(tab_files, text='指令表')
        
        # 指令檔案管理框架
        files_frame = ttk.LabelFrame(tab_files, text='指令檔案管理')
        files_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 三個開啟按鈕
        ttk.Button(files_frame, text='開啟 Command.txt', 
                  command=self.on_open_command_file).pack(pady=5)
        ttk.Button(files_frame, text='開啟 linux.txt', 
                  command=self.on_open_linux_file).pack(pady=5)
        ttk.Button(files_frame, text='開啟 download.txt', 
                  command=self.on_open_download_file).pack(pady=5)
    
    @safe_execute
    def _build_settings_tab(self):
        """建立設定標籤頁"""
        tab_settings = ttk.Frame(self.notebook)
        self.notebook.add(tab_settings, text='設定')
        
        # 字體設定框架
        font_frame = ttk.LabelFrame(tab_settings, text='字體大小設定')
        font_frame.pack(fill='x', padx=5, pady=5)
        
        # 右側字體控制
        right_font_frame = ttk.Frame(font_frame)
        right_font_frame.grid(row=0, column=0, columnspan=3, sticky='ew', padx=5, pady=2)
        
        ttk.Label(right_font_frame, text='右側字體大小:').pack(side='left')
        ttk.Button(right_font_frame, text='-', width=3, 
                  command=lambda: self._adjust_font_size('right', -1)).pack(side='left', padx=(10, 2))
        ttk.Label(right_font_frame, textvariable=self.var_font_size, width=3).pack(side='left', padx=2)
        ttk.Button(right_font_frame, text='+', width=3, 
                  command=lambda: self._adjust_font_size('right', 1)).pack(side='left', padx=2)
        
        # 左側字體控制
        left_font_frame = ttk.Frame(font_frame)
        left_font_frame.grid(row=1, column=0, columnspan=3, sticky='ew', padx=5, pady=2)
        
        ttk.Label(left_font_frame, text='左側字體大小:').pack(side='left')
        ttk.Button(left_font_frame, text='-', width=3, 
                  command=lambda: self._adjust_font_size('left', -1)).pack(side='left', padx=(10, 2))
        ttk.Label(left_font_frame, textvariable=self.var_left_font_size, width=3).pack(side='left', padx=2)
        ttk.Button(left_font_frame, text='+', width=3, 
                  command=lambda: self._adjust_font_size('left', 1)).pack(side='left', padx=2)
        
        # 彈出視窗字體控制
        popup_font_frame = ttk.Frame(font_frame)
        popup_font_frame.grid(row=2, column=0, columnspan=3, sticky='ew', padx=5, pady=2)
        
        ttk.Label(popup_font_frame, text='彈出視窗字體大小:').pack(side='left')
        ttk.Button(popup_font_frame, text='-', width=3, 
                  command=lambda: self._adjust_font_size('popup', -1)).pack(side='left', padx=(10, 2))
        ttk.Label(popup_font_frame, textvariable=self.var_popup_font_size, width=3).pack(side='left', padx=2)
        ttk.Button(popup_font_frame, text='+', width=3, 
                  command=lambda: self._adjust_font_size('popup', 1)).pack(side='left', padx=2)
        
        font_frame.columnconfigure(1, weight=1)
    
    @safe_execute
    def _adjust_font_size(self, font_type: str, delta: int):
        """調整字體大小"""
        if font_type == 'right':
            current = self.var_font_size.get()
            new_size = max(8, min(24, current + delta))
            self.var_font_size.set(new_size)
            self.on_font_size_change(new_size)
        elif font_type == 'left':
            current = self.var_left_font_size.get()
            new_size = max(8, min(24, current + delta))
            self.var_left_font_size.set(new_size)
            self.on_left_font_size_change(new_size)
        elif font_type == 'popup':
            current = self.var_popup_font_size.get()
            new_size = max(8, min(24, current + delta))
            self.var_popup_font_size.set(new_size)
            self.on_popup_font_size_change(new_size)
    
    @safe_execute
    def _build_control_buttons_section(self, parent):
        """建立控制按鈕區域"""
        # 控制按鈕框架
        control_frame = ttk.LabelFrame(parent, text='控制按鈕')
        control_frame.pack(fill='x', pady=(0, 5))
        
        # 上排按鈕（3個）
        top_frame = ttk.Frame(control_frame)
        top_frame.pack(pady=2)
        
        ttk.Button(top_frame, text='說明', style='Green.TButton',
                  command=self.on_help).pack(side='left', padx=(0, 2))
        ttk.Button(top_frame, text='測試SSH', style='Blue.TButton',
                  command=self.on_test_connection).pack(side='left', padx=(0, 2))
        ttk.Button(top_frame, text='重載指令表', style='Orange.TButton',
                  command=self.on_reload_commands).pack(side='left')
        
        # 下排按鈕（2個）
        bottom_frame = ttk.Frame(control_frame)
        bottom_frame.pack(pady=2)
        
        ttk.Button(bottom_frame, text='存LOG', style='Purple.TButton',
                  command=self.on_save_log).pack(side='left', padx=(0, 2))
        ttk.Button(bottom_frame, text='清空右視窗', style='Red.TButton',
                  command=self.on_clear_output).pack(side='left')
        
        # Timeout 和 清除訊息設定
        settings_frame = ttk.Frame(control_frame)
        settings_frame.pack(fill='x', pady=5)
        settings_frame.configure(style='TFrame')
        
        # 設定淡黃色背景
        timeout_frame = ttk.Frame(settings_frame)
        timeout_frame.pack(side='left', fill='x', expand=True)
        
        ttk.Checkbutton(timeout_frame, text='每次下指令清除舊訊息', 
                       variable=self.var_clear_output).pack(side='left')
        
        ttk.Label(timeout_frame, text='Timeout(sec):').pack(side='left', padx=(10, 0))
        ttk.Entry(timeout_frame, textvariable=self.var_timeout, width=8, 
                 style='Highlight.TEntry').pack(side='left', padx=(5, 0))
    
    @safe_execute
    def _build_right_panel(self, parent):
        """建立右側輸出面板"""
        
        # 標題與搜尋區域
        self._build_right_header(parent)
        
        # 主要輸出區域
        self._build_right_output(parent)
    
    @safe_execute
    def _build_right_header(self, parent):
        """建立右側標題區域"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill='x', pady=(0, 5))
        
        # 標題
        self.title_label = ttk.Label(header_frame, text='輸出結果', 
                                   font=self.font_manager.get_font_tuple(14, 'bold'))
        self.title_label.pack(side='left')
        
        Tooltip(self.title_label, "顯示指令執行結果和系統訊息的區域")
        
        # 搜尋框
        search_frame = ttk.Frame(header_frame)
        search_frame.pack(side='right')
        
        ttk.Entry(search_frame, textvariable=self.var_search_text, width=20).pack(side='left')
        ttk.Button(search_frame, text='搜尋', command=self.on_search_next).pack(side='left', padx=(2, 0))
        ttk.Button(search_frame, text='清除', command=self.on_search_clear).pack(side='left', padx=(2, 0))
    
    @safe_execute
    def _build_right_output(self, parent):
        """建立右側輸出區域"""
        # 輸出文字區域
        self.txt_output = ScrolledText(parent, wrap='word', state='disabled',
                                     font=self.font_manager.get_font_tuple(self.font_size))
        self.txt_output.pack(fill='both', expand=True)
        
        # 設定文字標籤樣式
        self.txt_output.tag_config('info', foreground='black')
        self.txt_output.tag_config('success', foreground='green')
        self.txt_output.tag_config('error', foreground='red')
        self.txt_output.tag_config('warning', foreground='orange')
        
        Tooltip(self.txt_output, "指令執行結果顯示區域。支援搜尋功能，可使用右上角的搜尋框快速定位內容。")
    
    @safe_execute
    def _load_initial_settings(self):
        """載入初始設定"""
        # 載入指令檔案
        self._load_commands_initial()
        
        # 載入 Linux 指令
        self._load_linux_commands()
        
        # 顯示歡迎訊息
        self._append_output("=== 4CAM DEBUG TOOL 已啟動 ===", 'info')
        self._append_output(f"版本: {self.settings.get('app_version')}", 'info')
        self._append_output(f"字體: {self.font_manager.primary_font}", 'info')
    
    @safe_execute
    def _setup_keyboard_shortcuts(self):
        """設定鍵盤快捷鍵"""
        shortcuts = {
            '<F1>': self.on_help,
            '<F5>': self.on_reload_commands,
            '<Control-l>': self.on_clear_output,
            '<Control-s>': self.on_save_log,
            '<Control-t>': self.on_test_connection,
            '<Return>': lambda: self.ent_manual_input.focus_set(),
            '<Escape>': lambda: self.root.focus_set(),
        }
        
        self.keyboard_manager.bind_shortcuts(shortcuts)
    
    # === 事件處理方法 ===
    
    @safe_execute_with_error
    def on_command_selected(self, _evt) -> None:
        """指令選擇事件"""
        idx = self.cbo_commands.current()
        if 0 <= idx < len(self.current_commands):
            pass  # 指令已在下拉選單中顯示
    
    @safe_execute_with_error
    def on_test_connection(self) -> None:
        """測試連線"""
        self._auto_fill_pc_ip()
        self._run_bg(self._task_test_connection)
    
    @safe_execute_with_error
    def on_execute_selected_command(self) -> None:
        """執行選中的指令"""
        if self.var_clear_output.get():
            self.txt_output.delete(1.0, tk.END)
        
        idx = self.cbo_commands.current()
        if idx >= 0 and idx < len(self.current_commands):
            cmd_item = self.current_commands[idx]
            self._run_bg(self._task_execute_command, cmd_item.command)
        else:
            self._append_output("請先選擇一個指令", 'warning')
    
    @safe_execute_with_error
    def on_execute_manual_command(self, _event=None) -> None:
        """執行手動輸入的指令"""
        if self.var_clear_output.get():
            self.txt_output.delete(1.0, tk.END)
        
        command = self.var_manual_input.get().strip()
        if command:
            self._run_bg(self._task_execute_command, command)
        else:
            self._append_output("請輸入指令", 'warning')
    
    @safe_execute_with_error
    def on_execute_linux_command(self) -> None:
        """執行 Linux 指令"""
        if self.var_clear_output.get():
            self.txt_output.delete(1.0, tk.END)
        
        selected = self.cbo_linux.get()
        if selected and '=' in selected:
            command = selected.split('=', 1)[1].strip()
            self._run_bg(self._task_execute_command, command)
        else:
            self._append_output("請選擇 Linux 指令", 'warning')
    
    @safe_execute
    def on_common_path_selected(self, event=None) -> None:
        """處理常用路徑選擇"""
        selected = self.var_common_path.get()
        if selected and selected != '選擇常用路徑...':
            # 提取路徑部分（去掉說明文字）
            path = selected.split(' - ')[0]
            self.var_src_glob.set(path)
    
    @safe_execute
    def on_open_destination_folder(self) -> None:
        """開啟目標資料夾"""
        import subprocess
        import platform
        
        dest_path = Path(self.var_dst_dir.get().strip())
        if not dest_path.exists():
            dest_path.mkdir(parents=True, exist_ok=True)
        
        try:
            if platform.system() == 'Windows':
                os.startfile(str(dest_path))
            elif platform.system() == 'Darwin':
                subprocess.run(['open', str(dest_path)])
            else:
                subprocess.run(['xdg-open', str(dest_path)])
        except Exception as e:
            self._append_output(f"無法開啟資料夾: {e}", 'error')
    
    @safe_execute
    def on_start_copy(self) -> None:
        """開始檔案傳輸"""
        src = self.var_src_glob.get().strip()
        dst = self.var_dst_dir.get().strip()
        
        if not src or not dst:
            self._append_output("請填寫來源和目標路徑", 'warning')
            return
        
        self._run_bg(self._task_copy_from_dut, src, dst)
    
    @safe_execute
    def _task_copy_from_dut(self, src_glob: str, dst_dir: str) -> None:
        """檔案傳輸任務"""
        try:
            self._append_output(f"開始傳輸檔案: {src_glob} -> {dst_dir}", 'info')
            
            if self.connection_status != 'connected':
                self._append_output("請先建立 SSH 連線", 'warning')
                return
            
            # 執行檔案傳輸
            success = self.ssh.download_files(src_glob, dst_dir)
            
            if success:
                self._append_output("✅ 檔案傳輸完成", 'success')
            else:
                self._append_output("❌ 檔案傳輸失敗", 'error')
                
        except Exception as e:
            self._append_output(f"檔案傳輸錯誤: {e}", 'error')
    
    @safe_execute_with_error
    def on_start_transfer(self) -> None:
        """開始檔案傳輸"""
        src = self.var_src_path.get().strip()
        dest = self.var_dest_path.get().strip()
        
        if not src or not dest:
            self._append_output("請填寫來源和目標路徑", 'warning')
            return
        
        self._run_bg(self._task_file_transfer, src, dest)
    
    @safe_execute
    def on_browse_dest(self) -> None:
        """瀏覽目標資料夾"""
        folder = filedialog.askdirectory(title="選擇目標資料夾")
        if folder:
            self.var_dest_path.set(folder)
    
    @safe_execute
    def on_open_dest_folder(self) -> None:
        """開啟目標資料夾"""
        import subprocess
        import platform
        
        dest_path = Path(self.var_dest_path.get().strip())
        if not dest_path.exists():
            dest_path.mkdir(parents=True, exist_ok=True)
        
        try:
            if platform.system() == 'Windows':
                os.startfile(str(dest_path))
            elif platform.system() == 'Darwin':
                subprocess.run(['open', str(dest_path)])
            else:
                subprocess.run(['xdg-open', str(dest_path)])
        except Exception as e:
            self._append_output(f"無法開啟資料夾: {e}", 'error')
    
    @safe_execute
    def on_open_command_file(self) -> None:
        """開啟指令檔案"""
        self._open_text_file('COMMANDS/Command.txt')
    
    @safe_execute
    def on_open_linux_file(self) -> None:
        """開啟 Linux 指令檔案"""
        self._open_text_file('COMMANDS/linux.txt')
    
    @safe_execute
    def on_open_download_file(self) -> None:
        """開啟下載指令檔案"""
        self._open_text_file('COMMANDS/download.txt')
    
    @safe_execute
    def _open_text_file(self, relative_path: str) -> None:
        """開啟文字檔案"""
        import subprocess
        import platform
        
        try:
            file_path = Path(get_resource_path(relative_path))
            if platform.system() == 'Windows':
                os.startfile(str(file_path))
            elif platform.system() == 'Darwin':
                subprocess.run(['open', str(file_path)])
            else:
                subprocess.run(['xdg-open', str(file_path)])
            self._append_output(f'已開啟檔案：{file_path}', 'info')
        except Exception as e:
            self._append_output(f'無法開啟檔案：{e}', 'error')
    
    @safe_execute_with_error
    def on_reload_commands(self, *_args) -> None:
        """重新載入所有指令檔案"""
        reload_success = []
        reload_failed = []
        
        try:
            cmd_path = Path(get_resource_path('COMMANDS/Command.txt'))
            self._load_commands_from(cmd_path)
            reload_success.append('Command.txt')
        except Exception as e:
            reload_failed.append(f'Command.txt: {e}')
            
        try:
            linux_path = Path(get_resource_path('COMMANDS/linux.txt'))
            self._load_linux_commands_from_file(linux_path)
            reload_success.append('linux.txt')
        except Exception as e:
            reload_failed.append(f'linux.txt: {e}')
            
        try:
            download_path = Path(get_resource_path('COMMANDS/download.txt'))
            if download_path.exists():
                with open(download_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.strip():
                        reload_success.append('download.txt')
                    else:
                        reload_failed.append('download.txt: 檔案為空')
            else:
                reload_failed.append('download.txt: 檔案不存在')
        except Exception as e:
            reload_failed.append(f'download.txt: {e}')
        
        # 顯示重載結果
        if reload_success:
            self._append_output(f'✅ 成功重新載入：{", ".join(reload_success)}', 'success')
        if reload_failed:
            for failed in reload_failed:
                self._append_output(f'❌ 重新載入失敗：{failed}', 'error')
    
    @safe_execute
    def on_help(self) -> None:
        """顯示說明"""
        self._generate_help_html()
        help_file = Path('4CAM_DEBUG_TOOL_使用說明.html')
        if help_file.exists():
            import webbrowser
            webbrowser.open(str(help_file.absolute()))
        else:
            messagebox.showinfo("說明", "說明檔案生成中，請稍後重試。")
    
    @safe_execute
    def on_clear_output(self) -> None:
        """清空輸出"""
        self.txt_output.config(state='normal')
        self.txt_output.delete(1.0, tk.END)
        self.txt_output.config(state='disabled')
    
    @safe_execute
    def on_save_log(self) -> None:
        """儲存日誌"""
        try:
            log_dir = Path("LOG")
            log_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"output_log_{timestamp}.txt"
            
            content = self.txt_output.get(1.0, tk.END)
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self._append_output(f'日誌已儲存至：{log_file}', 'success')
        except Exception as e:
            self._append_output(f'儲存日誌失敗：{e}', 'error')
    
    @safe_execute
    def on_search_next(self) -> None:
        """搜尋下一個"""
        search_text = self.var_search_text.get()
        if not search_text:
            return
        
        # 實作搜尋功能
        start_pos = self.txt_output.search(search_text, tk.INSERT, tk.END)
        if start_pos:
            end_pos = f"{start_pos}+{len(search_text)}c"
            self.txt_output.tag_remove(tk.SEL, 1.0, tk.END)
            self.txt_output.tag_add(tk.SEL, start_pos, end_pos)
            self.txt_output.mark_set(tk.INSERT, end_pos)
            self.txt_output.see(start_pos)
    
    @safe_execute
    def on_search_clear(self) -> None:
        """清除搜尋"""
        self.var_search_text.set('')
        self.txt_output.tag_remove(tk.SEL, 1.0, tk.END)
    
    @safe_execute
    def on_font_increase(self) -> None:
        """增加字體大小"""
        self.var_font_size.set(min(24, self.var_font_size.get() + 1))
        self.on_font_size_change()
    
    @safe_execute
    def on_font_decrease(self) -> None:
        """減少字體大小"""
        self.var_font_size.set(max(8, self.var_font_size.get() - 1))
        self.on_font_size_change()
    
    @safe_execute
    def on_font_size_change(self, *args) -> None:
        """字體大小變更"""
        new_size = self.var_font_size.get()
        self.font_size = new_size
        self.txt_output.config(font=self.font_manager.get_font_tuple(new_size))
        self.settings.set('font_size', new_size)
    
    @safe_execute
    def on_left_font_size_change(self, *args) -> None:
        """左側字體大小變更"""
        new_size = self.var_left_font_size.get()
        self.left_font_size = new_size
        self.style_manager.update_font_sizes(button_size=new_size, entry_size=new_size)
        self.settings.set('left_font_size', new_size)
    
    @safe_execute
    def on_popup_font_size_change(self, *args) -> None:
        """彈出視窗字體大小變更"""
        new_size = self.var_popup_font_size.get()
        self.popup_font_size = new_size
        self.root.popup_font_size = new_size
        self.settings.set('popup_font_size', new_size)
    
    def on_close(self) -> None:
        """關閉應用程式"""
        try:
            # 儲存設定
            self.settings.set('window_geometry', self.root.geometry(), save=False)
            self.settings.set('dut_ip', self.var_dut_ip.get(), save=False)
            self.settings.set('username', self.var_username.get(), save=False)
            self.settings.set('timeout', self.var_timeout.get(), save=False)
            self.settings.set('clear_output', self.var_clear_output.get(), save=False)
            
            # 儲存分隔條位置
            try:
                sash_pos = self._paned.sashpos(0)
                self.settings.set('sash_pos', sash_pos, save=False)
            except:
                pass
                
            self.settings.save_settings()
            
            # 關閉 SSH 連線
            if self.ssh:
                self.ssh.disconnect()
        except Exception as e:
            print(f"關閉時發生錯誤: {e}")
        finally:
            # 強制關閉視窗
            try:
                self.root.quit()
                self.root.destroy()
            except:
                pass
            # 確保程式退出
            import sys
            sys.exit(0)
    
    # === 工具方法 ===
    
    def _append_output(self, text: str, tag: str = 'info') -> None:
        """添加輸出文字"""
        try:
            self.txt_output.config(state='normal')
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.txt_output.insert(tk.END, f"[{timestamp}] {text}\n", tag)
            self.txt_output.config(state='disabled')
            self.txt_output.see(tk.END)
        except Exception as e:
            print(f"輸出錯誤: {e}")
    
    def _run_bg(self, func, *args) -> None:
        """在背景執行緒中執行函數"""
        thread = threading.Thread(target=func, args=args, daemon=True)
        thread.start()
    
    def _auto_fill_pc_ip(self) -> None:
        """自動填入 PC IP"""
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            # 可以在這裡實作更複雜的 IP 檢測邏輯
        except:
            pass
    
    @safe_execute
    def _load_commands_initial(self) -> None:
        """初始載入指令"""
        try:
            cmd_path = Path(get_resource_path('COMMANDS/Command.txt'))
            self._load_commands_from(cmd_path)
        except Exception as e:
            self._append_output(f'載入指令失敗: {e}', 'error')
    
    @safe_execute
    def _load_commands_from(self, file_path: Path) -> None:
        """從檔案載入指令"""
        try:
            self.current_commands = load_commands_from_file(file_path)
            
            # 更新下拉選單
            command_texts = [f"{cmd.name} | {cmd.command}" for cmd in self.current_commands]
            self.cbo_commands['values'] = command_texts
            
            if command_texts:
                self.cbo_commands.current(0)
            
            self._append_output(f'載入 {len(self.current_commands)} 個指令從 {file_path.name}', 'success')
        except Exception as e:
            self._append_output(f'載入指令失敗: {e}', 'error')
    
    @safe_execute
    def _load_linux_commands(self) -> None:
        """載入 Linux 指令"""
        try:
            linux_path = Path(get_resource_path('COMMANDS/linux.txt'))
            self._load_linux_commands_from_file(linux_path)
        except Exception as e:
            self._append_output(f'載入 Linux 指令失敗: {e}', 'error')
    
    @safe_execute
    def _load_linux_commands_from_file(self, file_path: Path) -> None:
        """從檔案載入 Linux 指令"""
        try:
            if not file_path.exists():
                self._append_output(f'Linux 指令檔案不存在: {file_path}', 'warning')
                return
            
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 解析指令（格式：NAME = COMMAND）
            commands = []
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    try:
                        name, command = line.split('=', 1)
                        commands.append(f"{i:02d}. {name.strip()} = {command.strip()}")
                    except ValueError:
                        continue
            
            # 更新下拉選單
            self.cbo_linux['values'] = commands
            if commands:
                self.cbo_linux.current(0)
            
            self._append_output(f'載入 {len(commands)} 個 Linux 指令', 'success')
            
        except Exception as e:
            self._append_output(f'載入 Linux 指令失敗: {e}', 'error')
    
    # === 背景任務方法 ===
    
    def _task_test_connection(self) -> None:
        """測試連線任務"""
        try:
            self._append_output("正在測試 SSH 連線...", 'info')
            
            dut_ip = self.var_dut_ip.get()
            username = self.var_username.get()
            timeout = self.var_timeout.get()
            
            # 嘗試連線
            if self.ssh.connect(dut_ip, username, timeout=timeout):
                self._append_output(f"✅ SSH 連線成功 ({dut_ip})", 'success')
                self.connection_status = 'connected'
                self.root.after(0, lambda: self.status_indicator.config(
                    text='● 已連線', foreground='green'))
            else:
                self._append_output(f"❌ SSH 連線失敗 ({dut_ip})", 'error')
                self.connection_status = 'disconnected'
                self.root.after(0, lambda: self.status_indicator.config(
                    text='● 連線失敗', foreground='red'))
                
        except Exception as e:
            self._append_output(f"連線測試錯誤: {e}", 'error')
            self.connection_status = 'disconnected'
            self.root.after(0, lambda: self.status_indicator.config(
                text='● 連線錯誤', foreground='red'))
    
    def _task_execute_command(self, command: str) -> None:
        """執行指令任務"""
        try:
            self._append_output(f"執行指令: {command}", 'info')
            
            if self.connection_status != 'connected':
                self._append_output("請先建立 SSH 連線", 'warning')
                return
            
            # 執行指令
            result = self.ssh.execute_command(command, timeout=self.var_timeout.get())
            
            if result.success:
                self._append_output("指令執行成功:", 'success')
                if result.stdout:
                    self._append_output(result.stdout, 'info')
                if result.stderr:
                    self._append_output(f"警告: {result.stderr}", 'warning')
            else:
                self._append_output(f"指令執行失敗: {result.error}", 'error')
                
        except Exception as e:
            self._append_output(f"執行指令錯誤: {e}", 'error')
    
    def _task_file_transfer(self, src_path: str, dest_path: str) -> None:
        """檔案傳輸任務"""
        try:
            self._append_output(f"開始傳輸檔案: {src_path} -> {dest_path}", 'info')
            
            if self.connection_status != 'connected':
                self._append_output("請先建立 SSH 連線", 'warning')
                return
            
            # 執行檔案傳輸
            success = self.ssh.download_files(src_path, dest_path)
            
            if success:
                self._append_output("✅ 檔案傳輸完成", 'success')
            else:
                self._append_output("❌ 檔案傳輸失敗", 'error')
                
        except Exception as e:
            self._append_output(f"檔案傳輸錯誤: {e}", 'error')
    
    def _generate_help_html(self) -> None:
        """生成說明 HTML 檔案"""
        # 這裡可以實作 HTML 說明檔案生成
        pass
    
    def run(self) -> None:
        """啟動應用程式"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\n程式被使用者中斷")
        except Exception as e:
            print(f"程式執行錯誤: {e}")
        finally:
            self.on_close()


def main() -> None:
    """主函數"""
    try:
        app = FourCamDebugTool()
        app.run()
    except Exception as e:
        print(f"應用程式啟動失敗: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
