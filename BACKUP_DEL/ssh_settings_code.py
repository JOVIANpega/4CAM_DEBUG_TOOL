��# SSH -��[@SJXz_�x
def create_ssh_settings(self, parent_frame):
    """uR�^ SSH -��[@SJX"""
    ssh_frame = ttk.LabelFrame(parent_frame, text="SSH -��[", padding=(10, 4))
    ssh_frame.pack(fill="x", pady=(0, 8))
    ssh_frame.columnconfigure(1, weight=1)
    
    ssh_settings = self.setup_data.get("SSH_Settings", {})
    
    # ;N_j0W@W�N�bx��U	�
    ttk.Label(ssh_frame, text=";N_j0W@W:").grid(row=0, column=0, sticky="w", pady=4)
    self.vars["SSH_Host"] = tk.StringVar(value=ssh_settings.get("Host", "192.168.11.143"))
    
    # 	�eQ IP wk�S
    ip_history = ssh_settings.get("IP_History", ["192.168.11.143", "192.168.225.1"])
    
    self.ssh_host_combo = ttk.Combobox(ssh_frame, textvariable=self.vars["SSH_Host"], 
                                      values=ip_history, width=20)
    self.ssh_host_combo.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=4)
    self.ssh_host_combo.bind("<<ComboboxSelected>>", self.on_ssh_host_changed)
    self.ssh_host_combo.bind("<Return>", self.on_ssh_host_enter)
    self.ssh_host_combo.bind("<FocusOut>", self.on_ssh_host_focus_out)
    
    # �e�X�� IP 	c�
    ttk.Button(ssh_frame, text="�e�XIP", command=self.add_ssh_ip).grid(row=0, column=2, padx=(5, 0), pady=4)
    
    # �W_�
    ttk.Label(ssh_frame, text="�W_�:").grid(row=1, column=0, sticky="w", pady=4)
    self.vars["SSH_Port"] = tk.StringVar(value=str(ssh_settings.get("Port", 22)))
    ttk.Entry(ssh_frame, textvariable=self.vars["SSH_Port"], width=20).grid(row=1, column=1, sticky="w", padx=(10, 0), pady=4)
    
    # �-�3^_��N�bx��U	�
    ttk.Label(ssh_frame, text="�-�3^_�:").grid(row=2, column=0, sticky="w", pady=4)
    self.vars["SSH_Default_Account"] = tk.StringVar(value=ssh_settings.get("Default_Account", "root/oelinux123"))
    
    # 	�eQ3^_�wk�S
    account_history = ssh_settings.get("Account_History", ["root/oelinux123", "root/"])
    
    self.ssh_account_combo = ttk.Combobox(ssh_frame, textvariable=self.vars["SSH_Default_Account"], 
                                         values=account_history, width=20)
    self.ssh_account_combo.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=4)
    self.ssh_account_combo.bind("<<ComboboxSelected>>", self.on_ssh_account_changed)
    
    # �e�X��3^_�	c�
    ttk.Button(ssh_frame, text="�e�X3^_�", command=self.add_ssh_account).grid(row=2, column=2, padx=(5, 0), pady=4)
    
    # #��}��Bf
    ttk.Label(ssh_frame, text="#��}��Bf:").grid(row=3, column=0, sticky="w", pady=4)
    self.vars["SSH_Connection_Timeout"] = tk.StringVar(value=str(ssh_settings.get("Connection_Timeout", 30)))
    ttk.Entry(ssh_frame, textvariable=self.vars["SSH_Connection_Timeout"], width=20).grid(row=3, column=1, sticky="w", padx=(10, 0), pady=4)
    
    # c�N��Bf
    ttk.Label(ssh_frame, text="c�N��Bf:").grid(row=4, column=0, sticky="w", pady=4)
    self.vars["SSH_Command_Timeout"] = tk.StringVar(value=str(ssh_settings.get("Command_Timeout", 30)))
    ttk.Entry(ssh_frame, textvariable=self.vars["SSH_Command_Timeout"], width=20).grid(row=4, column=1, sticky="w", padx=(10, 0), pady=4)
