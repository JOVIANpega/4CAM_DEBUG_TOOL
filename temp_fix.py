    def _task_test_connection(self) -> None:
        """測試連線任務"""
        self._update_connection_status('connecting')
        self._append_output('正在測試 SSH 連線...')
        
        try:
            result = self.ssh.test_connection(
                self.var_dut_ip.get(),
                self.var_username.get(),
                int(self.var_timeout.get() or '15')
            )
            
            if result:
                self._update_connection_status('connected')
                self._append_output('✅ SSH 連線成功！', 'success')
            else:
                self._update_connection_status('disconnected')
                self._append_output('❌ SSH 連線失敗', 'error')
                
        except Exception as e:
            self._update_connection_status('disconnected')
            self._append_output(f'❌ 連線測試失敗：{e}', 'error')
