#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修改腳本 - 直接執行這個來修改 main.py
實現頂部工具列布局：標題 + 通用按鍵 + 工具列
"""

import re

def modify_main_py():
    """修改 main.py 實現新的布局"""
    print("開始修改 main.py...")
    
    # 讀取檔案
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 修改標題區域 (第479-502行)
    old_title = '''        # 標題 + 版本 + 字體 + 清空按鍵
        top = ttk.Frame(scrollable_frame)
        top.pack(fill=tk.X)
        
        self.title_label = ttk.Label(top, text='4CAM DEBUG TOOL', font=('Microsoft JhengHei', 22, 'bold'))
        self.title_label.pack(side=tk.LEFT)
        self.title_label.configure(background='lightgreen')

        # 版本顯示與可編輯欄位
        ttk.Label(top, text='版本', font=self.left_font).pack(side=tk.LEFT, padx=(10, 4))
        self.ent_version = ttk.Entry(top, textvariable=self.var_app_version, width=10, font=self.left_font)
        self.ent_version.pack(side=tk.LEFT)
        Tooltip(self.ent_version, text='顯示於視窗標題與左上角的版本字串')
        # 當版本變更時，同步視窗標題
        def _on_version_change(*_a):
            try:
                self.root.title(f'4CAM_DEBUG_TOOL {self.var_app_version.get()}')
            except Exception:
                pass
        self.var_app_version.trace_add('write', _on_version_change)
        
        btn_clear = ttk.Button(top, text='清空', command=self.on_clear_output, width=6)
        btn_clear.pack(side=tk.RIGHT, padx=(6, 0))
        Tooltip(btn_clear, text='清空右側輸出內容')'''

    new_title = '''        # 標題區域（移除版本設定）
        title_frame = ttk.Frame(scrollable_frame)
        title_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.title_label = ttk.Label(title_frame, text='4CAM DEBUG TOOL', font=('Microsoft JhengHei', 22, 'bold'))
        self.title_label.pack(side=tk.LEFT)
        self.title_label.configure(background='lightgreen')

        # 右側：通用按鍵
        btn_frame = ttk.Frame(title_frame)
        btn_frame.pack(side=tk.RIGHT)

        btn_help = ttk.Button(btn_frame, text='說明', command=self.on_show_help, style='Green.TButton', width=6)
        btn_help.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(btn_help, text='開啟使用說明文件')

        btn_clear = ttk.Button(btn_frame, text='清空', command=self.on_clear_output, width=6)
        btn_clear.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(btn_clear, text='清空右側輸出內容')

        btn_log = ttk.Button(btn_frame, text='存取LOG', command=self.on_save_log_click, width=8)
        btn_log.pack(side=tk.LEFT)
        Tooltip(btn_log, text='將右側輸出全部寫入 LOG/時間日期分鐘.log')

        # 工具列
        toolbar_frame = ttk.Frame(scrollable_frame)
        toolbar_frame.pack(fill=tk.X, pady=(0, 5))

        # 左側：清空輸出勾選
        ck_clear = ttk.Checkbutton(toolbar_frame, text='每次下指令清除舊訊息', variable=self.var_clear_output, font=self.left_font)
        ck_clear.pack(side=tk.LEFT)
        Tooltip(ck_clear, text='勾選後每次執行指令前會自動清空右側輸出內容')'''

    # 2. 移除全域控制
    old_global = '''        # 全域控制（放置於左側主區塊，連線設定下）
        global_ctrl = ttk.Frame(scrollable_frame)
        global_ctrl.pack(fill=tk.X, pady=(4, 4))
        chk_clear = ttk.Checkbutton(global_ctrl, text='清除舊訊息', variable=self.var_clear_output)
        chk_clear.pack(side=tk.LEFT)
        btn_help_global = ttk.Button(global_ctrl, text='說明', command=self.on_show_help, style='Green.TButton', width=6)
        btn_help_global.pack(side=tk.RIGHT)
        Tooltip(btn_help_global, text='開啟使用說明文件')'''

    new_global = '''        # 全域控制已移到頂部工具列'''

    # 3. 移除底部LOG按鍵
    old_bottom = '''        # 左側底部：存取 LOG 按鈕
        bottom_frame = ttk.Frame(scrollable_frame)
        bottom_frame.pack(fill=tk.X, pady=(4, 0))
        btn_save_log = ttk.Button(bottom_frame, text='存取 LOG 資料', command=self.on_save_log_click)
        btn_save_log.pack(side=tk.LEFT)
        Tooltip(btn_save_log, text='將右側輸出全部寫入 LOG/時間日期分鐘.log')'''

    new_bottom = '''        # 存取LOG按鍵已移到頂部工具列'''

    # 4. 修改設定TAB
    old_settings = '''        # 設定分頁內容
        lf_settings = ttk.LabelFrame(tab_settings, text='字體設定', padding=8)
        lf_settings.pack(fill=tk.X, pady=(6, 6))
        
        # 左視窗字體設定
        left_font_frame = ttk.Frame(lf_settings)
        left_font_frame.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))'''

    new_settings = '''        # 設定分頁內容
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
        left_font_frame.grid(row=2, column=0, sticky=tk.W, pady=(0, 10))'''

    # 執行替換
    content = content.replace(old_title, new_title)
    content = content.replace(old_global, new_global)
    content = content.replace(old_bottom, new_bottom)
    content = content.replace(old_settings, new_settings)

    # 更新字體設定的row編號
    content = re.sub(r'right_font_frame\.grid\(row=1,', 'right_font_frame.grid(row=3,', content)
    content = re.sub(r'popup_font_frame\.grid\(row=2,', 'popup_font_frame.grid(row=4,', content)
    content = re.sub(r'reset_frame\.grid\(row=3,', 'reset_frame.grid(row=5,', content)

    # 保存檔案
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ main.py 修改完成！")
    print("實現的功能：")
    print("  - 頂部工具列：標題 + 三個通用按鍵（說明、清空、存取LOG）")
    print("  - 工具列：清空輸出勾選框")
    print("  - 設定TAB：版本設定 + 字體設定")
    print("  - 簡潔布局：所有通用功能集中管理")

if __name__ == "__main__":
    modify_main_py()
