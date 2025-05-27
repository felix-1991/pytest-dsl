"""
变量传递功能测试
"""

import pytest
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
