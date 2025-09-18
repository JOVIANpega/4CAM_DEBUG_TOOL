#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
screenshot_panel.py - 左側底部的截圖預覽區塊

用途：
- 在 GUI 左側底部顯示 assets/screenshots 內的 PNG/JPG 縮圖，整齊排版
- 無截圖時顯示提示訊息

注意事項：
- 優先使用 Pillow 載入圖片（支援 JPG/PNG）；若 Pillow 不可用，僅載入 PNG
- 函式切分，避免過長
"""

from __future__ import annotations

import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk

try:
    from PIL import Image, ImageTk  # type: ignore
    _PIL_OK = True
except Exception:
    _PIL_OK = False


def get_resource_path(relative_path: str) -> str:
    """取得資源路徑，支援 PyInstaller。"""
    try:
        import sys
        base_path = getattr(sys, '_MEIPASS')  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath('.')
    return os.path.join(base_path, relative_path)


def _list_image_files(folder: Path) -> list[Path]:
    try:
        if not folder.exists():
            return []
        exts = {'.png', '.jpg', '.jpeg'}
        files = [p for p in sorted(folder.iterdir()) if p.suffix.lower() in exts and p.is_file()]
        return files[:24]  # 限制最多 24 張，避免太擁擠
    except Exception:
        return []


def _load_thumbnail(path: Path, size: tuple[int, int]) -> tk.PhotoImage | None:
    w, h = size
    try:
        if _PIL_OK:
            img = Image.open(path)
            img.thumbnail((w, h))
            return ImageTk.PhotoImage(img)
        else:
            # Tk 原生僅可靠載入 PNG
            if path.suffix.lower() == '.png':
                return tk.PhotoImage(file=str(path))
            return None
    except Exception:
        return None


def create_screenshot_panel(parent: ttk.Frame, *, font=('Microsoft JhengHei', 11)) -> ttk.LabelFrame:
    """建立截圖預覽區塊，回傳外層 LabelFrame。

    - 自動尋找 assets/screenshots 目錄
    - 以 3 欄網格呈現縮圖
    """
    outer = ttk.LabelFrame(parent, text='截圖預覽', padding=6)
    outer.pack(fill=tk.X, pady=(6, 6))

    try:
        canvas = tk.Canvas(outer, height=120, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor='nw')

        # 載入檔案
        folder = Path(get_resource_path('assets')) / 'screenshots'
        files = _list_image_files(folder)

        thumbnails: list[tk.PhotoImage] = []
        if not files:
            ttk.Label(inner, text='將 PNG/JPG 放到 assets/screenshots 以顯示縮圖', font=font).grid(row=0, column=0, sticky=tk.W)
        else:
            col_count = 3
            thumb_size = (140, 90)
            for i, p in enumerate(files):
                img = _load_thumbnail(p, thumb_size)
                if img is None:
                    continue
                thumbnails.append(img)
                r, c = divmod(len(thumbnails)-1, col_count)
                lbl = ttk.Label(inner, image=img)
                lbl.grid(row=r*2, column=c, padx=4, pady=(2, 0))
                ttk.Label(inner, text=p.stem[:18], font=font).grid(row=r*2+1, column=c, padx=4, pady=(0, 6))

        def _on_configure(_e=None):
            try:
                inner.update_idletasks()
                bbox = inner.bbox() if hasattr(inner, 'bbox') else None
                width = inner.winfo_reqwidth()
                height = inner.winfo_reqheight()
                canvas.configure(scrollregion=(0, 0, width, height))
                canvas.itemconfigure('all', width=canvas.winfo_width())
            except Exception:
                pass

        inner.bind('<Configure>', _on_configure)
        outer._thumb_refs = thumbnails  # 防止被 GC
    except Exception:
        # 安全降級：若建立失敗，顯示簡易提示
        ttk.Label(outer, text='截圖預覽區塊建立失敗', font=font).pack(anchor='w')

    return outer


