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
import tkinter.font as tkFont
import logging
import json
from pathlib import Path
import socket
import datetime

# 本地模組
from ssh_client import SSHClientManager
from command_loader import load_commands_from_file, CommandItem
from yuv_viewer import create_yuv_viewer


class Tooltip:
    """創建 tooltip 的工具類別（支援自訂放大字體與最短字元長度）。"""
    def __init__(self, widget, text='widget info', *, font_size: int = None, min_length: int = 1):
        self.widget = widget
        self.text = text
        self.font_size = font_size  # 將在顯示時動態取得
        self.min_length = min_length
        self.tooltip_window = None
        self.tooltip_label = None
        self.auto_hide_timer = None  # 自動隱藏計時器
        self.widget.bind('<Enter>', self.on_enter)
        self.widget.bind('<Leave>', self.on_leave)
        self.widget.bind('<Motion>', self.on_motion)
        
    def on_enter(self, event=None):
        """當滑鼠進入時顯示 tooltip（自動取用當前 widget 顯示文字）。"""
        # 取消自動隱藏計時器
        if self.auto_hide_timer:
            self.widget.after_cancel(self.auto_hide_timer)
            self.auto_hide_timer = None
            
        self._refresh_text_from_widget()
        if len(self.text) >= self.min_length:
            self.show_tooltip()
            
        # 為 Combobox 添加特殊處理
        if isinstance(self.widget, ttk.Combobox):
            self.widget.bind('<Button-1>', self._on_combobox_click)
            self.widget.bind('<KeyPress>', self._on_combobox_key)
            
    def on_leave(self, event=None):
        """當滑鼠離開時隱藏 tooltip"""
        self.hide_tooltip()
        
    def show_tooltip(self):
        """顯示 tooltip（靠近元件右下）。"""
        if self.tooltip_window or not self.text:
            return
        # 初始位置（使用元件右下）
        try:
            x, y, _, _ = self.widget.bbox("insert")
        except Exception:
            x, y = 0, self.widget.winfo_height()
        x += self.widget.winfo_rootx() + 12
        y += self.widget.winfo_rooty() + 12
        
        # 動態取得字體大小
        font_size = self.font_size
        if font_size is None:
            # 嘗試從主視窗取得 popup_font_size
            try:
                main_window = self.widget.winfo_toplevel()
                if hasattr(main_window, 'popup_font_size'):
                    font_size = main_window.popup_font_size
                else:
                    font_size = 12  # 預設值
            except Exception:
                font_size = 12
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        try:
            tw.attributes('-topmost', True)
        except Exception:
            pass
        
        self.tooltip_label = label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Microsoft JhengHei", font_size, 'bold'),
            wraplength=500,
        )
        label.pack(ipadx=6, ipady=4)
        
        # 設定 3 秒後自動隱藏
        self.auto_hide_timer = self.widget.after(3000, self.hide_tooltip)
        
    def hide_tooltip(self):
        """隱藏 tooltip"""
        # 取消自動隱藏計時器
        if self.auto_hide_timer:
            self.widget.after_cancel(self.auto_hide_timer)
            self.auto_hide_timer = None
            
        tw = self.tooltip_window
        self.tooltip_window = None
        self.tooltip_label = None
        if tw:
            tw.destroy()
            
    def _on_combobox_click(self, event=None):
        """Combobox 點擊時的特殊處理"""
        # 延遲檢查是否展開
        self.widget.after(100, self._check_combobox_state)
        
    def _on_combobox_key(self, event=None):
        """Combobox 按鍵時的特殊處理"""
        if event.keysym in ['Up', 'Down', 'Return']:
            # 延遲檢查是否展開
            self.widget.after(100, self._check_combobox_state)
            
    def _check_combobox_state(self):
        """檢查 Combobox 是否展開並顯示 Tooltip"""
        try:
            if isinstance(self.widget, ttk.Combobox):
                # 檢查是否有下拉選項顯示
                current_value = self.widget.get()
                if current_value and len(current_value) >= self.min_length:
                    self._refresh_text_from_widget()
                    if not self.tooltip_window:
                        self.show_tooltip()
        except Exception:
            pass

    def on_motion(self, event=None):
        """滑鼠移動時更新內容與位置。"""
        if not self.tooltip_window:
            return
        self._refresh_text_from_widget()
        if self.tooltip_label is not None:
            self.tooltip_label.configure(text=self.text)
        try:
            x = event.x_root + 12
            y = event.y_root + 12
            self.tooltip_window.wm_geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _refresh_text_from_widget(self) -> None:
        try:
            if isinstance(self.widget, ttk.Combobox):
                # 對於 Combobox，顯示選中的指令內容
                value = self.widget.get()
                if value and value.strip():
                    # 根據 Combobox 的類型顯示不同的提示
                    if 'cbo_commands' in str(self.widget):
                        self.text = f"指令內容: {value}"
                    elif 'cbo_linux' in str(self.widget):
                        # 根據指令類型顯示不同的提示
                        try:
                            # 嘗試取得主視窗的指令類型
                            main_window = self.widget.winfo_toplevel()
                            if hasattr(main_window, 'var_linux_type'):
                                linux_type = main_window.var_linux_type.get()
                                type_map = {
                                    'linux': '基礎 Linux 指令',
                                    'command_simple': '4CAM 專用指令',
                                    'download': '檔案下載指令'
                                }
                                type_name = type_map.get(linux_type, '指令')
                                self.text = f"{type_name}: {value}"
                            else:
                                self.text = f"Linux 指令: {value}"
                        except:
                            self.text = f"Linux 指令: {value}"
                    elif 'cbo_common' in str(self.widget):
                        self.text = f"路徑: {value}"
                    else:
                        self.text = f"內容: {value}"
                else:
                    # 如果沒有選中，顯示預設提示
                    self.text = "選擇要執行的指令"
            else:
                # 其他元件使用動態內容
                value = self.widget.get()
                if value:
                    self.text = value
        except Exception:
            pass


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


