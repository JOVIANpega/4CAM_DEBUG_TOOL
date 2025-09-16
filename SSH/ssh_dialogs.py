��# -*- coding: utf-8 -*-
"""
SSH -��[\q�Fh!jD}
"""
import tkinter as tk
from tkinter import ttk, messagebox
import re


class SSHAccountDialog:
    """SSH 3^_�8�eQ\q�Fh"""
    
    def __init__(self, parent):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("�e�X SSH 3^_�")
        self.dialog.geometry("300x150")
        self.dialog.resizable(False, False)
        
        # O(u�T1z
        ttk.Label(self.dialog, text="O(u�T1z:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.username_entry = ttk.Entry(self.dialog, width=20)
        self.username_entry.grid(row=0, column=1, padx=10, pady=5)
        
        # �[�x
        ttk.Label(self.dialog, text="�[�x:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.password_entry = ttk.Entry(self.dialog, width=20, show="*")
        self.password_entry.grid(row=1, column=1, padx=10, pady=5)
        
        # 	c�
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="�x�[", command=self.ok_clicked).pack(side="left", padx=5)
        ttk.Button(button_frame, text="�S�m", command=self.cancel_clicked).pack(side="left", padx=5)
        
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
    def ok_clicked(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if username:
            self.result = (username, password)
            self.dialog.destroy()
        else:
            messagebox.showerror("/���", "ˊ8�eQO(u�T1z")
    
    def cancel_clicked(self):
        self.dialog.destroy()


class SSHIPDialog:
    """SSH IP 0W@W8�eQ\q�Fh"""
    
    def __init__(self, parent):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("�e�X SSH IP 0W@W")
        self.dialog.geometry("300x120")
        self.dialog.resizable(False, False)
        
        # IP 0W@W
        ttk.Label(self.dialog, text="IP 0W@W:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.ip_entry = ttk.Entry(self.dialog, width=20)
        self.ip_entry.grid(row=0, column=1, padx=10, pady=5)
        self.ip_entry.focus()
        
        # �c:yjd|
        ttk.Label(self.dialog, text="�O�Y: 192.168.11.143", 
                 font=("Microsoft JhengHei UI", 9), foreground="#666666").grid(row=1, column=0, columnspan=2, pady=5)
        
        # 	c�
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="�x�[", command=self.ok_clicked).pack(side="left", padx=5)
        ttk.Button(button_frame, text="�S�m", command=self.cancel_clicked).pack(side="left", padx=5)
        
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # �}�[ Enter u�
        self.dialog.bind("<Return>", lambda e: self.ok_clicked())
        
    def ok_clicked(self):
        ip = self.ip_entry.get().strip()
        
        if ip:
            # !|�UW�I�
            ip_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
            if re.match(ip_pattern, ip):
                # �j�g�{W
                parts = ip.split(".")
                valid = True
                for part in parts:
                    if int(part) > 255:
                        valid = False
                        break
                
                if valid:
                    self.result = ip
                    self.dialog.destroy()
                else:
                    messagebox.showerror("/���", "IP 0W@W�{W!qHe�0-255	�")
            else:
                messagebox.showerror("/���", "IP 0W@W<h_!qHe")
        else:
            messagebox.showerror("/���", "ˊ8�eQ IP 0W@W")
    
    def cancel_clicked(self):
        self.dialog.destroy()
