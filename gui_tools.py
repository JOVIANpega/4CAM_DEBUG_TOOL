#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gui_tools.py - 4CAM DEBUG TOOL GUI 工具模組

主要功能：
- Tooltip 工具提示類別
- GUI 樣式管理
- 字體管理與檢測
- Windows 11 風格主題
- 鍵盤快捷鍵管理

作者：AI 助手
版本：1.0.0
"""

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont
from typing import Optional, Dict, Any
import threading
import time


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

    def on_enter(self, event=None):
        """滑鼠進入時顯示 tooltip"""
        # 檢查文字長度是否達到最小要求
        if len(self.text) < self.min_length:
            return
            
        self.show_tooltip()

    def on_leave(self, event=None):
        """滑鼠離開時隱藏 tooltip"""
        self.hide_tooltip()

    def show_tooltip(self):
        """顯示 tooltip"""
        if self.tooltip_window:
            return

        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f'+{x}+{y}')

        # 動態取得字體大小
        if self.font_size is None:
            try:
                # 嘗試從主視窗取得彈出字體大小
                root = self.widget.winfo_toplevel()
                if hasattr(root, 'popup_font_size'):
                    actual_font_size = root.popup_font_size
                else:
                    actual_font_size = 12
            except:
                actual_font_size = 12
        else:
            actual_font_size = self.font_size

        self.tooltip_label = tk.Label(
            self.tooltip_window,
            text=self.text,
            justify='left',
            background='#ffffe0',
            foreground='black',
            relief='solid',
            borderwidth=1,
            font=('Microsoft JhengHei UI', actual_font_size, 'normal'),
            wraplength=400
        )
        self.tooltip_label.pack()

        # 設定自動隱藏計時器（5秒後自動隱藏）
        self.auto_hide_timer = threading.Timer(5.0, self.hide_tooltip)
        self.auto_hide_timer.start()

    def hide_tooltip(self):
        """隱藏 tooltip"""
        # 取消自動隱藏計時器
        if self.auto_hide_timer:
            self.auto_hide_timer.cancel()
            self.auto_hide_timer = None

        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
            self.tooltip_label = None

    def update_text(self, new_text: str):
        """更新 tooltip 文字"""
        self.text = new_text
        if self.tooltip_label:
            self.tooltip_label.config(text=new_text)


class FontManager:
    """字體管理器 - 處理字體檢測與管理"""
    
    def __init__(self):
        self.available_fonts = self._detect_available_fonts()
        self.primary_font = self._get_best_font()
    
    def _detect_available_fonts(self) -> list:
        """檢測系統可用字體"""
        font_candidates = [
            "Microsoft JhengHei Light",
            "Microsoft JhengHei UI Light", 
            "Microsoft JhengHei",
            "Microsoft YaHei Light",
            "Microsoft YaHei",
            "Segoe UI",
            "TkDefaultFont"
        ]
        
        available = []
        print("開始檢測可用字體...")
        
        for font_name in font_candidates:
            try:
                test_font = tkFont.Font(family=font_name, size=10)
                actual_font = test_font.actual()
                print(f"測試字體: {font_name} -> 實際載入: {actual_font['family']}")
                
                # 檢查是否真的載入了指定的字體
                if (actual_font['family'].lower() == font_name.lower() or 
                    'jhenghei' in actual_font['family'].lower()):
                    print(f"✅ 使用字體: {font_name}")
                    available.append(font_name)
                    
            except Exception as e:
                print(f"❌ 字體 {font_name} 載入失敗: {e}")
                continue
        
        if not available:
            print("⚠️ 未找到理想字體，使用系統預設")
            available.append("TkDefaultFont")
            
        return available
    
    def _get_best_font(self) -> str:
        """取得最佳字體"""
        if self.available_fonts:
            return self.available_fonts[0]
        return "TkDefaultFont"
    
    def get_font_tuple(self, size: int = 12, weight: str = 'normal') -> tuple:
        """取得字體元組"""
        return (self.primary_font, size, weight)


class StyleManager:
    """樣式管理器 - 處理 Windows 11 風格主題"""
    
    def __init__(self, root: tk.Tk, font_manager: FontManager):
        self.root = root
        self.font_manager = font_manager
        self.style = ttk.Style(root)
        
        # Windows 11 色彩配置
        self.colors = {
            'bg': '#f5f5f5',           # 主背景色
            'fg': '#323130',           # 主文字色
            'frame_bg': '#f5f5f5',     # 框架背景色
            'button_bg': '#f0f0f0',    # 按鈕背景色
            'button_active': '#e0e0e0', # 按鈕啟用色
            'entry_bg': '#ffffff',     # 輸入框背景色
            'entry_focus': '#0078d4',  # 輸入框焦點色
            'tab_bg': '#f0f0f0',       # 標籤背景色
            'tab_selected_bg': '#ffffff', # 選中標籤背景色
            'success': '#107c10',      # 成功色
            'error': '#d13438',        # 錯誤色
            'warning': '#ff8c00',      # 警告色
        }
        
        self._setup_styles()
    
    def _setup_styles(self):
        """設定 Windows 11 風格樣式"""
        try:
            self.style.theme_use('clam')
            
            # 設定根視窗背景
            self.root.configure(bg=self.colors['bg'])
            
            # 通用按鈕樣式
            self.style.configure('TButton', 
                              background=self.colors['button_bg'],
                              foreground=self.colors['fg'],
                              borderwidth=1,
                              focuscolor='none',
                              padding=(10, 8),
                              font=self.font_manager.get_font_tuple(10),
                              relief='flat')
            
            self.style.map('TButton',
                          background=[('active', self.colors['button_active']),
                                    ('pressed', self.colors['button_active'])])
            
            # 輸入框樣式
            self.style.configure('TEntry',
                              fieldbackground=self.colors['entry_bg'],
                              foreground=self.colors['fg'],
                              borderwidth=1,
                              insertcolor=self.colors['fg'],
                              font=self.font_manager.get_font_tuple(10))
            
            self.style.map('TEntry',
                          focuscolor=[('focus', self.colors['entry_focus'])])
            
            # 標籤頁樣式
            self.style.configure('TNotebook',
                              background=self.colors['bg'],
                              borderwidth=0)
            
            self.style.configure('TNotebook.Tab',
                              background=self.colors['tab_bg'],
                              foreground=self.colors['fg'],
                              padding=(12, 8),
                              font=self.font_manager.get_font_tuple(10),
                              borderwidth=1)
            
            self.style.map('TNotebook.Tab',
                          background=[('selected', self.colors['tab_selected_bg']),
                                    ('active', self.colors['button_active'])],
                          foreground=[('selected', self.colors['fg']),
                                    ('active', self.colors['fg'])])
            
            # 核取方塊樣式
            self.style.configure('TCheckbutton',
                              background=self.colors['frame_bg'],
                              foreground=self.colors['fg'],
                              font=self.font_manager.get_font_tuple(10))
            
            # 框架樣式
            self.style.configure('TLabelframe',
                              background=self.colors['frame_bg'],
                              borderwidth=1,
                              relief='solid')
            
            self.style.configure('TLabelframe.Label',
                              background=self.colors['frame_bg'],
                              foreground=self.colors['fg'],
                              font=self.font_manager.get_font_tuple(10, 'bold'))
            
            self.style.configure('TFrame',
                              background=self.colors['frame_bg'])
            
            # 特殊樣式
            self._setup_special_styles()
            
        except Exception as e:
            print(f"樣式設定失敗: {e}")
    
    def _setup_special_styles(self):
        """設定特殊樣式（彩色按鈕等）"""
        # 彩色控制按鈕樣式
        button_colors = {
            'Green.TButton': '#107c10',
            'Blue.TButton': '#0078d4', 
            'Orange.TButton': '#ff8c00',
            'Purple.TButton': '#5c2d91',
            'Red.TButton': '#d13438'
        }
        
        for style_name, color in button_colors.items():
            self.style.configure(style_name,
                              background=color,
                              foreground='white',
                              borderwidth=0,
                              focuscolor='none',
                              padding=(12, 10),
                              font=self.font_manager.get_font_tuple(10, 'bold'),
                              relief='flat')
            
            # 深色版本用於 hover 效果
            darker_color = self._darken_color(color)
            self.style.map(style_name,
                          background=[('active', darker_color),
                                    ('pressed', darker_color)])
        
        # 高亮輸入框樣式（用於 timeout 欄位）
        self.style.configure('Highlight.TEntry',
                          fieldbackground='#fffacd',  # 淡黃色背景
                          foreground=self.colors['fg'],
                          borderwidth=2,
                          relief='solid',
                          font=self.font_manager.get_font_tuple(10))
    
    def _darken_color(self, hex_color: str, factor: float = 0.8) -> str:
        """將顏色變暗"""
        try:
            # 移除 # 符號
            hex_color = hex_color.lstrip('#')
            
            # 轉換為 RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # 變暗
            r = int(r * factor)
            g = int(g * factor)
            b = int(b * factor)
            
            # 轉回十六進位
            return f'#{r:02x}{g:02x}{b:02x}'
        except:
            return hex_color  # 如果轉換失敗，返回原色
    
    def update_font_sizes(self, button_size: int = 10, entry_size: int = 10):
        """更新字體大小"""
        # 更新按鈕字體
        self.style.configure('TButton', 
                          font=self.font_manager.get_font_tuple(button_size))
        
        # 更新輸入框字體
        self.style.configure('TEntry',
                          font=self.font_manager.get_font_tuple(entry_size))
        
        # 更新其他元件字體
        self.style.configure('TNotebook.Tab',
                          font=self.font_manager.get_font_tuple(button_size))
        
        self.style.configure('TCheckbutton',
                          font=self.font_manager.get_font_tuple(entry_size))


class KeyboardManager:
    """鍵盤快捷鍵管理器"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.shortcuts = {}
    
    def bind_shortcuts(self, shortcuts: Dict[str, callable]):
        """綁定快捷鍵"""
        self.shortcuts.update(shortcuts)
        
        for key, callback in shortcuts.items():
            self.root.bind(key, lambda event, cb=callback: cb())
    
    def add_shortcut(self, key: str, callback: callable):
        """新增單一快捷鍵"""
        self.shortcuts[key] = callback
        self.root.bind(key, lambda event: callback())
    
    def remove_shortcut(self, key: str):
        """移除快捷鍵"""
        if key in self.shortcuts:
            del self.shortcuts[key]
            self.root.unbind(key)


def setup_gui_tools(root: tk.Tk) -> tuple:
    """設定 GUI 工具，返回 (font_manager, style_manager, keyboard_manager)"""
    font_manager = FontManager()
    style_manager = StyleManager(root, font_manager)
    keyboard_manager = KeyboardManager(root)
    
    return font_manager, style_manager, keyboard_manager


if __name__ == "__main__":
    # 測試 GUI 工具
    root = tk.Tk()
    root.title("GUI 工具測試")
    root.geometry("400x300")
    
    font_manager, style_manager, keyboard_manager = setup_gui_tools(root)
    
    # 測試按鈕
    btn = ttk.Button(root, text="測試按鈕")
    btn.pack(pady=10)
    
    # 測試 Tooltip
    Tooltip(btn, "這是一個測試按鈕的提示訊息")
    
    # 測試快捷鍵
    keyboard_manager.add_shortcut('<F1>', lambda: print("F1 被按下"))
    
    root.mainloop()
