"""
测试远程关键字返回处理器
"""

import pytest
from pytest_dsl.remote.return_handlers import (
    RemoteReturnHandler,
    HTTPReturnHandler,
    AssertionReturnHandler,
    DefaultReturnHandler,
    ReturnHandlerRegistry,
    register_return_handler
)


class TestReturnHandler(RemoteReturnHandler):
    """测试用的返回处理器"""
    
    def can_handle(self, return_data):
        return isinstance(return_data, dict) and 'test_data' in return_data
    
    def process(self, return_data, context=None):
        return {
            'result': return_data['test_data'],
            'side_effects': {
                'variables': {'test_var': return_data['test_data']}
            },
            'metadata': {'keyword_type': 'test'}
        }
    
    @property
    def priority(self):
        return 5


class TestReturnHandlers:
    """测试返回处理器功能"""
    
    def test_http_return_handler(self):
        """测试HTTP返回处理器"""
        handler = HTTPReturnHandler()

        # 测试can_handle - 使用新格式的HTTP数据
        http_data = {
            'result': {'var1': 'value1'},
            'side_effects': {
                'variables': {'var1': 'value1'},
                'context_updates': {
                    'session_state': {'session1': {}},
                    'response': {'status': 200}
                }
            },
            'metadata': {'keyword_type': 'http_request'}
        }
        assert handler.can_handle(http_data)

        # 测试不匹配的数据
        non_http_data = {'result': 'value'}
        assert not handler.can_handle(non_http_data)

        # 测试process - HTTP处理器直接返回数据
        processed = handler.process(http_data)
        assert processed == http_data  # HTTP处理器直接返回原数据
    
    def test_assertion_return_handler(self):
        """测试断言返回处理器"""
        handler = AssertionReturnHandler()
        
        # 测试can_handle
        assertion_data = {
            'result': 'value',
            'captures': {'extracted_var': 'extracted_value'},
            'metadata': {'jsonpath': '$.data.value'}
        }
        assert handler.can_handle(assertion_data)
        
        # 测试process
        processed = handler.process(assertion_data)
        assert processed['result'] == 'value'
        assert processed['side_effects']['variables'] == {'extracted_var': 'extracted_value'}
        assert processed['metadata']['jsonpath'] == '$.data.value'
    
    def test_default_return_handler(self):
        """测试默认返回处理器"""
        handler = DefaultReturnHandler()
        
        # 默认处理器总是能处理
        assert handler.can_handle({'any': 'data'})
        assert handler.can_handle('simple_value')
        
        # 测试字典格式
        dict_data = {'result': 'value', 'metadata': {'info': 'test'}}
        processed = handler.process(dict_data)
        assert processed['result'] == 'value'
        assert processed['metadata']['info'] == 'test'
        
        # 测试简单值
        simple_data = 'simple_value'
        processed = handler.process(simple_data)
        assert processed['result'] == 'simple_value'
        assert processed['side_effects'] == {}
    
    def test_return_handler_registry(self):
        """测试返回处理器注册表"""
        registry = ReturnHandlerRegistry()
        
        # 注册测试处理器
        test_handler = TestReturnHandler()
        registry.register(test_handler)
        
        # 测试处理器按优先级排序
        priorities = [h.priority for h in registry._handlers]
        assert priorities == sorted(priorities)
        
        # 测试处理匹配的数据
        test_data = {'test_data': 'test_value'}
        processed = registry.process(test_data)
        assert processed['result'] == 'test_value'
        assert processed['side_effects']['variables']['test_var'] == 'test_value'
        
        # 测试处理不匹配的数据（应该使用默认处理器）
        other_data = {'other': 'value'}
        processed = registry.process(other_data)
        assert processed['result'] == {'other': 'value'}
    
    def test_register_return_handler_function(self):
        """测试注册函数"""
        # 这个测试会影响全局状态，所以要小心
        original_handlers_count = len(register_return_handler.__globals__['return_handler_registry']._handlers)
        
        test_handler = TestReturnHandler()
        register_return_handler(test_handler)
        
        new_handlers_count = len(register_return_handler.__globals__['return_handler_registry']._handlers)
        assert new_handlers_count == original_handlers_count + 1
    
    def test_priority_ordering(self):
        """测试优先级排序"""
        registry = ReturnHandlerRegistry()
        
        # 创建不同优先级的处理器
        class HighPriorityHandler(RemoteReturnHandler):
            def can_handle(self, return_data):
                return isinstance(return_data, dict) and 'high' in return_data
            def process(self, return_data, context=None):
                return {'result': 'high_priority'}
            @property
            def priority(self):
                return 1
        
        class LowPriorityHandler(RemoteReturnHandler):
            def can_handle(self, return_data):
                return isinstance(return_data, dict) and 'high' in return_data  # 故意重叠
            def process(self, return_data, context=None):
                return {'result': 'low_priority'}
            @property
            def priority(self):
                return 50
        
        # 先注册低优先级，再注册高优先级
        registry.register(LowPriorityHandler())
        registry.register(HighPriorityHandler())
        
        # 高优先级应该先被使用
        test_data = {'high': 'value'}
        processed = registry.process(test_data)
        assert processed['result'] == 'high_priority'
    
    def test_side_effects_format(self):
        """测试副作用格式处理"""
        registry = ReturnHandlerRegistry()

        # 测试新格式的数据
        new_format_data = {
            'result': 'main_result',
            'side_effects': {
                'variables': {'var1': 'value1'},
                'context_updates': {'session': 'active'},
                'custom_handlers': [{'type': 'logger'}]
            },
            'metadata': {'type': 'custom'}
        }

        # 新格式会被默认处理器处理，提取result字段
        processed = registry.process(new_format_data)
        # 默认处理器会提取result字段
        assert processed['result'] == 'main_result'
        assert processed['metadata']['type'] == 'custom'
    
    def test_non_dict_data(self):
        """测试非字典数据的处理"""
        registry = ReturnHandlerRegistry()
        
        # 测试字符串
        result = registry.process("simple_string")
        assert result == "simple_string"
        
        # 测试数字
        result = registry.process(42)
        assert result == 42
        
        # 测试列表
        result = registry.process([1, 2, 3])
        assert result == [1, 2, 3]
    
    def test_handler_error_handling(self):
        """测试处理器错误处理"""
        class ErrorHandler(RemoteReturnHandler):
            def can_handle(self, return_data):
                return isinstance(return_data, dict) and 'error_test' in return_data
            def process(self, return_data, context=None):
                raise ValueError("Test error")
            @property
            def priority(self):
                return 1
        
        registry = ReturnHandlerRegistry()
        registry.register(ErrorHandler())
        
        # 如果处理器抛出异常，应该被传播
        test_data = {'error_test': True}
        with pytest.raises(ValueError, match="Test error"):
            registry.process(test_data)


if __name__ == "__main__":
    pytest.main([__file__])
