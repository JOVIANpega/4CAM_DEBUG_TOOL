#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YUV 檔案檢視器模組

主要用途：
- 檢視 YUV 檔案列表
- 預覽 YUV 檔案（需要 FFmpeg）
- 將 YUV 轉換為 JPG（需要 FFmpeg）
- 自動檢查 FFmpeg 是否可用

作者：AI 助手
版本：1.0.0
檔案角色：YUV 檔案檢視器模組
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import subprocess
import sys
import os
from typing import List, Optional


class YUVViewer:
    """YUV 檔案檢視器類別"""
    
    def __init__(self, parent_window, primary_font, left_font, append_output_callback):
        """
        初始化 YUV 檢視器
        
        Args:
            parent_window: 父視窗
            primary_font: 主要字體
            left_font: 左側字體
            append_output_callback: 輸出回調函數
        """
        self.parent_window = parent_window
        self.primary_font = primary_font
        self.left_font = left_font
        self.append_output = append_output_callback
        self.ffmpeg_path = self._find_ffmpeg()
        
    def _find_ffmpeg(self) -> Optional[str]:
        """尋找 FFmpeg 執行檔"""
        # 檢查當前目錄
        current_dir = Path(__file__).parent
        ffmpeg_paths = [
            current_dir / 'ffmpeg.exe',
            current_dir / 'ffplay.exe',
            Path('ffmpeg.exe'),
            Path('ffplay.exe')
        ]
        
        for path in ffmpeg_paths:
            if path.exists():
                return str(path.parent)
        
        # 檢查系統 PATH
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return 'system'
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
            
        try:
            subprocess.run(['ffplay', '-version'], capture_output=True, check=True)
            return 'system'
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
            
        return None
    
    def _check_ffmpeg_available(self) -> bool:
        """檢查 FFmpeg 是否可用"""
        if self.ffmpeg_path is None:
            self._show_ffmpeg_required_dialog()
            return False
        return True
    
    def _show_ffmpeg_required_dialog(self):
        """顯示 FFmpeg 需求對話框"""
        dialog = tk.Toplevel(self.parent_window)
        dialog.title('需要 FFmpeg')
        dialog.geometry('500x300')
        dialog.resizable(False, False)
        
        # 設定視窗圖示
        try:
            dialog.iconbitmap('assets/icon.ico')
        except Exception:
            pass
        
        # 主框架
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 標題
        title_label = ttk.Label(main_frame, text='⚠️ 需要 FFmpeg 才能檢視 YUV 檔案', 
                               font=(self.primary_font, 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 說明文字
        info_text = """YUV 檔案檢視功能需要 FFmpeg 支援。

請下載 FFmpeg 並將以下檔案放在程式目錄中：
• ffmpeg.exe
• ffplay.exe

下載位置：https://ffmpeg.org/download.html

或者點擊下方按鈕選擇 FFmpeg 安裝目錄。"""
        
        info_label = ttk.Label(main_frame, text=info_text, font=self.left_font, 
                              justify=tk.LEFT, wraplength=450)
        info_label.pack(pady=(0, 20))
        
        # 按鈕框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 選擇 FFmpeg 目錄按鈕
        btn_select = ttk.Button(button_frame, text='選擇 FFmpeg 目錄', 
                               command=lambda: self._select_ffmpeg_directory(dialog))
        btn_select.pack(side=tk.LEFT, padx=(0, 10))
        
        # 下載 FFmpeg 按鈕
        btn_download = ttk.Button(button_frame, text='開啟下載頁面', 
                                 command=self._open_download_page)
        btn_download.pack(side=tk.LEFT, padx=(0, 10))
        
        # 關閉按鈕
        btn_close = ttk.Button(button_frame, text='關閉', command=dialog.destroy)
        btn_close.pack(side=tk.RIGHT)
        
        # 狀態標籤
        self.status_label = ttk.Label(main_frame, text='', font=self.left_font)
        self.status_label.pack(pady=(10, 0))
        
        # 置中顯示
        dialog.transient(self.parent_window)
        dialog.grab_set()
        dialog.focus_set()
        
        # 置中視窗
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
    
    def _select_ffmpeg_directory(self, dialog):
        """選擇 FFmpeg 目錄"""
        directory = filedialog.askdirectory(title='選擇 FFmpeg 安裝目錄')
        if directory:
            ffmpeg_dir = Path(directory)
            ffmpeg_exe = ffmpeg_dir / 'ffmpeg.exe'
            ffplay_exe = ffmpeg_dir / 'ffplay.exe'
            
            if ffmpeg_exe.exists() and ffplay_exe.exists():
                self.ffmpeg_path = str(ffmpeg_dir)
                self.status_label.config(text='✅ FFmpeg 設定成功！')
                dialog.after(2000, dialog.destroy)
            else:
                self.status_label.config(text='❌ 找不到 ffmpeg.exe 或 ffplay.exe')
    
    def _open_download_page(self):
        """開啟 FFmpeg 下載頁面"""
        import webbrowser
        webbrowser.open('https://ffmpeg.org/download.html')
    
    def open_viewer(self, yuv_files: List[Path], base_dir: Path):
        """開啟 YUV 檢視器視窗"""
        if not yuv_files:
            messagebox.showinfo('資訊', '沒有找到 YUV 檔案')
            return
        
        # 創建 YUV 檢視器視窗
        yuv_window = tk.Toplevel(self.parent_window)
        yuv_window.title('YUV 檔案檢視器')
        yuv_window.geometry('900x700')
        yuv_window.resizable(True, True)
        
        # 設定視窗圖示
        try:
            yuv_window.iconbitmap('assets/icon.ico')
        except Exception:
            pass
        
        # 創建主框架
        main_frame = ttk.Frame(yuv_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # 標題
        title_label = ttk.Label(main_frame, text='YUV 檔案檢視器', 
                               font=(self.primary_font, 16, 'bold'))
        title_label.pack(pady=(0, 15))
        
        # 檔案列表框架
        list_frame = ttk.LabelFrame(main_frame, text='YUV 檔案列表', padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # 檔案列表
        file_listbox = tk.Listbox(list_frame, font=self.left_font, height=12)
        file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 滾動條
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        file_listbox.configure(yscrollcommand=scrollbar.set)
        
        # 添加檔案到列表
        for i, yuv_file in enumerate(yuv_files):
            relative_path = yuv_file.relative_to(base_dir)
            file_size = yuv_file.stat().st_size
            size_mb = file_size / (1024 * 1024)
            display_text = f"{relative_path} ({size_mb:.1f} MB)"
            file_listbox.insert(tk.END, display_text)
        
        # 控制框架
        control_frame = ttk.LabelFrame(main_frame, text='控制選項', padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 第一行：解析度與像素格式選擇
        row1_frame = ttk.Frame(control_frame)
        row1_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(row1_frame, text='解析度：', font=self.left_font).pack(side=tk.LEFT)
        resolution_var = tk.StringVar(value='1920x1080')
        resolution_combo = ttk.Combobox(row1_frame, textvariable=resolution_var, 
                                       values=['3840x2160', '2560x1440', '1920x1080', '1600x900', '1280x720', '1024x768', '800x600', '640x480', '320x240'], 
                                       state='readonly', width=12, font=self.left_font)
        resolution_combo.pack(side=tk.LEFT, padx=(5, 12))

        ttk.Label(row1_frame, text='像素格式：', font=self.left_font).pack(side=tk.LEFT)
        pixel_format_var = tk.StringVar(value='yuv420p')
        pixel_format_combo = ttk.Combobox(row1_frame, textvariable=pixel_format_var,
                                         values=['yuv420p', 'nv12', 'yuv422p', 'yuyv422'],
                                         state='readonly', width=10, font=self.left_font)
        pixel_format_combo.pack(side=tk.LEFT, padx=(5, 12))

        auto_try_var = tk.BooleanVar(value=True)
        chk_auto_try = ttk.Checkbutton(row1_frame, text='自動嘗試常見解析度', variable=auto_try_var)
        chk_auto_try.pack(side=tk.LEFT)
        
        # 第二行：按鈕
        row2_frame = ttk.Frame(control_frame)
        row2_frame.pack(fill=tk.X)
        
        # 預覽按鈕
        btn_preview = ttk.Button(row2_frame, text='預覽 YUV', 
                                command=lambda: self._preview_yuv_file(yuv_files, file_listbox, resolution_var, pixel_format_var, auto_try_var))
        btn_preview.pack(side=tk.LEFT, padx=(0, 10))
        
        # 轉換按鈕
        btn_convert = ttk.Button(row2_frame, text='轉換為 JPG', 
                                command=lambda: self._convert_yuv_to_jpg(yuv_files, file_listbox, resolution_var, pixel_format_var, auto_try_var, base_dir))
        btn_convert.pack(side=tk.LEFT, padx=(0, 10))
        
        # 批次轉換按鈕
        btn_batch = ttk.Button(row2_frame, text='批次轉換', 
                              command=lambda: self._batch_convert_yuv(yuv_files, resolution_var, base_dir))
        btn_batch.pack(side=tk.LEFT, padx=(0, 10))
        
        # 開啟資料夾按鈕
        btn_open_folder = ttk.Button(row2_frame, text='開啟資料夾', 
                                    command=lambda: self._open_folder(base_dir))
        btn_open_folder.pack(side=tk.LEFT, padx=(0, 10))
        
        # 關閉按鈕
        btn_close = ttk.Button(row2_frame, text='關閉', command=yuv_window.destroy)
        btn_close.pack(side=tk.RIGHT)
        
        # 狀態框架
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X)
        
        # 狀態標籤
        status_text = f'找到 {len(yuv_files)} 個 YUV 檔案'
        if self.ffmpeg_path:
            status_text += ' | FFmpeg: 可用'
        else:
            status_text += ' | FFmpeg: 不可用（預覽和轉換功能受限）'
            
        status_label = ttk.Label(status_frame, text=status_text, font=self.left_font)
        status_label.pack(anchor=tk.W)
        
        # 置中顯示
        yuv_window.transient(self.parent_window)
        yuv_window.grab_set()
        yuv_window.focus_set()
        
        # 置中視窗
        yuv_window.update_idletasks()
        x = (yuv_window.winfo_screenwidth() // 2) - (yuv_window.winfo_width() // 2)
        y = (yuv_window.winfo_screenheight() // 2) - (yuv_window.winfo_height() // 2)
        yuv_window.geometry(f"+{x}+{y}")
    
    def _preview_yuv_file(self, yuv_files: List[Path], file_listbox: tk.Listbox, resolution_var: tk.StringVar, pixel_format_var: tk.StringVar, auto_try_var: tk.BooleanVar):
        """預覽選中的 YUV 檔案"""
        if not self._check_ffmpeg_available():
            return
            
        try:
            selection = file_listbox.curselection()
            if not selection:
                messagebox.showwarning('提醒', '請選擇要預覽的 YUV 檔案')
                return
                
            selected_file = yuv_files[selection[0]]
            resolution = resolution_var.get()
            width, height = resolution.split('x')
            pix_fmt = pixel_format_var.get()
            
            # 構建 FFplay 指令
            if self.ffmpeg_path == 'system':
                cmd = ['ffplay']
            else:
                cmd = [str(Path(self.ffmpeg_path) / 'ffplay.exe')]
            
            cmd.extend([
                '-f', 'rawvideo', 
                '-pixel_format', pix_fmt,
                '-video_size', f'{width}x{height}',
                '-i', str(selected_file),
                '-window_title', f'YUV 預覽 - {selected_file.name}'
            ])
            
            # 執行預覽
            subprocess.Popen(cmd)
            self.append_output(f'🎬 開始預覽 YUV 檔案：{selected_file.name}')
            
        except Exception as e:
            messagebox.showerror('錯誤', f'預覽失敗：{e}')
            self.append_output(f'❌ YUV 預覽失敗：{e}', 'error')
    
    def _convert_yuv_to_jpg(self, yuv_files: List[Path], file_listbox: tk.Listbox, 
                           resolution_var: tk.StringVar, pixel_format_var: tk.StringVar, auto_try_var: tk.BooleanVar, base_dir: Path):
        """將選中的 YUV 檔案轉換為 JPG"""
        if not self._check_ffmpeg_available():
            return
            
        try:
            selection = file_listbox.curselection()
            if not selection:
                messagebox.showwarning('提醒', '請選擇要轉換的 YUV 檔案')
                return
                
            selected_file = yuv_files[selection[0]]
            resolution = resolution_var.get()
            width, height = resolution.split('x')
            pix_fmt = pixel_format_var.get()
            
            # 創建輸出檔案路徑
            output_file = selected_file.with_suffix('.jpg')
            
            # 構建 FFmpeg 指令
            if self.ffmpeg_path == 'system':
                cmd = ['ffmpeg']
            else:
                cmd = [str(Path(self.ffmpeg_path) / 'ffmpeg.exe')]
            
            cmd.extend([
                '-f', 'rawvideo',
                '-pixel_format', pix_fmt,
                '-video_size', f'{width}x{height}',
                '-i', str(selected_file),
                '-y',  # 覆蓋輸出檔案
                str(output_file)
            ])
            
            # 執行轉換
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            messagebox.showinfo('成功', f'轉換完成：{output_file.name}')
            self.append_output(f'✅ YUV 轉換成功：{output_file.name}')
            
        except subprocess.CalledProcessError as e:
            # 若啟用自動嘗試，依序嘗試常見解析度與像素格式
            if auto_try_var.get():
                try_resolutions = ['1920x1080', '1280x720', '640x480']
                try_pixfmts = ['yuv420p', 'nv12', 'yuv422p']
                tried = []
                for res in try_resolutions:
                    w, h = res.split('x')
                    for pf in try_pixfmts:
                        tried.append(f"{res}/{pf}")
                        try_cmd = cmd[:1] + ['-f', 'rawvideo', '-pixel_format', pf, '-video_size', f'{w}x{h}', '-i', str(selected_file), '-y', str(output_file)]
                        try:
                            subprocess.run(try_cmd, capture_output=True, text=True, check=True)
                            messagebox.showinfo('成功', f'轉換完成（自動嘗試 {res}/{pf}）：{output_file.name}')
                            self.append_output(f'✅ 自動嘗試成功：{selected_file.name} -> {output_file.name} 使用 {res}/{pf}')
                            return
                        except subprocess.CalledProcessError:
                            continue
                messagebox.showerror('錯誤', f'轉換失敗，已嘗試：{", ".join(tried)}\n原始錯誤：{e.stderr}')
                self.append_output(f'❌ YUV 轉換失敗（已自動嘗試多組參數）：{e.stderr}', 'error')
            else:
                messagebox.showerror('錯誤', f'轉換失敗：{e.stderr}')
                self.append_output(f'❌ YUV 轉換失敗：{e.stderr}', 'error')
        except Exception as e:
            messagebox.showerror('錯誤', f'轉換失敗：{e}')
            self.append_output(f'❌ YUV 轉換失敗：{e}', 'error')
    
    def _batch_convert_yuv(self, yuv_files: List[Path], resolution_var: tk.StringVar, base_dir: Path):
        """批次轉換所有 YUV 檔案"""
        if not self._check_ffmpeg_available():
            return
            
        if not yuv_files:
            messagebox.showwarning('提醒', '沒有 YUV 檔案可轉換')
            return
        
        # 確認對話框
        result = messagebox.askyesno('確認', f'確定要批次轉換 {len(yuv_files)} 個 YUV 檔案嗎？\n\n這可能需要一些時間。')
        if not result:
            return
        
        try:
            resolution = resolution_var.get()
            width, height = resolution.split('x')
            success_count = 0
            
            # 構建 FFmpeg 指令
            if self.ffmpeg_path == 'system':
                ffmpeg_cmd = 'ffmpeg'
            else:
                ffmpeg_cmd = str(Path(self.ffmpeg_path) / 'ffmpeg.exe')
            
            for i, yuv_file in enumerate(yuv_files):
                try:
                    output_file = yuv_file.with_suffix('.jpg')
                    
                    cmd = [
                        ffmpeg_cmd,
                        '-f', 'rawvideo',
                        '-pixel_format', 'yuv420p',
                        '-video_size', f'{width}x{height}',
                        '-i', str(yuv_file),
                        '-y',  # 覆蓋輸出檔案
                        str(output_file)
                    ]
                    
                    subprocess.run(cmd, capture_output=True, text=True, check=True)
                    success_count += 1
                    self.append_output(f'✅ 轉換完成 ({i+1}/{len(yuv_files)}): {yuv_file.name}')
                    
                except subprocess.CalledProcessError as e:
                    self.append_output(f'❌ 轉換失敗 ({i+1}/{len(yuv_files)}): {yuv_file.name} - {e.stderr}', 'error')
                except Exception as e:
                    self.append_output(f'❌ 轉換失敗 ({i+1}/{len(yuv_files)}): {yuv_file.name} - {e}', 'error')
            
            # 顯示結果
            messagebox.showinfo('批次轉換完成', f'成功轉換 {success_count}/{len(yuv_files)} 個檔案')
            self.append_output(f'🎉 批次轉換完成：{success_count}/{len(yuv_files)} 個檔案')
            
        except Exception as e:
            messagebox.showerror('錯誤', f'批次轉換失敗：{e}')
            self.append_output(f'❌ 批次轉換失敗：{e}', 'error')
    
    def _open_folder(self, folder_path: Path):
        """開啟資料夾"""
        try:
            os.startfile(str(folder_path))
            self.append_output(f'📁 已開啟資料夾：{folder_path}')
        except Exception as e:
            messagebox.showerror('錯誤', f'無法開啟資料夾：{e}')
            self.append_output(f'❌ 無法開啟資料夾：{e}', 'error')


def create_yuv_viewer(parent_window, primary_font, left_font, append_output_callback):
    """創建 YUV 檢視器實例"""
    return YUVViewer(parent_window, primary_font, left_font, append_output_callback)