def _safe_makedirs(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


# ------------------------------
# GUI 主視窗
# ------------------------------
class FourCamDebugTool:
    def __init__(self) -> None:
        self.root = tk.Tk()
        # 應用程式版本（可由設定檔覆蓋）
        self.var_app_version = tk.StringVar(value='v1.2.0')
        self.root.title(f'4CAM_DEBUG_TOOL {self.var_app_version.get()}')
        self.root.geometry('900x560')
        self.root.resizable(True, True)
        self.root.minsize(800, 500)
        
        # 讓主視窗可以被 Tooltip 存取字體設定
        self.root.popup_font_size = 12  # 初始值

        # 狀態
        self.font_size = 12  # 右視窗字體大小
        self.left_font_size = 10  # 左視窗字體大小
        self.popup_font_size = 12  # 彈出視窗字體大小
        self.current_commands: list[CommandItem] = []
        self.ssh = SSHClientManager()
        self.settings_file = Path('settings.json')
        self.connection_status = 'disconnected'  # disconnected, connecting, connected
        # 儲存元件原始樣式（提供 hover 後恢復）
        try:
            import weakref
            self._orig_styles = weakref.WeakKeyDictionary()
        except Exception:
            self._orig_styles = {}

        # Windows 11 風格主題設定
        try:
            style = ttk.Style(self.root)
            style.theme_use('clam')
            
            # 字體檢測函數 - 更詳細的檢測
            def get_available_font():
                font_candidates = [
                    "Microsoft JhengHei Light",
                    "Microsoft JhengHei UI Light", 
                    "Microsoft JhengHei",
                    "Microsoft YaHei Light",
                    "Microsoft YaHei",
                    "Segoe UI",
                    "TkDefaultFont"
                ]
                
                print("開始檢測可用字體...")
                for font_name in font_candidates:
                    try:
                        test_font = tkFont.Font(family=font_name, size=10)
                        actual_font = test_font.actual()
                        print(f"測試字體: {font_name} -> 實際載入: {actual_font['family']}")
                        
                        # 檢查是否真的載入了指定的字體
                        if actual_font['family'].lower() == font_name.lower() or 'jhenghei' in actual_font['family'].lower():
                            print(f"✅ 使用字體: {font_name}")
                            return font_name
                    except Exception as e:
                        print(f"❌ 字體 {font_name} 載入失敗: {e}")
                        continue
                
                print("⚠️ 使用字體: TkDefaultFont (系統預設)")
                return "TkDefaultFont"
            
            # 設定主要字體
            self.primary_font = get_available_font()
            # 使用命名字體物件，統一控制左側字體大小
            try:
                if 'LeftFont' in tkFont.names():
                    self.left_font = tkFont.nametofont('LeftFont')
                    self.left_font.configure(family=self.primary_font, size=self.left_font_size, weight='normal')
                else:
                    self.left_font = tkFont.Font(name='LeftFont', family=self.primary_font, size=self.left_font_size, weight='normal')
            except Exception:
                # 後備方案：建立未命名字體物件
                self.left_font = tkFont.Font(family=self.primary_font, size=self.left_font_size, weight='normal')
            
            # Windows 11 統一配色方案 - 確保顏色一致性
            colors = {
                'bg': '#f5f5f5',           # 主背景色（統一淺灰）
                'fg': '#323130',           # 主文字色
                'select_bg': '#0078d4',    # 選中背景色
                'select_fg': 'white',      # 選中文字色
                'entry_bg': '#ffffff',     # 輸入框背景（純白）
                'button_bg': '#f0f0f0',    # 按鈕背景（統一淺灰）
                'button_active': '#e0e0e0', # 按鈕激活色（稍深灰）
                'tab_bg': '#8B4513',       # 標籤頁背景（與按鈕一致）
                'tab_selected_bg': '#A0522D', # 選中標籤頁背景（較深棕色）
                'frame_bg': '#f5f5f5',     # 框架背景（與主背景一致）
                'accent': '#0078d4',       # 強調色
                'success': '#107c10',      # 成功色
                'warning': '#ff8c00',      # 警告色
                'error': '#d13438',        # 錯誤色
                'info': '#0078d4'          # 資訊色
            }
            
            # 設定主視窗背景
            self.root.configure(bg=colors['bg'])
            
            # 通用按鈕樣式 - 使用 LeftFont 命名字體
            style.configure('TButton', 
                          background=colors['button_bg'],
                          foreground=colors['fg'],
                          borderwidth=1,
                          focuscolor='none',
                          padding=(10, 8),
                          font=self.left_font,
                          relief='flat')
            style.map('TButton',
                     background=[('active', colors['button_active']),
                               ('pressed', '#c5c3c1')])
            
            # 輸入框樣式 - 使用 LeftFont 命名字體
            style.configure('TEntry',
                          fieldbackground=colors['entry_bg'],
                          foreground=colors['fg'],
                          borderwidth=1,
                          insertcolor=colors['fg'],
                          font=self.left_font)
            
            # 標籤頁樣式 - 使用檢測到的字體
            style.configure('TNotebook',
                          background=colors['bg'],
                          borderwidth=0,
                          tabmargins=(2, 2, 2, 0))
            style.configure('TNotebook.Tab',
                          background=colors['tab_bg'],
                          foreground='white',  # 初始就是白色文字
                          padding=(14, 10),
                          font=self.left_font)
            style.map('TNotebook.Tab',
                     background=[('selected', colors['tab_selected_bg']),
                               ('active', '#CD853F')],  # 深棕色懸停效果
                     foreground=[('selected', 'black'),
                               ('active', 'white')])
            
            # 控制按鈕專用樣式 - 使用 LeftFont 命名字體
            style.configure('Green.TButton', 
                          background=colors['success'], 
                          foreground='white',
                          padding=(12, 10),
                          font=self.left_font,
                          relief='flat',
                          borderwidth=0)
            style.map('Green.TButton', 
                     background=[('active', '#0e6e0e'), ('pressed', '#0a5a0a')])
            
            style.configure('Blue.TButton', 
                          background=colors['info'], 
                          foreground='white',
                          padding=(12, 10),
                          font=self.left_font,
                          relief='flat',
                          borderwidth=0)
            style.map('Blue.TButton', 
                     background=[('active', '#106ebe'), ('pressed', '#0d5a9e')])
            
            style.configure('Orange.TButton', 
                          background=colors['warning'], 
                          foreground='white',
                          padding=(12, 10),
                          font=self.left_font,
                          relief='flat',
                          borderwidth=0)
            style.map('Orange.TButton', 
                     background=[('active', '#e67e00'), ('pressed', '#cc6f00')])
            
            style.configure('Purple.TButton', 
                          background='#5c2d91', 
                          foreground='white',
                          padding=(12, 10),
                          font=self.left_font,
                          relief='flat',
                          borderwidth=0)
            style.map('Purple.TButton', 
                     background=[('active', '#4a2568'), ('pressed', '#3d1f56')])
            
            style.configure('Red.TButton', 
                          background=colors['error'], 
                          foreground='white',
                          padding=(12, 10),
                          font=(self.primary_font, self.left_font_size, 'bold'),
                          relief='flat',
                          borderwidth=0)
            style.map('Red.TButton', 
                     background=[('active', '#b52d30'), ('pressed', '#a0262a')])
            
            # Checkbutton 樣式 - 使用檢測到的字體和統一背景
            style.configure('TCheckbutton',
                          background=colors['frame_bg'],
                          foreground=colors['fg'],
                          focuscolor='none',
                          font=(self.primary_font, 10))
            style.map('TCheckbutton',
                     background=[('active', colors['button_active'])])
            
            # LabelFrame 樣式 - 使用檢測到的字體和統一背景
            style.configure('TLabelframe',
                          background=colors['frame_bg'],
                          foreground=colors['fg'],
                          borderwidth=1,
                          relief='solid')
            style.configure('TLabelframe.Label',
                          background=colors['frame_bg'],
                          foreground=colors['fg'],
                          font=(self.primary_font, 10, 'bold'))
            
            # Frame 樣式 - 統一背景色
            style.configure('TFrame',
                          background=colors['frame_bg'])
            
            # 輸入框高亮樣式
            style.configure('Highlight.TEntry', 
                          fieldbackground='#fff4ce',
                          borderwidth=2)
            
        except Exception as e:
            print(f"Windows 11 樣式設定失敗: {e}")
            # 設定基本字體作為備用
            self.primary_font = "TkDefaultFont"
            self.left_font = (self.primary_font, self.left_font_size, 'normal')

            # Notebook 標籤頁棕色主題
            style.configure('Brown.TNotebook', background='#efebe9', tabmargins=(4, 2, 4, 0))  # 淡棕背景
            style.configure('Brown.TNotebook.Tab', background='#795548', foreground='white', padding=(10, 6), font=self.left_font)
            style.map('Brown.TNotebook.Tab',
                      background=[('selected', '#5D4037'), ('active', '#6D4C41')],
                      foreground=[('selected', 'white'), ('active', 'white')])

            # 全局 hover 效果：所有 ttk.Button 在滑鼠靠近時變深藍、文字白色，離開還原
            def apply_hover_effect(widget: tk.Widget) -> None:
                try:
                    if isinstance(widget, ttk.Button):
                        # 保存原始樣式
                        try:
                            orig = widget.cget('style')
                            self._orig_styles[widget] = orig
                        except Exception:
                            pass
                        def on_enter(_e):
                            try:
                                widget.configure(style='Blue.TButton')
                            except Exception:
                                pass
                        def on_leave(_e):
                            try:
                                orig = self._orig_styles.get(widget) if isinstance(self._orig_styles, dict) else self._orig_styles.get(widget, None)
                                widget.configure(style=(orig if orig else 'TButton'))
                            except Exception:
                                pass
                        widget.bind('<Enter>', on_enter, add='+')
                        widget.bind('<Leave>', on_leave, add='+')
                    elif isinstance(widget, ttk.Checkbutton):
                        # 保存原始樣式
                        try:
                            orig_cb = widget.cget('style')
                            self._orig_styles[widget] = orig_cb
                        except Exception:
                            pass
                        def on_enter_cb(_e):
                            try:
                                widget.configure(style='Hover.TCheckbutton')
                            except Exception:
                                pass
                        def on_leave_cb(_e):
                            try:
                                orig = self._orig_styles.get(widget) if isinstance(self._orig_styles, dict) else self._orig_styles.get(widget, None)
                                widget.configure(style=(orig if orig else 'TCheckbutton'))
                            except Exception:
                                pass
                        widget.bind('<Enter>', on_enter_cb, add='+')
                        widget.bind('<Leave>', on_leave_cb, add='+')
                except Exception:
                    pass

            def walk_and_apply(container: tk.Widget) -> None:
                try:
                    for child in container.winfo_children():
                        apply_hover_effect(child)
                        walk_and_apply(child)
                except Exception:
                    pass

            # 立即套用 hover 綁定，提升感應速度
            self.root.after(0, lambda: walk_and_apply(self.root))
        except Exception:
            pass

        # 預設設定
        self.var_dut_ip = tk.StringVar(value='192.168.11.143')
        self.var_pc_ip = tk.StringVar(value='192.168.11.142')
        self.var_timeout = tk.StringVar(value='60')
        self.var_username = tk.StringVar(value='root')
        self.var_password = tk.StringVar(value='')  # 保留但不使用

        # 指令相關
        self.var_command_choice = tk.StringVar()
        self.var_clear_output = tk.BooleanVar(value=True)  # 預設打勾

        # 檔案傳輸
        self.var_src_glob = tk.StringVar(value='/mnt/usr/*.jpg')
        self.var_dst_dir = tk.StringVar(value=str(Path('D:/VALO360/4CAM')))
        self.var_common_path = tk.StringVar(value='選擇常用路徑...')

        # 載入設定
        self._load_settings()
        
        # 同步設定主視窗的 popup_font_size
        self.root.popup_font_size = self.popup_font_size
        
        # 初始化字體變數值
        self.var_left_font_size = tk.IntVar(value=self.left_font_size)
        self.var_right_font_size = tk.IntVar(value=self.font_size)
        self.var_popup_font_size = tk.IntVar(value=self.popup_font_size)
        
        # 依設定檔立刻同步左側命名字體大小，避免啟動時使用預設值
        try:
            lf = tkFont.nametofont('LeftFont')
            lf.configure(size=self.left_font_size)
        except Exception:
            try:
                self.left_font = tkFont.Font(name='LeftFont', family=self.primary_font, size=self.left_font_size, weight='normal')
            except Exception:
                pass
        
        self._build_layout()
        self._load_commands_initial()
        
        # 初始化彈出視窗字體
        self._apply_popup_font_size()
        
        # 綁定視窗關閉事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # 綁定鍵盤快捷鍵
        self._bind_keyboard_shortcuts()
        
        # 自動嘗試連線
        self.root.after(1000, self._auto_connect)
        # 啟動後嘗試自動偵測 PC IP（若未填）
        self.root.after(300, self._auto_fill_pc_ip)

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
        # 左右可調整的分隔視窗
        self._paned = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        self._paned.pack(fill=tk.BOTH, expand=True)
        
        # 設定分隔條樣式（更粗，紅色）
        style = ttk.Style()
        style.configure('TPanedwindow', sashwidth=8, sashrelief=tk.RAISED)
        style.map('TPanedwindow', sashcolor=[('active', '#FF0000'), ('!active', '#FF0000')])

        left = ttk.Frame(self._paned, padding=10)
        right = ttk.Frame(self._paned, padding=10)
        self._paned.add(left, weight=2)
        self._paned.add(right, weight=3)

        self._build_left(left)
        self._build_right(right)

        # 若有保存的分隔條位置，套用（延後讓視窗初始化完成）
        def _apply_saved_sash():
            try:
                if hasattr(self, '_saved_sash') and isinstance(self._saved_sash, int):
                    self._safe_set_sash(self._saved_sash)
            except Exception:
                pass
        self.root.after(200, _apply_saved_sash)

    def _build_left(self, parent: ttk.Frame) -> None:
        # 建立主容器（固定，不滾動）
        main_container = ttk.Frame(parent)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # 直接使用 Frame，不添加滾動功能
        scrollable_frame = ttk.Frame(main_container)
        scrollable_frame.pack(fill=tk.BOTH, expand=True)
        
        # 保存 scrollable_frame 引用
        self.scrollable_frame = scrollable_frame
        
        # 標題區域（移除版本設定）
        title_frame = ttk.Frame(scrollable_frame)
        title_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Windows 11 風格主標題 - 使用檢測到的字體
        self.title_label = tk.Label(title_frame, 
                                   text='4CAM DEBUG TOOL', 
                                   font=(self.primary_font, 24, 'bold'),  # 固定 24，不受 LeftFont 控制
                                   foreground='#006400',  # 深綠色文字
                                   background='#FFFFE0')  # 淡黃色背景
        self.title_label.pack(side=tk.LEFT)
        

        # 右側：通用按鍵
        btn_frame = ttk.Frame(title_frame)
        btn_frame.pack(side=tk.RIGHT)


        # 工具列
        toolbar_frame = ttk.Frame(scrollable_frame)
        toolbar_frame.pack(fill=tk.X, pady=(0, 5))

        
        # 連線設定（保留在分頁上方）
        lf_conn = ttk.LabelFrame(scrollable_frame, text='連線設定', padding=8)
        lf_conn.pack(fill=tk.X, pady=(10, 6))
        ent_dut = self._add_labeled_entry(lf_conn, 'DUT IP', self.var_dut_ip, 0)
        self.ent_pc_ip = self._add_labeled_entry(lf_conn, 'PC IP', self.var_pc_ip, 1)
        try:
            self.ent_pc_ip.configure(style='Hint.TEntry')
            ent_dut.bind('<FocusOut>', lambda _e: self._auto_fill_pc_ip())
            self.ent_pc_ip.bind('<KeyRelease>', lambda _e: self._clear_pc_ip_hint_style())
        except Exception:
            pass
        self._add_labeled_entry(lf_conn, 'Username', self.var_username, 2)
        btns = ttk.Frame(lf_conn)
        btns.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))

        # 全域控制已移到頂部工具列
        
        # Notebook 分頁容器
        nb = ttk.Notebook(scrollable_frame, style='Brown.TNotebook')
        nb.pack(fill=tk.BOTH, expand=False)
        tab_cmd = ttk.Frame(nb)
        tab_linux = ttk.Frame(nb)
        tab_manual = ttk.Frame(nb)
        tab_copy = ttk.Frame(nb)
        tab_files = ttk.Frame(nb)
        tab_settings = ttk.Frame(nb)
        nb.add(tab_cmd, text='DUT指令')
        nb.add(tab_linux, text='LINUX 指令')
        nb.add(tab_copy, text='檔案傳輸')
        nb.add(tab_manual, text='手動指令')
        nb.add(tab_files, text='指令表')
        nb.add(tab_settings, text='設定')
        
        # 指令控制（放入 指令 分頁）
        lf_cmd = ttk.LabelFrame(tab_cmd, text='指令控制（COMMANDS/Command.txt）', padding=8)
        lf_cmd.pack(fill=tk.X, pady=(6, 6))
        
        ttk.Label(lf_cmd, text='指令選擇', font=self.left_font).grid(row=1, column=0, sticky=tk.W, pady=(6, 0))
        self.cbo_commands = ttk.Combobox(lf_cmd, textvariable=self.var_command_choice, width=50, state='readonly', font=self.left_font)
        self.cbo_commands.grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=(6, 0), pady=(6, 0))
        self.cbo_commands.bind('<<ComboboxSelected>>', self.on_command_selected)
        Tooltip(self.cbo_commands, text='選擇要執行的指令', min_length=1)
        
        btn_frame = ttk.Frame(lf_cmd)
        btn_frame.grid(row=2, column=0, columnspan=3, sticky=tk.E, pady=(6, 0))
        btn_exec_cmd = ttk.Button(btn_frame, text='執行指令', command=self.on_execute_selected_command, style='Blue.TButton')
        btn_exec_cmd.pack(side=tk.RIGHT)
        Tooltip(btn_exec_cmd, text='執行上方選取的指令')
        
        # 清空勾選已移到全域頂部
        
        # LINUX 指令（放入 LINUX 分頁）
        lf_linux = ttk.LabelFrame(tab_linux, text='Linux 指令集', padding=8)
        lf_linux.pack(fill=tk.X)
        
        # Linux 指令下拉選單
        self.var_linux_choice = tk.StringVar()
        self.cbo_linux = ttk.Combobox(lf_linux, textvariable=self.var_linux_choice, values=[], width=47, state='readonly', font=self.left_font)
        self.cbo_linux.grid(row=0, column=0, padx=(0, 6), pady=(6, 0))
        Tooltip(self.cbo_linux, text='選擇要執行的 Linux 指令', min_length=1)
        
        btn_exec_linux = ttk.Button(lf_linux, text='執行', command=self.on_execute_linux, style='Blue.TButton')
        btn_exec_linux.grid(row=0, column=1, padx=(6, 0), pady=(6, 0))
        Tooltip(btn_exec_linux, text='執行常用 Linux 指令')
        self.root.after(100, self._load_linux_commands)

        # 手動指令（放入 手動指令 分頁）
        lf_manual = ttk.LabelFrame(tab_manual, text='手動輸入指令', padding=8)
        lf_manual.pack(fill=tk.X)
        
        ttk.Label(lf_manual, text='手動輸入指令', font=self.left_font).grid(row=0, column=0, sticky=tk.W, pady=(0, 6))
        manual_frame = ttk.Frame(lf_manual)
        manual_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W)
        self.var_manual_input = tk.StringVar()
        self.ent_manual_input = ttk.Entry(manual_frame, textvariable=self.var_manual_input, width=50, font=self.left_font)
        self.ent_manual_input.pack(fill=tk.X)
        self.ent_manual_input.insert(0, '輸入 Linux 指令，例如：ls -la /mnt/usr/')
        self.ent_manual_input.bind('<FocusIn>', lambda e: self.ent_manual_input.delete(0, tk.END) if self.var_manual_input.get().startswith('輸入 ') else None)
        self.ent_manual_input.bind('<Return>', lambda e: self.on_execute_manual_input())
        
        # 按鍵放在下方
        btn_frame = ttk.Frame(lf_manual)
        btn_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))
        btn_exec_manual = ttk.Button(btn_frame, text='執行自訂', command=self.on_execute_manual_input, style='Blue.TButton')
        btn_exec_manual.pack(side=tk.LEFT)
        Tooltip(btn_exec_manual, text='執行手動輸入的 Linux 指令')

        # 清理快捷（勾選多項後一次執行）
        lf_cleanup = ttk.LabelFrame(tab_linux, text='清理快捷（勾選後按下執行）', padding=8)
        lf_cleanup.pack(fill=tk.X, pady=(8, 0))
        self.var_del_usr_jpg = tk.BooleanVar(value=False)
        self.var_del_usr_yuv = tk.BooleanVar(value=False)
        self.var_del_vsp_jpg = tk.BooleanVar(value=False)
        self.var_del_vsp_yuv = tk.BooleanVar(value=False)

        ck1 = ttk.Checkbutton(lf_cleanup, text='刪除 /mnt/usr/ JPG', variable=self.var_del_usr_jpg)
        ck2 = ttk.Checkbutton(lf_cleanup, text='刪除 /mnt/usr/ YUV', variable=self.var_del_usr_yuv)
        ck3 = ttk.Checkbutton(lf_cleanup, text='刪除 /var/vsp/ JPG', variable=self.var_del_vsp_jpg)
        ck4 = ttk.Checkbutton(lf_cleanup, text='刪除 /var/vsp/ YUV', variable=self.var_del_vsp_yuv)
        ck1.grid(row=0, column=0, sticky=tk.W, padx=(0, 12))
        ck2.grid(row=0, column=1, sticky=tk.W, padx=(0, 12))
        ck3.grid(row=1, column=0, sticky=tk.W, padx=(0, 12), pady=(6, 0))
        ck4.grid(row=1, column=1, sticky=tk.W, padx=(0, 12), pady=(6, 0))

        btn_cleanup = ttk.Button(lf_cleanup, text='執行刪除', command=self.on_execute_cleanup, style='Blue.TButton')
        btn_cleanup.grid(row=0, column=2, rowspan=2, sticky=tk.E, padx=(12, 0))
        Tooltip(btn_cleanup, text='依勾選項目執行刪除指令')
        Tooltip(ck1, text='rm -f /mnt/usr/*.jpg')
        Tooltip(ck2, text='rm -f /mnt/usr/*.yuv')
        Tooltip(ck3, text='rm -f /var/vsp/*.jpg')
        Tooltip(ck4, text='rm -f /var/vsp/*.yuv')
        
        # 檔案傳輸（放入 檔案傳輸 分頁）
        lf_copy = ttk.LabelFrame(tab_copy, text='檔案傳輸（DUT → PC）', padding=8)
        lf_copy.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(lf_copy, text='常用路徑', font=self.left_font).grid(row=0, column=0, sticky=tk.W)
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
                                 width=45, state='readonly', font=self.left_font)
        self.cbo_common.grid(row=0, column=1, sticky=tk.W, padx=(6, 0))
        Tooltip(self.cbo_common, text='選擇常用的檔案路徑', min_length=1)
        self.cbo_common.bind('<<ComboboxSelected>>', self.on_common_path_selected)
        
        self.ent_src = self._add_labeled_entry(lf_copy, '來源（DUT glob）', self.var_src_glob, 1, width=42)
        
        ttk.Label(lf_copy, text='目標（PC 資料夾）', font=self.left_font).grid(row=2, column=0, sticky=tk.W)
        entry_frame = ttk.Frame(lf_copy)
        entry_frame.grid(row=2, column=1, sticky=tk.W, padx=(6, 0))
        self.ent_dst = ttk.Entry(entry_frame, textvariable=self.var_dst_dir, width=42, font=self.left_font)
        self.ent_dst.pack(side=tk.LEFT)
        btn_open_dst = ttk.Button(entry_frame, text='開啟目標資料夾', command=self.on_open_destination_folder, width=12)
        btn_open_dst.pack(side=tk.LEFT, padx=(6, 0))
        Tooltip(btn_open_dst, text='開啟目標資料夾')
        
        btns2 = ttk.Frame(lf_copy)
        btns2.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))
        # 使用說明已移到全域頂部
        btn_copy_all = ttk.Button(btns2, text='將DUT所有資料下載到PC', command=self.on_copy_all_from_dut)
        btn_copy_all.pack(side=tk.LEFT)
        Tooltip(btn_copy_all, text='依常用類型一次下載並自動分類到 JPG/YUV/BIN/CONFIG/LOG')
        btn_copy = ttk.Button(btns2, text='開始傳輸', command=self.on_copy_from_dut, style='Blue.TButton')
        btn_copy.pack(side=tk.LEFT, padx=6)
        Tooltip(btn_copy, text='從 DUT 複製檔案到 PC')
        
        btn_yuv_viewer = ttk.Button(btns2, text='檢視YUV檔案', command=self.on_view_yuv_files, style='Orange.TButton')
        btn_yuv_viewer.pack(side=tk.LEFT, padx=6)
        Tooltip(btn_yuv_viewer, text='檢視已下載的YUV檔案')
        
        # 指令表（放入 指令表 分頁）
        lf_files = ttk.LabelFrame(tab_files, text='指令檔案管理', padding=8)
        lf_files.pack(fill=tk.X, pady=(6, 6))
        
        # 指令表按鈕組
        files_buttons_frame = ttk.Frame(lf_files)
        files_buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        btn_open_cmd = ttk.Button(files_buttons_frame, text='開啟 Command.txt', command=self.on_open_command_file, style='Blue.TButton', width=15)
        btn_open_cmd.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(btn_open_cmd, text='以系統預設編輯器開啟 Command.txt')
        
        btn_open_linux = ttk.Button(files_buttons_frame, text='開啟 linux.txt', command=self.on_open_linux_file, style='Blue.TButton', width=15)
        btn_open_linux.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(btn_open_linux, text='以系統預設程式開啟 linux.txt')
        
        btn_open_download = ttk.Button(files_buttons_frame, text='開啟 download.txt', command=self.on_open_command_files, style='Blue.TButton', width=15)
        btn_open_download.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(btn_open_download, text='開啟 download.txt 指令檔案')
        
        # 套用字體
        for child in lf_conn.winfo_children() + lf_cmd.winfo_children() + lf_linux.winfo_children() + lf_manual.winfo_children() + lf_copy.winfo_children() + lf_files.winfo_children():
            try:
                child.configure(font=self.left_font)
            except Exception:
                pass

        # 存取LOG按鍵已移到頂部工具列

        # 設定分頁內容
        lf_settings = ttk.LabelFrame(tab_settings, text='應用程式設定', padding=8)
        lf_settings.pack(fill=tk.X, pady=(6, 6))

        # 版本設定
        version_frame = ttk.Frame(lf_settings)
        version_frame.grid(row=0, column=0, sticky=tk.W, pady=(0, 15))
        ttk.Label(version_frame, text='應用程式版本', font=self.left_font).grid(row=0, column=0, sticky=tk.W)

        version_controls = ttk.Frame(version_frame)
        version_controls.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        self.ent_version = ttk.Entry(version_controls, textvariable=self.var_app_version, width=15, font=self.left_font)
        self.ent_version.pack(side=tk.LEFT)
        Tooltip(self.ent_version, text='顯示於視窗標題與左上角的版本字串')

        # 當版本變更時，同步視窗標題
        def _on_version_change(*_a):
            try:
                self.root.title(f'4CAM_DEBUG_TOOL {self.var_app_version.get()}')
            except Exception:
                pass
        self.var_app_version.trace_add('write', _on_version_change)

        # 字體設定標籤
        font_label = ttk.Label(lf_settings, text='字體設定', font=('Microsoft JhengHei', 12, 'bold'))
        font_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        
        # 左視窗字體設定
        left_font_frame = ttk.Frame(lf_settings)
        left_font_frame.grid(row=2, column=0, sticky=tk.W, pady=(0, 10))
        ttk.Label(left_font_frame, text='左視窗字體大小', font=self.left_font).grid(row=0, column=0, sticky=tk.W)
        
        left_font_controls = ttk.Frame(left_font_frame)
        left_font_controls.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(left_font_controls, text='大小:', font=self.left_font).pack(side=tk.LEFT)
        ttk.Label(left_font_controls, textvariable=self.var_left_font_size, font=self.left_font, width=3).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(left_font_controls, text='-', width=2, command=self.on_left_font_minus).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(left_font_controls, text='+', width=2, command=self.on_left_font_plus).pack(side=tk.LEFT, padx=(2, 0))
        
        # 右視窗字體設定
        right_font_frame = ttk.Frame(lf_settings)
        right_font_frame.grid(row=3, column=0, sticky=tk.W, pady=(0, 10))
        ttk.Label(right_font_frame, text='右視窗字體大小', font=self.left_font).grid(row=0, column=0, sticky=tk.W)
        
        right_font_controls = ttk.Frame(right_font_frame)
        right_font_controls.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(right_font_controls, text='大小:', font=self.left_font).pack(side=tk.LEFT)
        ttk.Label(right_font_controls, textvariable=self.var_right_font_size, font=self.left_font, width=3).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(right_font_controls, text='-', width=2, command=self.on_right_font_minus).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(right_font_controls, text='+', width=2, command=self.on_right_font_plus).pack(side=tk.LEFT, padx=(2, 0))
        
        # POP文字字體設定
        popup_font_frame = ttk.Frame(lf_settings)
        popup_font_frame.grid(row=4, column=0, sticky=tk.W, pady=(0, 10))
        ttk.Label(popup_font_frame, text='彈出視窗字體大小', font=self.left_font).grid(row=0, column=0, sticky=tk.W)
        
        popup_font_controls = ttk.Frame(popup_font_frame)
        popup_font_controls.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        ttk.Label(popup_font_controls, text='大小:', font=self.left_font).pack(side=tk.LEFT)
        ttk.Label(popup_font_controls, textvariable=self.var_popup_font_size, font=self.left_font, width=3).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(popup_font_controls, text='-', width=2, command=self.on_popup_font_minus).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(popup_font_controls, text='+', width=2, command=self.on_popup_font_plus).pack(side=tk.LEFT, padx=(2, 0))
        
        # 按鈕組：放在左視窗最下方，標籤頁下方，用框線包起來
        button_group_label = ttk.LabelFrame(scrollable_frame, text='控制按鈕', padding=8)
        button_group_label.pack(fill=tk.X, pady=(10, 5))
        
        # 按鈕容器 - 上下兩排佈局
        button_group_frame = ttk.Frame(button_group_label)
        button_group_frame.pack(fill=tk.X)
        
        # 上排：說明、測試SSH、重載指令表
        top_frame = ttk.Frame(button_group_frame)
        top_frame.pack(fill=tk.X, pady=(0, 4))
        
        btn_help = ttk.Button(top_frame, text='說明', command=self.on_show_help, style='Green.TButton')
        btn_help.pack(side=tk.LEFT, padx=(0, 2))
        Tooltip(btn_help, text='開啟使用說明文件')

        btn_test = ttk.Button(top_frame, text='測試SSH', command=self.on_test_connection, style='Blue.TButton')
        btn_test.pack(side=tk.LEFT, padx=(0, 2))
        Tooltip(btn_test, text='測試 SSH 連線狀態')

        btn_reload = ttk.Button(top_frame, text='重載指令表', command=self.on_reload_commands, style='Purple.TButton')
        btn_reload.pack(side=tk.LEFT, padx=(0, 2))
        Tooltip(btn_reload, text='重載所有命令列表')
        
        # 下排：存LOG、清空右視窗
        bottom_frame = ttk.Frame(button_group_frame)
        bottom_frame.pack(fill=tk.X)

        btn_log = ttk.Button(bottom_frame, text='存LOG', command=self.on_save_log_click, style='Orange.TButton')
        btn_log.pack(side=tk.LEFT, padx=(0, 2))
        Tooltip(btn_log, text='將右側輸出全部寫入 LOG/時間日期分鐘.log')

        btn_clear = ttk.Button(bottom_frame, text='清空右視窗', command=self.on_clear_output, style='Red.TButton')
        btn_clear.pack(side=tk.LEFT, padx=(0, 2))
        Tooltip(btn_clear, text='清空右側輸出內容')
        
        # 每次下指令清除舊訊息 checkbox 和 timeout 設定
        control_frame = ttk.Frame(button_group_label)
        control_frame.pack(fill=tk.X, pady=(8, 0))
        
        ck_clear = ttk.Checkbutton(control_frame, text='每次下指令清除舊訊息', variable=self.var_clear_output)
        ck_clear.pack(side=tk.LEFT)
        Tooltip(ck_clear, text='勾選後每次執行指令前會自動清空右側輸出內容')
        
        # Timeout 設定
        ttk.Label(control_frame, text='Timeout(sec):', font=self.left_font).pack(side=tk.LEFT, padx=(20, 5))
        ent_timeout = ttk.Entry(control_frame, textvariable=self.var_timeout, width=8, font=self.left_font)
        ent_timeout.pack(side=tk.LEFT, padx=(0, 5))
        ent_timeout.configure(style='Highlight.TEntry')  # 淡黃色底色
        Tooltip(ent_timeout, text='SSH 連線逾時時間（秒）')

    def _build_right(self, parent: ttk.Frame) -> None:
        # 標題 + SSH連線狀態指示器
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=tk.X)
        
        # 回傳內容標題
        ttk.Label(top_frame, text='回傳內容', font=('Microsoft JhengHei', 12, 'bold')).pack(side=tk.LEFT)
        
        # SSH 連線狀態指示器（靠近回傳內容文字）
        self.status_indicator = tk.Canvas(top_frame, width=20, height=20, highlightthickness=0)
        self.status_indicator.pack(side=tk.LEFT, padx=(8, 0))
        self._update_connection_status('disconnected')

        # 搜尋區塊（右側）
        search_frame = ttk.Frame(top_frame)
        search_frame.pack(side=tk.RIGHT)
        self.var_search = tk.StringVar()
        self.ent_search = ttk.Entry(search_frame, textvariable=self.var_search, width=18)
        self.ent_search.pack(side=tk.LEFT, padx=(0, 4))
        self.btn_search_next = ttk.Button(search_frame, text='搜尋/下一個', command=self.on_search_next)
        self.btn_search_next.pack(side=tk.LEFT)
        self.btn_search_clear = ttk.Button(search_frame, text='清除標記', command=self.on_search_clear)
        self.btn_search_clear.pack(side=tk.LEFT, padx=(4, 0))
        # 追蹤上一個搜尋位置
        self._last_search_index = '1.0'
        
        self.txt_output = ScrolledText(parent, width=50, height=30, font=('Microsoft JhengHei', self.font_size))
        self.txt_output.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
    def _build_right(self, parent: ttk.Frame) -> None:
        # 標題 + SSH連線狀態指示器
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=tk.X)
        
        # 回傳內容標題
        title_label = ttk.Label(top_frame, text='回傳內容', font=('Segoe UI', 12, 'bold'))
        title_label.pack(side=tk.LEFT)
        Tooltip(title_label, text='顯示 SSH 指令執行結果和系統訊息')
        
        # SSH 連線狀態指示器（靠近回傳內容文字）
        self.status_indicator = tk.Canvas(top_frame, width=20, height=20, highlightthickness=0)
        self.status_indicator.pack(side=tk.LEFT, padx=(8, 0))
        self._update_connection_status('disconnected')
        Tooltip(self.status_indicator, text='SSH 連線狀態：綠色=已連線，黃色=連線中，黑色=未連線')

        # 搜尋區塊（右側）
        search_frame = ttk.Frame(top_frame)
        search_frame.pack(side=tk.RIGHT)
        self.var_search = tk.StringVar()
        self.ent_search = ttk.Entry(search_frame, textvariable=self.var_search, width=18)
        self.ent_search.pack(side=tk.LEFT, padx=(0, 4))
        Tooltip(self.ent_search, text='輸入要搜尋的文字，支援正則表達式')
        
        self.btn_search_next = ttk.Button(search_frame, text='搜尋/下一個', command=self.on_search_next)
        self.btn_search_next.pack(side=tk.LEFT)
        Tooltip(self.btn_search_next, text='搜尋文字並標記結果，重複點擊可找下一個')
        
        self.btn_search_clear = ttk.Button(search_frame, text='清除標記', command=self.on_search_clear)
        self.btn_search_clear.pack(side=tk.LEFT, padx=(4, 0))
        Tooltip(self.btn_search_clear, text='清除所有搜尋標記，恢復正常顯示')
        
        # 追蹤上一個搜尋位置
        self._last_search_index = '1.0'
        
        self.txt_output = ScrolledText(parent, width=50, height=30, font=('Cascadia Code', self.font_size))
        self.txt_output.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        Tooltip(self.txt_output, text='SSH 指令執行結果顯示區域\n• 綠色：成功訊息\n• 紅色：錯誤訊息\n• 藍色：資訊訊息\n• 黑色：一般輸出')
        
        # 加粗直向捲動條
        try:
            if hasattr(self.txt_output, 'vbar') and self.txt_output.vbar:
                self.txt_output.vbar.configure(width=18)
        except Exception:
            pass
        
        # 設定文字標籤顏色
        self.txt_output.tag_configure("success", foreground="green", font=('Microsoft JhengHei', self.font_size, 'bold'))
        self.txt_output.tag_configure("error", foreground="red", font=('Microsoft JhengHei', self.font_size, 'bold'))
        self.txt_output.tag_configure("warning", foreground="orange", font=('Microsoft JhengHei', self.font_size, 'bold'))
        self.txt_output.tag_configure("info", foreground="blue", font=('Microsoft JhengHei', self.font_size, 'bold'))
        self.txt_output.tag_configure("file", foreground="purple", font=('Microsoft JhengHei', self.font_size, 'bold'))
        self.txt_output.tag_configure("path", foreground="darkgreen", font=('Microsoft JhengHei', self.font_size, 'bold'))
        
        # 檔案高亮標籤 - 移除背景色，JPG和YUV使用綠色
        self.txt_output.tag_configure("file_yuv", foreground="green", font=('Microsoft JhengHei', self.font_size, 'bold'))
        self.txt_output.tag_configure("file_jpg", foreground="green", font=('Microsoft JhengHei', self.font_size, 'bold'))
        self.txt_output.tag_configure("file_bin", foreground="darkgreen", font=('Microsoft JhengHei', self.font_size, 'bold'))
        self.txt_output.tag_configure("file_log", foreground="darkorange", font=('Microsoft JhengHei', self.font_size, 'bold'))
        self.txt_output.tag_configure("file_yml", foreground="darkmagenta", font=('Microsoft JhengHei', self.font_size, 'bold'))
        self.txt_output.tag_configure("file_other", foreground="black", font=('Microsoft JhengHei', self.font_size, 'bold'))
        
        # 特殊指令標籤
        self.txt_output.tag_configure("diag_sn", foreground="purple", font=('Microsoft JhengHei', self.font_size, 'bold'))

        # 搜尋標記（淡黃色反白）
        self.txt_output.tag_configure("search_hit", background="#fff9c4", foreground="black", font=('Microsoft JhengHei', self.font_size))

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
        ttk.Label(parent, text=label, font=getattr(self, 'left_font', None)).grid(row=row, column=0, sticky=tk.W, pady=2)
        ent = ttk.Entry(parent, textvariable=var, width=width, show=show, font=getattr(self, 'left_font', None))
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
        path = Path(get_resource_path('COMMANDS/Command.txt'))
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
                    # 分隔條位置
                    sash = settings['window'].get('sash')
                    if isinstance(sash, int):
                        self._saved_sash = sash
                
                # 載入連線設定
                if 'connection' in settings:
                    conn = settings['connection']
                    self.var_dut_ip.set(conn.get('dut_ip', '192.168.11.143'))
                    self.var_pc_ip.set(conn.get('pc_ip', '192.168.11.142'))
                    self.var_username.set(conn.get('username', 'root'))
                    self.var_password.set(conn.get('password', ''))
                    # 將逾時預設提升為 60 秒（若設定檔未提供）
                    self.var_timeout.set(str(conn.get('timeout', 60)))
                
                # 載入檔案設定
                if 'files' in settings:
                    files = settings['files']
                    self.var_src_glob.set(files.get('src_glob', '/mnt/usr/*.jpg'))
                    self.var_dst_dir.set(files.get('dst_dir', str(Path('D:/VALO360/4CAM'))))
                # 載入應用版本
                if 'app' in settings:
                    app_cfg = settings['app']
                    ver = app_cfg.get('version')
                    if ver:
                        self.var_app_version.set(str(ver))
                        try:
                            self.root.title(f'4CAM_DEBUG_TOOL {self.var_app_version.get()}')
                        except Exception:
                            pass
                
                # 載入字體設定
                if 'ui' in settings:
                    self.font_size = settings['ui'].get('font_size', 12)
                    self.left_font_size = settings['ui'].get('left_font_size', 10)
                    self.popup_font_size = settings['ui'].get('popup_font_size', 12)
                    # 載入清空輸出設定
                    clear_output = settings['ui'].get('clear_output', True)
                    self.var_clear_output.set(clear_output)
                    
        except Exception as e:
            logging.error(f"載入設定失敗: {e}")

    def _save_settings(self) -> None:
        """儲存設定檔案"""
        try:
            # 讀取分隔條位置
            try:
                sash_pos = int(self._paned.sashpos(0)) if hasattr(self, '_paned') else None
            except Exception:
                sash_pos = None

            window_cfg = {
                'geometry': self.root.geometry()
            }
            if sash_pos is not None:
                window_cfg['sash'] = sash_pos

            settings = {
                'window': window_cfg,
                'connection': {
                    'dut_ip': self.var_dut_ip.get(),
                    'pc_ip': self.var_pc_ip.get(),
                    'username': self.var_username.get(),
                    'password': self.var_password.get(),
                    'timeout': int(self.var_timeout.get() or '60')
                },
                'files': {
                    'src_glob': self.var_src_glob.get(),
                    'dst_dir': self.var_dst_dir.get()
                },
                'ui': {
                    'font_size': self.font_size,
                    'left_font_size': self.left_font_size,
                    'popup_font_size': self.popup_font_size,
                    'clear_output': self.var_clear_output.get()
                },
                'app': {
                    'version': self.var_app_version.get()
                }
            }
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logging.error(f"儲存設定失敗: {e}")

    def _load_commands_from(self, path: Path) -> None:
        try:
            self.current_commands = load_commands_from_file(path)
            display_items = [f"{i+1}. {c.name} = {c.command}" for i, c in enumerate(self.current_commands)]
            self.cbo_commands["values"] = display_items
            if display_items:
                self.cbo_commands.current(0)
                self.var_command_choice.set(display_items[0])
            self._append_output(f"已載入指令：{len(self.current_commands)} 項，來源 {path}")
        except Exception as exc:
            messagebox.showerror('錯誤', f'載入指令失敗：{exc}')

    # ---------- 事件 ----------
    def on_left_font_plus(self) -> None:
        if self.left_font_size < 16:
            self.left_font_size += 1
            self.var_left_font_size.set(self.left_font_size)
            self._apply_left_font_size()

    def on_left_font_minus(self) -> None:
        if self.left_font_size > 8:
            self.left_font_size -= 1
            self.var_left_font_size.set(self.left_font_size)
            self._apply_left_font_size()

    def on_right_font_plus(self) -> None:
        if self.font_size < 20:
            self.font_size += 1
            self.var_right_font_size.set(self.font_size)
            self._apply_right_font_size()

    def on_right_font_minus(self) -> None:
        if self.font_size > 10:
            self.font_size -= 1
            self.var_right_font_size.set(self.font_size)
            self._apply_right_font_size()

    def on_popup_font_plus(self) -> None:
        if self.popup_font_size < 18:
            self.popup_font_size += 1
            self.var_popup_font_size.set(self.popup_font_size)
            # 同步更新主視窗的 popup_font_size
            self.root.popup_font_size = self.popup_font_size
            self._apply_popup_font_size()

    def on_popup_font_minus(self) -> None:
        if self.popup_font_size > 10:
            self.popup_font_size -= 1
            self.var_popup_font_size.set(self.popup_font_size)
            # 同步更新主視窗的 popup_font_size
            self.root.popup_font_size = self.popup_font_size
            self._apply_popup_font_size()


    def on_pick_command_file(self) -> None:
        file_path = filedialog.askopenfilename(title='選擇 Command.txt', filetypes=[('Text', '*.txt'), ('All', '*.*')])
        if file_path:
            self.var_command_file.set(file_path)
            self._load_commands_from(Path(file_path))


    def on_open_linux_file(self) -> None:
        """開啟 linux.txt 指令檔案"""
        try:
            file_path = Path(get_resource_path('COMMANDS/linux.txt'))
            
            if file_path.exists():
                import subprocess
                import os
                import platform
                
                if platform.system() == 'Windows':
                    os.startfile(str(file_path))
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', str(file_path)])
                else:  # Linux
                    subprocess.run(['xdg-open', str(file_path)])
                    
                self._append_output(f'已開啟 linux.txt：{file_path}', 'info')
            else:
                messagebox.showwarning('提醒', f'linux.txt 檔案不存在：{file_path}')
        except Exception as e:
            self._append_output(f'無法開啟 linux.txt：{e}', 'error')

    def on_execute_cleanup(self) -> None:
        """執行 Linux TAB 內勾選的清理刪除指令。"""
        try:
            cmds: list[str] = []
            if hasattr(self, 'var_del_usr_jpg') and self.var_del_usr_jpg.get():
                cmds.append('rm -f /mnt/usr/*.jpg')
            if hasattr(self, 'var_del_usr_yuv') and self.var_del_usr_yuv.get():
                cmds.append('rm -f /mnt/usr/*.yuv')
            if hasattr(self, 'var_del_vsp_jpg') and self.var_del_vsp_jpg.get():
                cmds.append('rm -f /var/vsp/*.jpg')
            if hasattr(self, 'var_del_vsp_yuv') and self.var_del_vsp_yuv.get():
                cmds.append('rm -f /var/vsp/*.yuv')

            if not cmds:
                self._append_output('未勾選任何刪除項目', 'warning')
                return

            multi = '||'.join(cmds)
            self._run_bg(lambda: self._task_exec_command(multi))
        except Exception as e:
            self._append_output(f'執行刪除失敗：{e}', 'error')

    def on_open_command_file(self) -> None:
        """開啟指令表檔案"""
        command_file = Path(get_resource_path('COMMANDS/Command.txt'))
        if command_file.exists():
            try:
                # 使用系統預設程式開啟檔案
                import subprocess
                import platform
                
                if platform.system() == 'Windows':
                    os.startfile(str(command_file))
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', str(command_file)])
                else:  # Linux
                    subprocess.run(['xdg-open', str(command_file)])
                    
                self._append_output(f'已開啟指令表：{command_file}', 'info')
            except Exception as e:
                self._append_output(f'無法開啟指令表：{e}', 'error')
        else:
            messagebox.showwarning('提醒', '指令表檔案不存在，請先選擇有效的指令表檔案')

    def _open_file_path(self, path_str: str) -> None:
        """以系統預設程式開啟任意檔案路徑。"""
        try:
            if not path_str:
                messagebox.showwarning('提醒', '沒有可開啟的檔案')
                return
            p = Path(path_str)
            if not p.exists():
                messagebox.showwarning('提醒', f'檔案不存在：{p}')
                return
            import subprocess, platform
            if platform.system() == 'Windows':
                os.startfile(str(p))
            elif platform.system() == 'Darwin':
                subprocess.run(['open', str(p)])
            else:
                subprocess.run(['xdg-open', str(p)])
            self._append_output(f'已開啟檔案：{p}', 'info')
        except Exception as e:
            self._append_output(f'無法開啟檔案：{e}', 'error')

    def on_reload_commands(self, *_args) -> None:
        # 重新載入所有指令檔案：Command.txt、linux.txt、download.txt
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
            # 檢查 download.txt 是否存在並可讀取
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

    def on_command_selected(self, _evt) -> None:
        idx = self.cbo_commands.current()
        if 0 <= idx < len(self.current_commands):
            pass  # 不需要做任何事，因為指令選擇已經在下拉選單中顯示

    def on_test_connection(self) -> None:
        self._auto_fill_pc_ip()
        self._run_bg(self._task_test_connection)

    def on_execute_selected_command(self) -> None:
        # 根據 checkbox 狀態決定是否清空輸出
        if self.var_clear_output.get():
            self.txt_output.delete(1.0, tk.END)
            
        idx = self.cbo_commands.current()
        if 0 <= idx < len(self.current_commands):
            cmd = self.current_commands[idx].command
            self._run_bg(lambda: self._task_exec_command(cmd))
        else:
            messagebox.showwarning('提醒', '沒有指令可執行')

    def on_execute_unified(self) -> None:
        """統一執行：優先順序 自訂Linux > Linux下拉 > 指令表下拉 > 檔案傳輸。"""
        # 自訂 Linux（若輸入框有焦點且有內容，或內容非預設提示）
        manual_text = (self.var_manual_input.get() if hasattr(self, 'var_manual_input') else '').strip()
        if manual_text and not manual_text.startswith('輸入 '):
            if self.var_clear_output.get():
                self.txt_output.delete(1.0, tk.END)
            self._run_bg(lambda: self._task_exec_command(manual_text))
            return

        # 指令表下拉（Command.txt）
        idx_cmd = self.cbo_commands.current()
        if idx_cmd is not None and 0 <= idx_cmd < len(self.current_commands):
            if self.var_clear_output.get():
                self.txt_output.delete(1.0, tk.END)
            cmd = self.current_commands[idx_cmd].command
            self._run_bg(lambda: self._task_exec_command(cmd))
            return

        # 常用 Linux 下拉
        if hasattr(self, 'cbo_linux') and hasattr(self, 'linux_items'):
            idx_linux = self.cbo_linux.current()
            if idx_linux is not None and 0 <= idx_linux < len(self.linux_items):
                if self.var_clear_output.get():
                    self.txt_output.delete(1.0, tk.END)
                _name, cmd = self.linux_items[idx_linux]
                self._run_bg(lambda: self._task_exec_command(cmd))
                return

        # 檔案傳輸（檢查來源與目標有效）
        src = self.var_src_glob.get().strip() if hasattr(self, 'var_src_glob') else ''
        dst = self.var_dst_dir.get().strip() if hasattr(self, 'var_dst_dir') else ''
        if src and dst:
            if self.var_clear_output.get():
                self.txt_output.delete(1.0, tk.END)
            self._run_bg(lambda: self._task_copy_from_dut(src, dst))
            return

        messagebox.showwarning('提醒', '沒有可執行的內容，請先選擇或輸入指令')

    def on_execute_linux(self) -> None:
        # 以索引對應 COMMANDS/linux.txt 所載入的項目
        idx = self.cbo_linux.current() if hasattr(self, 'cbo_linux') else -1
        if idx is None or idx < 0 or not hasattr(self, 'linux_items') or idx >= len(self.linux_items):
            messagebox.showwarning('提醒', '請先選擇有效的 LINUX 指令')
            return

        if self.var_clear_output.get():
            self.txt_output.delete(1.0, tk.END)

        _name, cmd = self.linux_items[idx]
        self._run_bg(lambda: self._task_exec_command(cmd))

    def on_execute_manual_input(self) -> None:
        cmd = (self.var_manual_input.get() or '').strip()
        if not cmd:
            messagebox.showwarning('提醒', '請輸入要執行的 Linux 指令')
            return
        if self.var_clear_output.get():
            self.txt_output.delete(1.0, tk.END)
        self._run_bg(lambda: self._task_exec_command(cmd))


    def on_show_help(self) -> None:
        """開啟 HTML 使用說明文件（僅開啟，不再自動覆寫）。"""
        try:
            help_file = Path('4CAM_DEBUG_TOOL_使用說明.html')
            if not help_file.exists():
                messagebox.showwarning('提醒', '找不到說明檔，請通知維護者或重新產生。')
                return
            import webbrowser, os
            webbrowser.open(f'file://{os.path.abspath(help_file)}')
            self._append_output(f'已開啟使用說明：{help_file.absolute()}')
        except Exception as exc:
            messagebox.showerror('錯誤', f'開啟說明失敗：{exc}')

    # ---------- LINUX 指令載入 ----------
    def _get_linux_commands_path(self) -> Path:
        """優先使用執行檔所在目錄下的 COMMANDS/linux.txt；若不存在，從內嵌資源複製一份後使用外部檔。"""
        try:
            exec_dir = Path(getattr(sys, 'frozen', False) and Path(sys.executable).parent or Path.cwd())
        except Exception:
            exec_dir = Path.cwd()
        external_dir = exec_dir / 'COMMANDS'
        _safe_makedirs(external_dir)
        external_path = external_dir / 'linux.txt'

        if external_path.exists():
            return external_path

        # 嘗試從內嵌資源複製到外部，之後固定使用外部檔
        try:
            embedded_path = Path(get_resource_path('COMMANDS/linux.txt'))
            if embedded_path.exists():
                try:
                    external_path.write_text(embedded_path.read_text(encoding='utf-8'), encoding='utf-8')
                except Exception:
                    pass
        except Exception:
            pass

        return external_path

    def _ensure_linux_commands_file(self) -> None:
        path = self._get_linux_commands_path()
        if not path.exists():
            default_lines = [
                '# 常用 LINUX 指令（格式：NAME = COMMAND）',
                '# 範例：列出 /mnt/usr/ 所有檔案 = ls -la /mnt/usr/',
                '',
                '列出 /mnt/usr/ 所有檔案 = ls -la /mnt/usr/',
                '刪除 /mnt/usr/ JPG 檔 = rm -f /mnt/usr/*.jpg',
                '刪除 /mnt/usr/ YUV 檔 = rm -f /mnt/usr/*.yuv',
                '刪除 /var/vsp/ JPG 檔 = rm -f /var/vsp/*.jpg',
                '刪除 /var/vsp/ YUV 檔 = rm -f /var/vsp/*.yuv',
                '顯示系統資訊 = uname -a',
                '顯示磁碟使用量 = df -h',
                '顯示記憶體使用量 = free -h',
                '顯示目前目錄詳細檔案 = ls -la',
                '列出根目錄檔案 = ls -la /',
                '列出臨時目錄檔案 = ls -la /tmp',
                '列出使用者目錄檔案 = ls -la /mnt/usr',
                '網路連線 = netstat -an',
                '網路介面 = ifconfig',
                '路由表 = route -n',
                '核心版本 = cat /proc/version',
                'CPU 資訊 = cat /proc/cpuinfo',
                '記憶體資訊 = cat /proc/meminfo',
                '系統運行時間 = uptime',
                '系統時間 = date',
                '硬體時鐘 = hwclock',
                '掛載點 = mount',
                '已載入模組 = lsmod',
                'USB 設備 = lsusb',
                'PCI 設備 = lspci',
                'I2C 匯流排 0 = i2cdetect -y 0',
                'I2C 匯流排 1 = i2cdetect -y 1',
                '最近核心訊息 = dmesg | tail -20',
                '錯誤訊息過濾 = dmesg | grep -i error',
                '攝影機訊息過濾 = dmesg | grep -i camera',
                'VSP 目錄 = ls -la /var/vsp',
                'TMP TAR 目錄 = ls -la /tmp/tar',
                '檢查錄影程序 = ps aux | grep hd_video',
                '檢查診斷程序 = ps aux | grep diag',
                '停止錄影程序 = killall hd_video_record_with_vsp_4dev_smart2_pega_dre',
                '檢查 /tmp 空間 = df -h /tmp',
                '檢查 /var/vsp 空間 = df -h /var/vsp',
                '檢查 /mnt/usr 空間 = df -h /mnt/usr',
                '系統負載 = cat /proc/loadavg',
            ]
            try:
                path.write_text('\n'.join(default_lines), encoding='utf-8')
            except Exception:
                pass

    def _get_default_linux_commands(self) -> list[tuple[str, str]]:
        """內建的常用 LINUX 指令（作為補齊來源）。"""
        return [
            ('列出 /mnt/usr/ 所有檔案', 'ls -la /mnt/usr/'),
            ('刪除 /mnt/usr/ JPG 檔', 'rm -f /mnt/usr/*.jpg'),
            ('刪除 /mnt/usr/ YUV 檔', 'rm -f /mnt/usr/*.yuv'),
            ('刪除 /var/vsp/ JPG 檔', 'rm -f /var/vsp/*.jpg'),
            ('刪除 /var/vsp/ YUV 檔', 'rm -f /var/vsp/*.yuv'),
            ('顯示系統資訊', 'uname -a'),
            ('顯示磁碟使用量', 'df -h'),
            ('顯示記憶體使用量', 'free -h'),
            ('顯示目前目錄詳細檔案', 'ls -la'),
            ('列出根目錄檔案', 'ls -la /'),
            ('列出臨時目錄檔案', 'ls -la /tmp'),
            ('列出使用者目錄檔案', 'ls -la /mnt/usr'),
            ('網路連線', 'netstat -an'),
            ('網路介面', 'ifconfig'),
            ('路由表', 'route -n'),
            ('核心版本', 'cat /proc/version'),
            ('CPU 資訊', 'cat /proc/cpuinfo'),
            ('記憶體資訊', 'cat /proc/meminfo'),
            ('系統運行時間', 'uptime'),
            ('系統時間', 'date'),
            ('硬體時鐘', 'hwclock'),
            ('掛載點', 'mount'),
            ('已載入模組', 'lsmod'),
            ('USB 設備', 'lsusb'),
            ('PCI 設備', 'lspci'),
            ('I2C 匯流排 0', 'i2cdetect -y 0'),
            ('I2C 匯流排 1', 'i2cdetect -y 1'),
            ('最近核心訊息', 'dmesg | tail -20'),
            ('錯誤訊息過濾', 'dmesg | grep -i error'),
            ('攝影機訊息過濾', 'dmesg | grep -i camera'),
            ('VSP 目錄', 'ls -la /var/vsp'),
            ('TMP TAR 目錄', 'ls -la /tmp/tar'),
            ('檢查錄影程序', 'ps aux | grep hd_video'),
            ('檢查診斷程序', 'ps aux | grep diag'),
            ('停止錄影程序', 'killall hd_video_record_with_vsp_4dev_smart2_pega_dre'),
            ('檢查 /tmp 空間', 'df -h /tmp'),
            ('檢查 /var/vsp 空間', 'df -h /var/vsp'),
            ('檢查 /mnt/usr 空間', 'df -h /mnt/usr'),
            ('系統負載', 'cat /proc/loadavg'),
        ]

    def _append_default_linux_commands_if_missing(self) -> None:
        """將內建常用指令補齊到 linux.txt（以名稱去重），不覆蓋既有內容。"""
        path = self._get_linux_commands_path()
        try:
            existing_lines = path.read_text(encoding='utf-8').splitlines()
        except Exception:
            existing_lines = []

        # 解析既有名稱集合
        existing_names = set()
        for raw in existing_lines:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            if ' = ' in line:
                name, _cmd = line.split(' = ', 1)
                existing_names.add(name.strip())

        # 準備要追加的行
        to_add = []
        for name, cmd in self._get_default_linux_commands():
            if name not in existing_names:
                to_add.append(f'{name} = {cmd}')

        if to_add:
            try:
                with open(path, 'a', encoding='utf-8') as f:
                    if existing_lines and existing_lines[-1].strip() != '':
                        f.write('\n')
                    f.write('\n'.join(to_add) + '\n')
            except Exception:
                pass

    def _load_linux_commands(self) -> None:
        """讀取預設的 Linux 指令檔案並更新下拉顯示（含編號）。"""
        # 使用打包後的檔案路徑
        path = Path(get_resource_path('COMMANDS/linux.txt'))
        
        # 如果檔案不存在，建立預設檔案
        if not path.exists():
                self._ensure_linux_commands_file()
                path = self._get_linux_commands_path()
        
        self._load_linux_commands_from_file(path)

    def _load_linux_commands_from_file(self, path: Path) -> None:
        """從指定檔案讀取 Linux 指令並更新下拉顯示（含編號）。"""
        items = []
        try:
            for raw in path.read_text(encoding='utf-8').splitlines():
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                # 修正：支援兩種格式：' = ' 和 '='
                if '=' in line:
                    if ' = ' in line:
                        name, cmd = line.split(' = ', 1)
                    else:
                        name, cmd = line.split('=', 1)
                    name = name.strip()
                    cmd = cmd.strip()
                    if name and cmd:
                        items.append((name, cmd))
        except Exception as e:
            self._append_output(f'載入 linux.txt 失敗：{e}', 'error')
            items = []

        self.linux_items = items
        display = [f'{i+1}. {name} = {cmd}' for i, (name, cmd) in enumerate(items)]
        if hasattr(self, 'cbo_linux'):
            # 清除現有選項
            self.cbo_linux['values'] = []
            self.cbo_linux.update()
            
            # 設定新選項
            self.cbo_linux['values'] = display
            if display:
                self.cbo_linux.current(0)
                self.var_linux_choice.set(display[0])
            else:
                self.var_linux_choice.set('')
            
            # 強制更新下拉選單
            self.cbo_linux.update()
            self.root.update_idletasks()
        
        # 顯示載入結果
        msg = f'已載入 LINUX 指令：{len(items)} 項，來源 {path}'
        if hasattr(self, 'txt_output') and self.txt_output:
            self._append_output(msg)
        else:
            logging.info(msg)

    def _generate_help_html(self) -> str:
        """產生 HTML 使用說明文件"""
        import datetime
        
        html_content = r"""<!DOCTYPE html>
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
                <li><strong>SSH 連線管理</strong>：自動連線到 DUT 設備，支援連線狀態指示器</li>
                <li><strong>六標籤頁介面</strong>：DUT指令、LINUX 指令、檔案傳輸、手動指令、指令表、設定</li>
                <li><strong>指令執行</strong>：支援預設指令、Linux 指令集和手動輸入指令</li>
                <li><strong>檔案傳輸</strong>：使用 SCP 從 DUT 下載檔案到 PC</li>
                <li><strong>指令表管理</strong>：統一管理所有指令檔案的開啟功能（Command.txt、linux.txt、download.txt）</li>
                <li><strong>控制按鈕組</strong>：五個不同顏色按鈕，包含說明、測試SSH、存LOG、重載指令表、清空右視窗</li>
                <li><strong>Timeout 設定</strong>：SSH 連線逾時時間設定</li>
                <li><strong>左右視窗分隔條</strong>：8像素粗的紅色分隔條，方便調整視窗大小</li>
                <li><strong>鍵盤快捷鍵</strong>：F1(說明)、F5(重載)、Ctrl+L(清空)、Ctrl+S(存LOG)、Ctrl+T(測試SSH)</li>
                <li><strong>Windows 11 風格</strong>：採用現代化配色方案、深棕色TAB標籤頁、白色文字配淡黃色背景標題</li>
                <li><strong>設定保存</strong>：自動保存和載入使用者設定</li>
                <li><strong>字體調整</strong>：可調整左側、右側、彈出視窗的獨立字體大小</li>
            </ul>
        </div>

        <div class="section">
            <h2>🚀 快速開始</h2>
            <ol>
                <li><strong>啟動程式</strong>：執行 <code>python main.py</code> 或雙擊 EXE 檔案</li>
                <li><strong>檢查連線</strong>：程式會自動嘗試連線到 DUT（預設 IP：192.168.11.143）</li>
                <li><strong>執行指令</strong>：在各個標籤頁選擇指令並點擊「執行」</li>
                <li><strong>檔案傳輸</strong>：設定來源和目標路徑，點擊「開始傳輸」</li>
                <li><strong>指令表管理</strong>：在「指令表」標籤頁開啟各種指令檔案進行編輯</li>
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
                <li>從 <code>COMMANDS/Command.txt</code> 載入預設指令</li>
                <li>支援下拉選單選擇</li>
                <li>指令格式：<code>指令名稱 = 完整指令</code></li>
            </ul>

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
            
        # 根據 checkbox 狀態決定是否清空輸出
        if self.var_clear_output.get():
            self.txt_output.delete(1.0, tk.END)
            
        self._run_bg(lambda: self._task_copy_from_dut(src, dst))

    def on_view_yuv_files(self) -> None:
        """開啟 YUV 檔案檢視器"""
        try:
            # 檢查目標資料夾
            dst_dir = Path(self.var_dst_dir.get().strip())
            if not dst_dir.exists():
                messagebox.showwarning('提醒', '目標資料夾不存在，請先設定正確的目標路徑')
                return
                
            # 掃描 YUV 檔案
            yuv_files = list(dst_dir.glob('**/*.yuv'))
            if not yuv_files:
                messagebox.showinfo('資訊', '目標資料夾中沒有找到 YUV 檔案')
                return
                
            # 創建並開啟 YUV 檢視器
            yuv_viewer = create_yuv_viewer(self.root, self.primary_font, self.left_font, self._append_output)
            yuv_viewer.open_viewer(yuv_files, dst_dir)
            
        except Exception as e:
            messagebox.showerror('錯誤', f'開啟 YUV 檢視器失敗：{e}')
            self._append_output(f'❌ YUV 檢視器錯誤：{e}', 'error')

    def on_copy_all_from_dut(self) -> None:
        """將常用類型一次下載並分類到子資料夾。"""
        try:
            # 以 D:\VALO360 作為分類根目錄
            base_dst = Path(r'D:\VALO360')
            plans = [
                # /mnt/usr
                ('/mnt/usr/*.jpg', base_dst / 'JPG'),
                ('/mnt/usr/*.yuv', base_dst / 'YUV'),
                ('/mnt/usr/*.bin', base_dst / 'BIN'),
                ('/mnt/usr/*.yml', base_dst / 'CONFIG'),
                ('/mnt/usr/*.log', base_dst / 'LOG'),
                # /var/vsp
                ('/var/vsp/*.jpg', base_dst / 'JPG'),
                ('/var/vsp/*.yuv', base_dst / 'YUV'),
                ('/var/vsp/*.bin', base_dst / 'BIN'),
                ('/var/vsp/*.yml', base_dst / 'CONFIG'),
                ('/var/vsp/*.log', base_dst / 'LOG'),
                # /tmp 也下載
                ('/tmp/*.jpg', base_dst / 'JPG'),
                ('/tmp/*.yuv', base_dst / 'YUV'),
                ('/tmp/*.bin', base_dst / 'BIN'),
                ('/tmp/*.log', base_dst / 'LOG'),
            ]
            # 逐項在背景執行，序列化下載避免裝置壓力
            def _run_batch():
                for src_glob, dst_dir in plans:
                    try:
                        self._task_copy_from_dut(src_glob, str(dst_dir))
                    except Exception as e:
                        self._append_output(f'批次下載錯誤：{e}', 'error')
            self._run_bg(_run_batch)
        except Exception as e:
            self._append_output(f'無法啟動批次下載：{e}', 'error')

    def on_common_path_selected(self, event=None) -> None:
        """處理常用路徑選擇"""
        selected = self.var_common_path.get()
        if selected and selected != '選擇常用路徑...':
            # 根據 checkbox 狀態決定是否清空輸出
            if self.var_clear_output.get():
                self.txt_output.delete(1.0, tk.END)
                
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

    def on_open_command_files(self) -> None:
        """開啟 download.txt 指令檔案"""
        try:
            file_path = Path('COMMANDS') / 'download.txt'
            if not file_path.exists():
                messagebox.showwarning('提醒', 'download.txt 檔案不存在')
                return
            
            # 開啟 download.txt 檔案
            import subprocess
            import platform
            
            if platform.system() == 'Windows':
                os.startfile(str(file_path))
            else:
                subprocess.run(['xdg-open', str(file_path)])
                
        except Exception as e:
            messagebox.showerror('錯誤', f'開啟檔案時發生錯誤：{e}')

    def on_open_destination_folder(self) -> None:
        """開啟目標資料夾（優先開啟 D:\\VALO360 根目錄）。"""
        try:
            dst_path = self.var_dst_dir.get().strip()
            if not dst_path:
                messagebox.showwarning('提醒', '請先輸入目標資料夾路徑')
                return
            
            from pathlib import Path
            import os
            base = Path(r'D:\\VALO360')
            dst = Path(dst_path)
            # 優先開啟 D:\VALO360（若目標在其底下）
            to_open = base if str(dst).upper().startswith(str(base).upper()) else dst
            # 確保要開啟的目錄存在
            if not to_open.exists():
                try:
                    to_open.mkdir(parents=True, exist_ok=True)
                    self._append_output(f'已建立資料夾：{to_open}')
                except Exception as e:
                    messagebox.showerror('錯誤', f'無法建立資料夾：{e}')
                    return
            # 開啟
            if os.name == 'nt':
                os.startfile(str(to_open))
            elif os.name == 'posix':
                os.system(f'open "{to_open}"' if os.uname().sysname == 'Darwin' else f'xdg-open "{to_open}"')
            self._append_output(f'已開啟資料夾：{to_open}')
            
        except Exception as exc:
            messagebox.showerror('錯誤', f'開啟資料夾失敗：{exc}')

    def on_clear_output(self) -> None:
        """清空輸出內容"""
        self.txt_output.delete(1.0, tk.END)

    def on_search_next(self) -> None:
        """搜尋下一個符合內容，並以 search_hit 標籤高亮。"""
        query = (self.var_search.get() or '').strip()
        if not query:
            return
        try:
            # 從上次位置往下找
            start_idx = self._last_search_index
            pos = self.txt_output.search(query, start_idx, nocase=True, stopindex=tk.END)
            if not pos:
                # 從文件開頭再找一次
                pos = self.txt_output.search(query, '1.0', nocase=True, stopindex=tk.END)
                if not pos:
                    return
            # 計算結束位置
            end = f"{pos}+{len(query)}c"
            # 捲動到可視
            self.txt_output.see(pos)
            # 清掉舊的搜尋標記後再加上新的（避免過多標記堆疊）
            self.txt_output.tag_remove('search_hit', '1.0', tk.END)
            self.txt_output.tag_add('search_hit', pos, end)
            # 下一次從當前命中之後繼續
            self._last_search_index = end
        except Exception:
            pass

    def on_search_clear(self) -> None:
        """清除搜尋標記與狀態。"""
        try:
            self.txt_output.tag_remove('search_hit', '1.0', tk.END)
            self._last_search_index = '1.0'
            if hasattr(self, 'ent_search') and self.ent_search:
                self.ent_search.delete(0, tk.END)
        except Exception:
            pass


    def _on_closing(self) -> None:
        """視窗關閉時的處理"""
        try:
            self._save_settings()
        except Exception:
            pass

        # 非阻塞關閉 SSH：在背景執行，避免 GUI 主執行緒卡住
        def _shutdown():
            try:
                self.ssh.close()
            except Exception:
                pass
            # 最多等待 1 秒，確保背景關閉不拖延主程序銷毀
            try:
                time.sleep(1)
            except Exception:
                pass

        try:
            threading.Thread(target=_shutdown, daemon=True).start()
        except Exception:
            # 若建立背景執行緒失敗，改為同步關閉
            try:
                self.ssh.close()
            except Exception:
                pass

        # 立即銷毀主視窗，讓 mainloop 儘快退出
        try:
            self.root.destroy()
        except Exception:
            pass

    # ---------- 自動偵測 PC IP ----------
    def _auto_fill_pc_ip(self) -> None:
        """若 PC IP 未填，嘗試對 DUT IP 建立暫時 socket 取得來源 IP，並以灰底樣式顯示可覆寫。"""
        try:
            dut_ip = (self.var_dut_ip.get() or '').strip()
            if not dut_ip:
                return
            current_pc = (self.var_pc_ip.get() or '').strip()
            if current_pc:
                return
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.2)
            try:
                s.connect((dut_ip, 22))
                local_ip = s.getsockname()[0]
                if local_ip:
                    self.var_pc_ip.set(local_ip)
                    try:
                        self.ent_pc_ip.configure(style='Hint.TEntry')
                    except Exception:
                        pass
            finally:
                s.close()
        except Exception:
            pass

    def _clear_pc_ip_hint_style(self) -> None:
        try:
            self.ent_pc_ip.configure(style='TEntry')
        except Exception:
            pass

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
            # 檢查是否為多指令模式（用 || 分隔）
            if '||' in command:
                self._execute_multiple_commands(command)
            else:
                self._execute_single_command(command)
                
        except Exception as exc:
            self._append_output(f'[錯誤] 執行失敗：{exc}')
            # 即使出錯也顯示指令完畢標記
            self._append_output('===指令完畢===', 'info')

    def _execute_single_command(self, command: str) -> None:
        """執行單一指令"""
        # 顯示送出的指令
        self._append_output(f'送出指令: {command}', 'info')
        self._append_output(f'$ {command}')
        
        # 確保 SSH 連線正常
        try:
            # 使用左側設定的逾時（秒）
            timeout_sec = int(self.var_timeout.get() or '60')
            code, out, err = self.ssh.exec_command(command, timeout=timeout_sec)
        except Exception as e:
            if 'SSH 連線已斷開' in str(e):
                self._append_output('檢測到 SSH 連線斷開，嘗試重新連線...')
                self._ensure_ssh()
                code, out, err = self.ssh.exec_command(command, timeout=timeout_sec)
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
                    code2, out2, err2 = self.ssh.exec_command(alt_cmd, timeout=timeout_sec)
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

    def _execute_multiple_commands(self, command: str) -> None:
        """執行多指令模式（用 || 分隔）"""
        commands = [cmd.strip() for cmd in command.split('||')]
        self._append_output(f'送出多指令: {len(commands)} 個指令', 'info')
        
        for i, cmd in enumerate(commands, 1):
            if not cmd:
                continue
                
            # 支援 "名稱 = 指令" 格式：若子指令包含等號，僅取等號右側作為實際命令
            display_cmd = cmd
            if '=' in cmd:
                try:
                    _, rhs = cmd.split('=', 1)
                    cmd = rhs.strip()
                except Exception:
                    pass

            self._append_output(f'--- 執行第 {i} 個指令 ---', 'info')
            self._append_output(f'$ {cmd}')
            
            try:
                timeout_sec = int(self.var_timeout.get() or '60')
                code, out, err = self.ssh.exec_command(cmd, timeout=timeout_sec)
                
                if out:
                    self._append_output(out)
                if err and 'Warning:' not in err:
                    self._append_output(err)
                
                self._append_output(f'第 {i} 個指令 Exit code: {code}')
                
                # 如果指令失敗（非 0），繼續執行下一個
                if code != 0:
                    self._append_output(f'第 {i} 個指令失敗，繼續執行下一個...', 'warning')
                
            except Exception as e:
                self._append_output(f'第 {i} 個指令執行錯誤: {e}', 'error')
                # 即使出錯也繼續執行下一個
                continue
        
        # 顯示所有指令完畢標記
        self._append_output('===所有指令完畢===', 'info')

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
                    # 自動開啟 D:\VALO360 根目錄
                    try:
                        import os
                        base = Path(r'D:\\VALO360')
                        if os.name == 'nt' and base.exists():
                            os.startfile(str(base))
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
                    # 顯示所有找到的檔案
                    self._append_output(f'📁 找到 {file_count} 個檔案：')
                    for f in files_found:
                        # 只顯示檔案名稱，不顯示完整路徑
                        filename = f.split('/')[-1]
                        self._append_output(f'  - {filename}')
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

    def _apply_left_font_size(self) -> None:
        """更新左側視窗的字體大小（改用命名字體 LeftFont 全域同步）"""
        try:
            # 同步命名字體 LeftFont 的尺寸
            try:
                lf = tkFont.nametofont('LeftFont')
                lf.configure(size=self.left_font_size)
            except Exception:
                # 若命名字體不存在則重建
                self.left_font = tkFont.Font(name='LeftFont', family=self.primary_font, size=self.left_font_size, weight='normal')
            
            # 更新所有 ttk 樣式
            try:
                style = ttk.Style(self.root)
                style.configure('TLabel', font='LeftFont')
                style.configure('TButton', font='LeftFont')
                style.configure('TEntry', font='LeftFont')
                style.configure('TCombobox', font='LeftFont')
                style.configure('TCheckbutton', font='LeftFont')
                style.configure('TNotebook.Tab', font='LeftFont')
                # 強制更新樣式
                style.update()
            except Exception:
                pass
            
            # 強制更新所有重要元件
            try:
                # 更新標題標籤（固定24號字體，不受左視窗字體控制）
                if hasattr(self, 'title_label'):
                    self.title_label.configure(font=(self.primary_font, 24, 'bold'))
                
                # 強制更新所有下拉選單
                comboboxes = [
                    'cbo_commands', 'cbo_linux', 'cbo_common'
                ]
                for cbo_name in comboboxes:
                    if hasattr(self, cbo_name):
                        cbo = getattr(self, cbo_name)
                        if cbo and cbo.winfo_exists():
                            cbo.configure(font='LeftFont')
                            # 強制重新設定
                            cbo.update()
                
                # 強制更新所有輸入欄位
                entries = [
                    'ent_version', 'ent_manual_input', 'ent_dst', 'ent_search'
                ]
                for ent_name in entries:
                    if hasattr(self, ent_name):
                        ent = getattr(self, ent_name)
                        if ent and ent.winfo_exists():
                            ent.configure(font='LeftFont')
                            # 強制重新設定
                            ent.update()
                
            except Exception as e:
                logging.error(f"更新特定元件字體失敗: {e}")
            
            # 遞迴更新所有左側元件
            def update_widget_font(widget):
                try:
                    # 處理 ttk 元件
                    if isinstance(widget, (ttk.Label, ttk.Button, ttk.Entry, ttk.Combobox, ttk.Checkbutton)):
                        widget.configure(font='LeftFont')
                        widget.update()
                    # 處理 tk 元件
                    elif isinstance(widget, (tk.Label, tk.Button, tk.Entry, tk.Text, tk.Checkbutton)):
                        widget.configure(font='LeftFont')
                        widget.update()
                    # 處理有 font 屬性的元件
                    elif hasattr(widget, 'configure'):
                        try:
                            config_options = widget.configure()
                            if 'font' in config_options:
                                widget.configure(font='LeftFont')
                                widget.update()
                        except Exception:
                            pass
                except Exception:
                    pass
            
            # 遞迴更新所有左側元件
            def walk_widgets(parent):
                try:
                    update_widget_font(parent)
                    for child in parent.winfo_children():
                        walk_widgets(child)
                except Exception:
                    pass
            
            # 更新滾動容器中的所有元件
            if hasattr(self, 'scrollable_frame'):
                walk_widgets(self.scrollable_frame)
                
            # 強制更新整個左側視窗
            if hasattr(self, 'scrollable_frame'):
                self.scrollable_frame.update()
                
        except Exception as e:
            logging.error(f"更新左側字體大小失敗: {e}")

    def _apply_right_font_size(self) -> None:
        """更新右側視窗的字體大小"""
        try:
            # 更新基本文字區域字體
            self.txt_output.configure(font=('Microsoft JhengHei', self.font_size))
            
            # 更新所有標籤的字體大小
            tags = [
                "success", "error", "warning", "info", "file", "path",
                "file_yuv", "file_jpg", "file_bin", "file_log", "file_yml", "file_other",
                "diag_sn", "search_hit"
            ]
            
            for tag in tags:
                try:
                    # 獲取現有標籤的設定
                    current_config = self.txt_output.tag_cget(tag, 'foreground')
                    if current_config:
                        # 重新設定標籤，保持顏色但更新字體大小
                        self.txt_output.tag_configure(tag, foreground=current_config, font=('Microsoft JhengHei', self.font_size, 'bold'))
                except Exception:
                    # 如果標籤不存在或設定失敗，跳過
                    pass
                    
        except Exception as e:
            logging.error(f"更新右側字體大小失敗: {e}")

    def _apply_popup_font_size(self) -> None:
        """更新彈出視窗的字體大小"""
        try:
            # 設定 messagebox 的字體
            default_font = tkFont.nametofont("TkDefaultFont")
            default_font.configure(size=self.popup_font_size)
            
            # 設定 filedialog 的字體
            fixed_font = tkFont.nametofont("TkFixedFont")
            fixed_font.configure(size=self.popup_font_size)
            
            # 設定 text font
            text_font = tkFont.nametofont("TkTextFont")
            text_font.configure(size=self.popup_font_size)
            
            # 設定 caption font
            caption_font = tkFont.nametofont("TkCaptionFont")
            caption_font.configure(size=self.popup_font_size)
            
            # 設定 small caption font
            small_caption_font = tkFont.nametofont("TkSmallCaptionFont")
            small_caption_font.configure(size=self.popup_font_size)
            
            # 設定 icon font
            icon_font = tkFont.nametofont("TkIconFont")
            icon_font.configure(size=self.popup_font_size)
            
            # 設定 menu font
            menu_font = tkFont.nametofont("TkMenuFont")
            menu_font.configure(size=self.popup_font_size)
            
        except Exception as e:
            logging.error(f"更新彈出視窗字體大小失敗: {e}")

    def _safe_set_sash(self, pos: int) -> None:
        """安全設定分隔條位置。"""
        try:
            if hasattr(self, '_paned') and self._paned:
                # 位置界於 100 與 視窗寬度-200 之間，以避免不可視
                total = self.root.winfo_width() or 900
                clamped = max(100, min(total - 200, pos))
                self._paned.sashpos(0, clamped)
        except Exception:
            pass

    def _append_output(self, text: str, tag: str = None) -> None:
        """添加輸出到右側文字區域，支援彩色標籤"""
        # 對 Linux 指令送出與結果之間插入分段空白行，提升可讀性
        normalized = text.rstrip()
        if normalized.startswith('送出指令:'):
            # 若前一行不是空行，則先補一空行
            try:
                prev = self.txt_output.get('end-2l linestart', 'end-1l').strip()
                if prev:
                    self.txt_output.insert(tk.END, '\n')
            except Exception:
                pass
        self.txt_output.insert(tk.END, normalized + '\n')
        
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

    # ---------- 檔案/LOG ----------
    def on_save_log_click(self) -> None:
        """將右側輸出內容寫入 LOG/時間日期分鐘.log"""
        try:
            content = self.txt_output.get('1.0', tk.END).rstrip()
            if not content:
                messagebox.showinfo('提示', '目前沒有可寫入的輸出內容')
                return
            log_dir = Path('LOG')
            _safe_makedirs(log_dir)
            ts = datetime.datetime.now().strftime('%Y%m%d_%H%M')
            file_path = log_dir / f'{ts}.log'
            file_path.write_text(content + '\n', encoding='utf-8')
            self._append_output(f'已寫入 LOG：{file_path}', 'info')
            # 立刻以系統預設程式開啟該檔案
            try:
                import platform, subprocess, os as _os
                if platform.system() == 'Windows':
                    _os.startfile(str(file_path))
                elif platform.system() == 'Darwin':
                    subprocess.run(['open', str(file_path)])
                else:
                    subprocess.run(['xdg-open', str(file_path)])
            except Exception:
                pass
        except Exception as exc:
            messagebox.showerror('錯誤', f'寫入 LOG 失敗：{exc}')


    def _bind_keyboard_shortcuts(self) -> None:
        """綁定鍵盤快捷鍵"""
        try:
            # F1: 開啟說明文件
            self.root.bind('<F1>', lambda e: self.on_show_help())
            
            # F5: 重載指令表
            self.root.bind('<F5>', lambda e: self.on_reload_commands())
            
            # Ctrl+L: 清空右視窗
            self.root.bind('<Control-l>', lambda e: self.on_clear_output())
            
            # Ctrl+S: 存LOG
            self.root.bind('<Control-s>', lambda e: self.on_save_log_click())
            
            # Ctrl+T: 測試SSH連線
            self.root.bind('<Control-t>', lambda e: self.on_test_connection())
            
            # Enter: 在指令輸入框時執行指令
            self.root.bind('<Return>', self._on_enter_key)
            
            # Escape: 關閉彈出視窗
            self.root.bind('<Escape>', lambda e: self._close_popup_windows())
            
        except Exception as e:
            print(f"綁定鍵盤快捷鍵失敗: {e}")

    def _on_enter_key(self, event) -> None:
        """處理 Enter 鍵按下事件"""
        try:
            # 檢查當前焦點在哪個輸入框
            focused = self.root.focus_get()
            
            if focused == self.ent_manual_input:
                # 手動指令輸入框：執行指令
                self.on_execute_manual_command()
            elif focused == self.ent_src_glob:
                # 來源路徑輸入框：檢查檔案
                self.on_check_files()
            elif focused == self.ent_dst:
                # 目標路徑輸入框：開啟資料夾
                self.on_open_destination_folder()
                
        except Exception as e:
            print(f"處理 Enter 鍵事件失敗: {e}")

    def _close_popup_windows(self) -> None:
        """關閉所有彈出視窗"""
        try:
            # 關閉所有 Toplevel 視窗
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    widget.destroy()
        except Exception as e:
            print(f"關閉彈出視窗失敗: {e}")


def main() -> None:
    app = FourCamDebugTool()
    app.run()


if __name__ == '__main__':
    main()


