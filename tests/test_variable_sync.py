"""
变量传递功能测试
"""

import pytest
import threading
from unittest.mock import Mock, patch

from pytest_dsl.remote.keyword_client import RemoteKeywordClient, RemoteKeywordManager
from pytest_dsl.remote.keyword_server import RemoteKeywordServer
from pytest_dsl.core.global_context import global_context


class TestVariableTransfer:
    """变量传递功能测试类"""

    def setup_method(self):
        """测试前准备"""
        # 清理全局变量
        global_context.clear_all()

        # 设置测试变量
        global_context.set_variable('g_test_var1', 'value1')
        global_context.set_variable('g_test_var2', 'value2')

    def teardown_method(self):
        """测试后清理"""
        global_context.clear_all()

    def test_config_initialization(self):
        """测试配置初始化"""
        # 默认配置
        client = RemoteKeywordClient()
        assert client.sync_config['sync_global_vars'] is True
        assert client.sync_config['sync_yaml_vars'] is True

        # 自定义配置
        custom_config = {
            'sync_global_vars': False,
            'sync_yaml_vars': True,
        }
        client = RemoteKeywordClient(sync_config=custom_config)
        assert client.sync_config['sync_global_vars'] is False
        assert client.sync_config['sync_yaml_vars'] is True

    def test_collect_global_variables(self):
        """测试收集全局变量"""
        client = RemoteKeywordClient()
        variables = client._collect_global_variables()

        assert 'g_test_var1' in variables
        assert 'g_test_var2' in variables
        assert variables['g_test_var1'] == 'value1'
        assert variables['g_test_var2'] == 'value2'

    def test_collect_yaml_variables(self):
        """测试收集YAML变量"""
        client = RemoteKeywordClient()
        variables = client._collect_yaml_variables()

        # 应该包含测试配置或为空
        assert isinstance(variables, dict)

    @patch('xmlrpc.client.ServerProxy')
    def test_send_initial_variables(self, mock_server_proxy):
        """测试发送初始变量到远程"""
        # 模拟服务器响应
        mock_server = Mock()
        mock_server.sync_variables_from_client.return_value = {
            'status': 'success',
            'message': 'Variables received successfully'
        }
        mock_server_proxy.return_value = mock_server

        client = RemoteKeywordClient()
        client._send_initial_variables()

        # 验证调用了远程接口
        mock_server.sync_variables_from_client.assert_called_once()

    def test_remote_keyword_manager(self):
        """测试远程关键字管理器"""
        manager = RemoteKeywordManager()

        # 测试基本功能
        assert isinstance(manager.clients, dict)

    def test_server_variable_storage(self):
        """测试服务器变量存储"""
        server = RemoteKeywordServer()

        # 测试设置共享变量
        result = server.set_shared_variable('test_var', 'test_value')
        assert result['status'] == 'success'
        assert 'test_var' in server.shared_variables
        assert server.shared_variables['test_var'] == 'test_value'

        # 测试获取共享变量
        result = server.get_shared_variable('test_var')
        assert result['status'] == 'success'
        assert result['value'] == 'test_value'

        # 测试获取不存在的变量
        result = server.get_shared_variable('nonexistent')
        assert result['status'] == 'error'

        # 测试列出所有变量
        result = server.list_shared_variables()
        assert result['status'] == 'success'
        assert 'test_var' in result['variables']

    def test_server_sync_from_client(self):
        """测试服务器接收客户端变量"""
        server = RemoteKeywordServer()

        variables = {
            'g_client_var1': 'client_value1',
            'g_client_var2': 'client_value2'
        }

        result = server.sync_variables_from_client(variables)
        assert result['status'] == 'success'

        # 验证变量已存储
        assert server.shared_variables['g_client_var1'] == 'client_value1'
        assert server.shared_variables['g_client_var2'] == 'client_value2'

    def test_server_sync_batches_global_file_update(self, monkeypatch):
        server = RemoteKeywordServer()
        calls = []

        monkeypatch.setattr(
            global_context,
            'set_variables',
            lambda values, attach=True, lock_timeout=None: calls.append(
                (values, attach, lock_timeout)),
        )

        result = server.sync_variables_from_client({
            'g_first': 1,
            'g_second': 2,
            'local_only': 3,
        })

        assert result['status'] == 'success'
        assert len(calls) == 1
        assert calls[0][0:2] == (
            {'g_first': 1, 'g_second': 2}, False)
        assert calls[0][2] == 20.0

    def test_server_sync_metadata_returns_request_id_and_timings(self):
        server = RemoteKeywordServer.__new__(RemoteKeywordServer)
        server.api_key = None
        server.shared_variables = {}
        server._variables_lock = threading.RLock()
        server._sync_lock_timeout = 0.1

        result = server.sync_variables_from_client_with_metadata(
            {'local_only': 1},
            {
                'client_request_id': 'sync-request-123',
                'sync_timeout_seconds': 1.0,
            },
        )

        assert result['status'] == 'success'
        diagnostics = result['diagnostics']
        assert diagnostics['request_id'] == 'sync-request-123'
        assert diagnostics['stage'] == 'complete'
        assert diagnostics['sync_timeout_seconds'] == 1.0
        assert diagnostics['variable_count'] == 1
        assert diagnostics['elapsed_ms'] >= 0

    def test_server_sync_returns_structured_error_when_variable_lock_busy(self):
        class BusyLock:
            def __init__(self):
                self.timeout = None

            def acquire(self, timeout):
                self.timeout = timeout
                return False

            def release(self):
                raise AssertionError('unacquired lock must not be released')

        server = RemoteKeywordServer.__new__(RemoteKeywordServer)
        server.api_key = None
        server.shared_variables = {}
        server._variables_lock = BusyLock()
        server._sync_lock_timeout = 10.0

        result = server.sync_variables_from_client_with_metadata(
            {'local_only': 1},
            {
                'client_request_id': 'busy-request',
                'sync_timeout_seconds': 0.5,
            },
        )

        assert result['status'] == 'error'
        assert result['error_code'] == 'sync_lock_timeout'
        assert result['diagnostics']['stage'] == 'variables_lock'
        # The server reserves 0.1s for serializing and returning the response.
        assert 0 < server._variables_lock.timeout <= 0.4

    def test_server_file_lock_budget_is_shorter_than_rpc_timeout(
            self, monkeypatch):
        from filelock import Timeout as FileLockTimeout

        server = RemoteKeywordServer.__new__(RemoteKeywordServer)
        server.api_key = None
        server.shared_variables = {}
        server._variables_lock = threading.RLock()
        server._sync_lock_timeout = 0.01
        server._sync_file_lock_timeout = 20.0
        observed = {}

        def fail_file_lock(values, attach=True, lock_timeout=None):
            observed['lock_timeout'] = lock_timeout
            raise FileLockTimeout(global_context._lock_file)

        monkeypatch.setattr(global_context, 'set_variables', fail_file_lock)

        result = server.sync_variables_from_client_with_metadata(
            {'g_value': 1},
            {
                'client_request_id': 'file-lock-request',
                'sync_timeout_seconds': 0.5,
            },
        )

        assert result['status'] == 'error'
        assert result['error_code'] == 'global_file_lock_timeout'
        assert result['diagnostics']['stage'] == 'global_file_lock'
        assert 0 < observed['lock_timeout'] < 0.5

    def test_repeated_global_values_skip_disk_rewrite(self, monkeypatch):
        from contextlib import nullcontext
        from pytest_dsl.core.global_context import GlobalContext

        context = GlobalContext()
        writes = []
        monkeypatch.setattr(context, '_lock', lambda timeout=None: nullcontext())
        monkeypatch.setattr(
            context, '_load_variables', lambda: {'g_unchanged': 1})
        monkeypatch.setattr(
            context, '_save_variables', lambda values: writes.append(values))

        changed = context.set_variables(
            {'g_unchanged': 1}, attach=False, lock_timeout=0.1)

        assert changed is False
        assert writes == []

    def test_api_key_authentication(self):
        """测试API密钥认证"""
        server = RemoteKeywordServer(api_key='test_key')

        # 正确的API密钥
        result = server.set_shared_variable('test_var', 'test_value', 'test_key')
        assert result['status'] == 'success'

        # 错误的API密钥
        result = server.set_shared_variable('test_var', 'test_value', 'wrong_key')
        assert result['status'] == 'error'
        assert '认证失败' in result['error']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
