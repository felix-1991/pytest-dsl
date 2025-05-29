"""测试增强的变量访问语法"""

import pytest
from pytest_dsl.core.variable_utils import VariableReplacer
from pytest_dsl.core.context import TestContext


class TestEnhancedVariableAccess:
    """测试增强的变量访问语法"""

    def setup_method(self):
        """设置测试数据"""
        self.test_data = {
            # 基本变量
            'environment': 'test',
            'version': '1.0.0',

            # 嵌套字典
            'api': {
                'base_url': 'https://api.example.com',
                'timeout': 30,
                'endpoints': {
                    'login': '/auth/login',
                    'users': '/api/users'
                }
            },

            # 用户数据
            'test_users': {
                'admin': {
                    'username': 'admin',
                    'password': 'admin123',
                    'roles': ['admin', 'user'],
                    'profile': {
                        'name': '管理员',
                        'email': 'admin@example.com'
                    }
                }
            },

            # 数组数据
            'users_array': [
                {
                    'id': 1,
                    'name': '张三',
                    'tags': ['developer', 'python'],
                    'settings': {
                        'theme': 'dark',
                        'language': 'zh-CN'
                    }
                },
                {
                    'id': 2,
                    'name': '李四',
                    'tags': ['tester', 'automation']
                }
            ],

            # 字符串键映射
            'config_map': {
                'dev-server': 'https://dev.example.com',
                'api-key': 'test-key-123',
                'timeout': 30
            },

            # 简单数组
            'strings': ['hello', 'world', 'test'],
            'numbers': [1, 2, 3, 42, 100]
        }

        self.replacer = VariableReplacer(local_variables=self.test_data)

    def test_basic_variable_access(self):
        """测试基本变量访问"""
        assert self.replacer.replace_in_string("${environment}") == "test"
        assert self.replacer.replace_in_string("${version}") == "1.0.0"

    def test_dot_notation_access(self):
        """测试点号访问（现有功能）"""
        assert self.replacer.replace_in_string("${api.base_url}") == "https://api.example.com"
        assert self.replacer.replace_in_string("${api.timeout}") == "30"
        assert self.replacer.replace_in_string("${api.endpoints.login}") == "/auth/login"
        assert self.replacer.replace_in_string("${test_users.admin.username}") == "admin"

    def test_array_index_access(self):
        """测试数组索引访问"""
        # 正向索引
        assert self.replacer.replace_in_string("${users_array[0].id}") == "1"
        assert self.replacer.replace_in_string("${users_array[0].name}") == "张三"
        assert self.replacer.replace_in_string("${users_array[1].id}") == "2"
        assert self.replacer.replace_in_string("${users_array[1].name}") == "李四"

        # 负向索引
        assert self.replacer.replace_in_string("${users_array[-1].id}") == "2"
        assert self.replacer.replace_in_string("${users_array[-2].id}") == "1"

    def test_nested_array_access(self):
        """测试嵌套数组访问"""
        assert self.replacer.replace_in_string("${users_array[0].tags[0]}") == "developer"
        assert self.replacer.replace_in_string("${users_array[0].tags[1]}") == "python"
        assert self.replacer.replace_in_string("${users_array[1].tags[0]}") == "tester"
        assert self.replacer.replace_in_string("${test_users.admin.roles[0]}") == "admin"
        assert self.replacer.replace_in_string("${test_users.admin.roles[1]}") == "user"

    def test_string_key_access_double_quotes(self):
        """测试字符串键访问（双引号）"""
        assert self.replacer.replace_in_string('${config_map["dev-server"]}') == "https://dev.example.com"
        assert self.replacer.replace_in_string('${config_map["api-key"]}') == "test-key-123"
        assert self.replacer.replace_in_string('${config_map["timeout"]}') == "30"

    def test_string_key_access_single_quotes(self):
        """测试字符串键访问（单引号）"""
        assert self.replacer.replace_in_string("${config_map['dev-server']}") == "https://dev.example.com"
        assert self.replacer.replace_in_string("${config_map['api-key']}") == "test-key-123"

    def test_simple_array_access(self):
        """测试简单数组访问"""
        assert self.replacer.replace_in_string("${strings[0]}") == "hello"
        assert self.replacer.replace_in_string("${strings[1]}") == "world"
        assert self.replacer.replace_in_string("${strings[-1]}") == "test"
        assert self.replacer.replace_in_string("${numbers[0]}") == "1"
        assert self.replacer.replace_in_string("${numbers[-1]}") == "100"

    def test_complex_nested_access(self):
        """测试复杂嵌套访问"""
        assert self.replacer.replace_in_string("${users_array[0].settings.theme}") == "dark"
        assert self.replacer.replace_in_string("${users_array[0].settings.language}") == "zh-CN"
        assert self.replacer.replace_in_string("${test_users.admin.profile.name}") == "管理员"
        assert self.replacer.replace_in_string("${test_users.admin.profile.email}") == "admin@example.com"

    def test_mixed_access_patterns(self):
        """测试混合访问模式"""
        # 在同一个字符串中使用多种访问模式
        result = self.replacer.replace_in_string(
            "用户${users_array[0].name}的主题是${users_array[0].settings.theme}，"
            "服务器地址是${config_map['dev-server']}"
        )
        expected = "用户张三的主题是dark，服务器地址是https://dev.example.com"
        assert result == expected

    def test_error_handling(self):
        """测试错误处理"""
        # 不存在的变量
        with pytest.raises(KeyError, match="无法解析变量引用.*nonexistent.*不存在"):
            self.replacer.replace_in_string("${nonexistent}")

        # 数组索引超出范围
        with pytest.raises(KeyError, match="无法解析变量引用.*数组索引 10 超出范围"):
            self.replacer.replace_in_string("${strings[10]}")

        # 不存在的字典键
        with pytest.raises(KeyError, match="无法解析变量引用.*字典中不存在键.*nonexistent"):
            self.replacer.replace_in_string('${config_map["nonexistent"]}')

        # 类型错误
        with pytest.raises(KeyError, match="无法解析变量引用.*无法在 str 类型上使用索引访问"):
            self.replacer.replace_in_string("${environment[0]}")

    def test_backward_compatibility(self):
        """测试向后兼容性"""
        # 确保现有的点号语法仍然工作
        assert self.replacer.replace_in_string("${api.base_url}") == "https://api.example.com"
        assert self.replacer.replace_in_string("${test_users.admin.username}") == "admin"
        assert self.replacer.replace_in_string("${api.endpoints.login}") == "/auth/login"
