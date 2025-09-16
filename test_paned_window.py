#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_paned_window.py - 測試 PanedWindow 是否正常工作

主要用途：
- 測試 ttk.PanedWindow 是否能正常顯示左右分割視窗
- 確認問題是否出在 PanedWindow 本身

作者：AI 助手
版本：1.0.0
"""

import tkinter as tk
from tkinter import ttk

def test_paned_window():
    root = tk.Tk()
    root.title('PanedWindow 測試')
    root.geometry('800x600')
    
    # 創建 PanedWindow
    paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
    paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # 創建左右框架
    left_frame = ttk.Frame(paned_window, padding=10)
    right_frame = ttk.Frame(paned_window, padding=10)
    
    # 添加到 PanedWindow
    paned_window.add(left_frame, weight=1)
    paned_window.add(right_frame, weight=2)
    
    # 左邊內容
    ttk.Label(left_frame, text='左邊視窗', font=('Microsoft JhengHei', 14, 'bold')).pack()
    ttk.Button(left_frame, text='測試按鈕').pack(pady=10)
    
    # 右邊內容
    ttk.Label(right_frame, text='右邊視窗', font=('Microsoft JhengHei', 14, 'bold')).pack()
    text_widget = tk.Text(right_frame, height=20, width=50)
    text_widget.pack(fill=tk.BOTH, expand=True)
    text_widget.insert('1.0', '這是右邊的文字區域\n可以測試拖拉分割線')
    
    root.mainloop()

if __name__ == "__main__":
    test_paned_window()
