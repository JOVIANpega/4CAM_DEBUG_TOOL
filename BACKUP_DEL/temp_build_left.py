    def _build_left(self, parent: ttk.Frame) -> None:
        # 標題 + 字體 + 清空按鈕
        top = ttk.Frame(parent)
        top.pack(fill=tk.X)
        ttk.Label(top, text='4CAM_DEBUG_TOOL', font=('Microsoft JhengHei', 14, 'bold')).pack(side=tk.LEFT)
        
        # 右邊按鈕區域
        right_buttons = ttk.Frame(top)
        right_buttons.pack(side=tk.RIGHT)
        ttk.Button(right_buttons, text='清空輸出', command=self.on_clear_output, width=12).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(right_buttons, text='+', width=3, command=self.on_font_plus).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(right_buttons, text='-', width=3, command=self.on_font_minus).pack(side=tk.LEFT)

        # 連線設定
        lf_conn = ttk.LabelFrame(parent, text='連線設定', padding=8)
        lf_conn.pack(fill=tk.X, pady=(10, 6))
        self._add_labeled_entry(lf_conn, 'DUT IP', self.var_dut_ip, 0)
        self._add_labeled_entry(lf_conn, 'PC IP', self.var_pc_ip, 1)
        self._add_labeled_entry(lf_conn, 'Username', self.var_username, 2)
        # 移除密碼欄位，因為 DUT 不需要密碼
        self._add_labeled_entry(lf_conn, 'Timeout(sec)', self.var_timeout, 3)
        btns = ttk.Frame(lf_conn)
        btns.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))
        ttk.Button(btns, text='測試連線', command=self.on_test_connection).pack(side=tk.LEFT)
        ttk.Button(btns, text='重新載入指令', command=self.on_reload_commands).pack(side=tk.LEFT, padx=6)

        # 指令控制
        lf_cmd = ttk.LabelFrame(parent, text='指令控制（Command.txt）', padding=8)
        lf_cmd.pack(fill=tk.X, pady=(6, 6))
        ttk.Label(lf_cmd, text='指令檔').grid(row=0, column=0, sticky=tk.W)
        ent_cmdfile = ttk.Entry(lf_cmd, textvariable=self.var_command_file, width=42)
        ent_cmdfile.grid(row=0, column=1, sticky=tk.W, padx=(6, 0))
        ttk.Button(lf_cmd, text='選擇', command=self.on_pick_command_file).grid(row=0, column=2, padx=(6, 0))

        ttk.Label(lf_cmd, text='指令選擇').grid(row=1, column=0, sticky=tk.W, pady=(6, 0))
        self.cbo_commands = ttk.Combobox(lf_cmd, textvariable=self.var_command_choice, width=50, state='readonly')
        self.cbo_commands.grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=(6, 0), pady=(6, 0))
        self.cbo_commands.bind('<<ComboboxSelected>>', self.on_command_selected)
        ttk.Button(lf_cmd, text='執行指令', command=self.on_execute_selected_command).grid(row=2, column=2, sticky=tk.E, pady=(6, 0))
        ttk.Button(lf_cmd, text='開啟指令表', command=self.on_open_command_file).grid(row=2, column=1, sticky=tk.E, padx=(6, 0), pady=(6, 0))

        # 常用 Linux 指令
        lf_manual = ttk.LabelFrame(parent, text='常用 Linux 指令', padding=8)
        lf_manual.pack(fill=tk.X)
        
        # 常用 Linux 指令列表（含說明）
        self.linux_commands = [
            'ls -la - 列出詳細檔案資訊',
            'ls -la / - 列出根目錄詳細資訊', 
            'ls -la /tmp - 列出臨時目錄檔案',
            'ls -la /mnt/usr - 列出使用者目錄檔案',
            'pwd - 顯示當前工作目錄',
            'whoami - 顯示當前使用者',
            'uname -a - 顯示系統資訊',
            'df -h - 顯示磁碟使用量',
            'free -h - 顯示記憶體使用量',
            'ps aux - 顯示所有執行程序',
            'top - 即時系統監控',
            'netstat -an - 顯示網路連線',
            'ifconfig - 顯示網路介面',
            'route -n - 顯示路由表',
            'cat /proc/version - 顯示核心版本',
            'cat /proc/cpuinfo - 顯示 CPU 資訊',
            'cat /proc/meminfo - 顯示記憶體資訊',
            'uptime - 顯示系統運行時間',
            'date - 顯示系統時間',
            'hwclock - 顯示硬體時鐘',
            'mount - 顯示掛載點',
            'umount - 卸載檔案系統',
            'find / -name "*.log" 2>/dev/null - 搜尋日誌檔案',
            'grep -r "error" /var/log 2>/dev/null - 搜尋錯誤訊息',
            'tail -f /var/log/messages - 即時監控系統訊息',
            'dmesg | tail -20 - 顯示最近核心訊息',
            'lsmod - 顯示已載入模組',
            'lsusb - 顯示 USB 設備',
            'lspci - 顯示 PCI 設備',
            'i2cdetect -y 0 - 偵測 I2C 匯流排 0',
            'i2cdetect -y 1 - 偵測 I2C 匯流排 1'
        ]
        
        self.var_manual = tk.StringVar(value=self.linux_commands[0])
        cbo_manual = ttk.Combobox(lf_manual, textvariable=self.var_manual, values=self.linux_commands, width=47, state='readonly')
        cbo_manual.grid(row=0, column=0, padx=(0, 6))
        ttk.Button(lf_manual, text='執行', command=self.on_execute_manual).grid(row=0, column=1)

        # 檔案傳輸
        lf_copy = ttk.LabelFrame(parent, text='檔案傳輸（DUT → PC）', padding=8)
        lf_copy.pack(fill=tk.X, pady=(6, 0))
        
        # 常用檔案路徑下拉選單
        ttk.Label(lf_copy, text='常用路徑').grid(row=0, column=0, sticky=tk.W)
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
        cbo_common = ttk.Combobox(lf_copy, textvariable=self.var_common_path, values=self.common_paths, 
                                 width=45, state='readonly')
        cbo_common.grid(row=0, column=1, sticky=tk.W, padx=(6, 0))
        cbo_common.bind('<<ComboboxSelected>>', self.on_common_path_selected)
        
        self._add_labeled_entry(lf_copy, '來源（DUT glob）', self.var_src_glob, 1, width=42)
        
        # 目標資料夾輸入欄和開啟按鍵
        ttk.Label(lf_copy, text='目標（PC 資料夾）').grid(row=2, column=0, sticky=tk.W)
        entry_frame = ttk.Frame(lf_copy)
        entry_frame.grid(row=2, column=1, sticky=tk.W, padx=(6, 0))
        ent_dst = ttk.Entry(entry_frame, textvariable=self.var_dst_dir, width=42)
        ent_dst.pack(side=tk.LEFT)
        ttk.Button(entry_frame, text='📁', command=self.on_open_destination_folder, width=3).pack(side=tk.LEFT, padx=(6, 0))
        
        btns2 = ttk.Frame(lf_copy)
        btns2.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))
        ttk.Button(btns2, text='使用說明', command=self.on_show_help).pack(side=tk.LEFT)
        ttk.Button(btns2, text='開始傳輸', command=self.on_copy_from_dut).pack(side=tk.LEFT, padx=6)

        for child in lf_conn.winfo_children() + lf_cmd.winfo_children() + lf_manual.winfo_children() + lf_copy.winfo_children():
            try:
                child.configure(font=('Microsoft JhengHei', self.font_size))
            except Exception:
                pass
