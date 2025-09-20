#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk

# 測試最基本的 PanedWindow
root = tk.Tk()
root.title('測試 PanedWindow')
root.geometry('800x600')

# 創建 PanedWindow
paned = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
paned.pack(fill=tk.BOTH, expand=True)

# 左邊框架
left = ttk.Frame(paned)
ttk.Label(left, text='左邊').pack()

# 右邊框架  
right = ttk.Frame(paned)
ttk.Label(right, text='右邊').pack()

# 添加到 PanedWindow
paned.add(left, weight=1)
paned.add(right, weight=2)

print("PanedWindow 已創建")
root.mainloop()
