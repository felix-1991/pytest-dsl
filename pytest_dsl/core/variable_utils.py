import re
from typing import Any, Dict, List, Union
from pytest_dsl.core.global_context import global_context
from pytest_dsl.core.context import TestContext
from pytest_dsl.core.yaml_vars import yaml_vars


class VariableReplacer:
    """统一的变量替换工具类
    
    提供统一的变量替换功能，支持字符串、字典和列表中的变量替换。
    变量查找优先级：本地变量 > 测试上下文 > YAML变量 > 全局上下文
    """
    
    def __init__(self, local_variables: Dict[str, Any] = None, test_context: TestContext = None):
        """初始化变量替换器
        
        Args:
            local_variables: 本地变量字典
            test_context: 测试上下文对象
        """
        self.local_variables = local_variables or {}
        self.test_context = test_context or TestContext()
        
    def get_variable(self, var_name: str) -> Any:
        """获取变量值，按照优先级查找
        
        Args:
            var_name: 变量名
            
        Returns:
            变量值，如果变量不存在则返回变量引用本身
        """
        # 从本地变量获取
        if var_name in self.local_variables:
            return self.local_variables[var_name]
        
        # 从测试上下文中获取
        if self.test_context.has(var_name):
            return self.test_context.get(var_name)
        
        # 从YAML变量中获取
        yaml_value = yaml_vars.get_variable(var_name)
        if yaml_value is not None:
            return yaml_value
            
        # 从全局上下文获取
        if global_context.has_variable(var_name):
            return global_context.get_variable(var_name)
            
        # 如果变量不存在，返回变量引用本身
        return f"${{{var_name}}}"
    
    def replace_in_string(self, value: str) -> str:
        """替换字符串中的变量引用
        
        Args:
            value: 包含变量引用的字符串
            
        Returns:
            替换后的字符串
        """
        if not isinstance(value, str) or '${' not in value:
            return value
            
        pattern = r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
        result = value
        matches = list(re.finditer(pattern, value))
        
        # 从后向前替换，避免前面的替换影响后面的索引位置
        for match in reversed(matches):
            var_name = match.group(1)
            var_value = self.get_variable(var_name)
            result = result[:match.start()] + str(var_value) + result[match.end():]
        
        return result
    
    def replace_in_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """递归替换字典中的变量引用
        
        Args:
            data: 包含变量引用的字典
            
        Returns:
            替换后的字典
        """
        if not isinstance(data, dict):
            return data
            
        return {k: self.replace_in_value(v) for k, v in data.items()}
    
    def replace_in_list(self, data: List[Any]) -> List[Any]:
        """递归替换列表中的变量引用
        
        Args:
            data: 包含变量引用的列表
            
        Returns:
            替换后的列表
        """
        if not isinstance(data, list):
            return data
            
        return [self.replace_in_value(item) for item in data]
    
    def replace_in_value(self, value: Any) -> Any:
        """递归替换任意值中的变量引用
        
        Args:
            value: 任意值，可能是字符串、字典、列表等
            
        Returns:
            替换后的值
        """
        if isinstance(value, str):
            return self.replace_in_string(value)
        elif isinstance(value, dict):
            return self.replace_in_dict(value)
        elif isinstance(value, list):
            return self.replace_in_list(value)
        else:
            return value 