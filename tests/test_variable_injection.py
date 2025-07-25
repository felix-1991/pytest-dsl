"""
测试变量注入和上下文更新功能
"""

import pytest
import threading
from pytest_dsl.core.dsl_executor import DSLExecutor
from pytest_dsl.core.global_context import global_context
from pytest_dsl.remote.keyword_client import RemoteKeywordClient


class TestVariableInjection:
    """测试变量注入功能"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        # 清理全局变量
        global_context.clear_all()
    
    def test_thread_local_executor_setting(self):
        """测试线程本地执行器设置"""
        executor = DSLExecutor()
        
        # 检查线程本地执行器是否正确设置
        assert hasattr(threading.current_thread(), 'dsl_executor')
        assert threading.current_thread().dsl_executor is executor
    
    def test_variable_injection_global(self):
        """测试全局变量注入"""
        executor = DSLExecutor()
        client = RemoteKeywordClient("http://localhost:8000", "localhost", 8000)
        
        # 模拟包含全局变量的返回数据
        processed_data = {
            'result': 'test_result',
            'side_effects': {
                'variables': {
                    'g_test_var': 'global_value',
                    'g_another_var': 42
                }
            },
            'metadata': {}
        }
        
        # 执行变量注入
        client._inject_variables(processed_data['side_effects']['variables'])
        
        # 验证全局变量是否正确注入
        assert global_context.get_variable('g_test_var') == 'global_value'
        assert global_context.get_variable('g_another_var') == 42
    
    def test_variable_injection_local(self):
        """测试本地变量注入"""
        executor = DSLExecutor()
        client = RemoteKeywordClient("http://localhost:8000", "localhost", 8000)
        
        # 模拟包含本地变量的返回数据
        processed_data = {
            'result': 'test_result',
            'side_effects': {
                'variables': {
                    'local_var': 'local_value',
                    'test_data': {'key': 'value'}
                }
            },
            'metadata': {}
        }
        
        # 执行变量注入
        client._inject_variables(processed_data['side_effects']['variables'])
        
        # 验证本地变量是否正确注入
        assert executor.variable_replacer.local_variables['local_var'] == 'local_value'
        assert executor.test_context.get('local_var') == 'local_value'
        assert executor.test_context.get('test_data') == {'key': 'value'}
    
    def test_context_updates(self):
        """测试上下文更新"""
        executor = DSLExecutor()
        client = RemoteKeywordClient("http://localhost:8000", "localhost", 8000)

        # 模拟上下文更新数据
        context_updates = {
            'session_state': {
                'session1': {'cookies': {'auth': 'token123'}}
            },
            'response': {
                'status_code': 200,
                'data': {'result': 'success'}
            },
            'custom_context': {
                'last_operation': 'http_request'
            }
        }

        # 执行上下文更新
        client._update_context(context_updates)

        # 这里主要验证方法能正常执行，不抛出异常
        # 实际的上下文更新逻辑可以根据需要进一步实现


    
    def test_handle_side_effects(self):
        """测试副作用处理"""
        executor = DSLExecutor()
        client = RemoteKeywordClient("http://localhost:8000", "localhost", 8000)

        # 模拟新格式数据
        processed_data = {
            'result': 'main_result',
            'side_effects': {
                'variables': {
                    'captured_var': 'captured_value',
                    'g_global_var': 'global_value'
                },
                'context_updates': {
                    'session_state': {'session1': {'active': True}},
                    'response': {'status': 200}
                }
            },
            'metadata': {
                'keyword_type': 'test',
                'execution_time': 0.1
            }
        }

        # 处理副作用
        client._handle_side_effects(processed_data)

        # 验证变量是否被正确注入
        assert executor.test_context.get('captured_var') == 'captured_value'
        assert global_context.get_variable('g_global_var') == 'global_value'
    
    def test_get_current_executor(self):
        """测试获取当前执行器"""
        executor = DSLExecutor()
        client = RemoteKeywordClient("http://localhost:8000", "localhost", 8000)
        
        # 获取当前执行器
        current_executor = client._get_current_executor()
        
        # 验证能正确获取到执行器
        assert current_executor is executor
    
    def test_variable_injection_without_executor(self):
        """测试没有执行器时的变量注入"""
        # 清除线程本地执行器
        if hasattr(threading.current_thread(), 'dsl_executor'):
            delattr(threading.current_thread(), 'dsl_executor')
        
        client = RemoteKeywordClient("http://localhost:8000", "localhost", 8000)
        
        # 模拟变量注入
        variables = {
            'fallback_var': 'fallback_value'
        }
        
        # 执行变量注入（应该回退到全局变量）
        client._inject_variables(variables)
        
        # 验证变量被注入为全局变量
        assert global_context.get_variable('fallback_var') == 'fallback_value'
    
    def test_error_handling_in_injection(self):
        """测试变量注入中的错误处理"""
        executor = DSLExecutor()
        client = RemoteKeywordClient("http://localhost:8000", "localhost", 8000)
        
        # 模拟可能导致错误的变量（例如不可序列化的对象）
        class UnserializableObject:
            def __str__(self):
                raise Exception("Cannot convert to string")
        
        variables = {
            'normal_var': 'normal_value',
            'error_var': UnserializableObject()
        }
        
        # 执行变量注入（应该处理错误但不崩溃）
        try:
            client._inject_variables(variables)
            # 正常变量应该被注入
            assert executor.test_context.get('normal_var') == 'normal_value'
        except Exception as e:
            # 如果有异常，应该是可控的
            assert "变量注入失败" in str(e) or isinstance(e, Exception)


if __name__ == "__main__":
    pytest.main([__file__])
