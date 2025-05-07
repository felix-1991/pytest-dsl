import re
import json
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
        self._test_context = test_context or TestContext()
        
    @property
    def test_context(self) -> TestContext:
        """获取测试上下文，确保始终使用最新的上下文对象
        
        如果上下文对象中包含executor属性，则使用executor的上下文
        （这确保即使上下文被替换也能获取正确的引用）
        
        Returns:
            测试上下文对象
        """
        if hasattr(self._test_context, 'executor') and self._test_context.executor is not None:
            return self._test_context.executor.test_context
        return self._test_context
        
    def get_variable(self, var_name: str) -> Any:
        """获取变量值，按照优先级查找
        
        Args:
            var_name: 变量名
            
        Returns:
            变量值，如果变量不存在则抛出 KeyError
            
        Raises:
            KeyError: 当变量不存在时
        """
        # 从本地变量获取
        if var_name in self.local_variables:
            value = self.local_variables[var_name]
            return self._convert_value(value)
        
        # 从测试上下文中获取
        if self.test_context.has(var_name):
            value = self.test_context.get(var_name)
            return self._convert_value(value)
        
        # 从YAML变量中获取
        yaml_value = yaml_vars.get_variable(var_name)
        if yaml_value is not None:
            return self._convert_value(yaml_value)
            
        # 从全局上下文获取
        if global_context.has_variable(var_name):
            value = global_context.get_variable(var_name)
            return self._convert_value(value)
            
        # 如果变量不存在，抛出异常
        raise KeyError(f"变量 '{var_name}' 不存在")
    
    def _convert_value(self, value: Any) -> Any:
        """转换值为正确的类型
        
        Args:
            value: 要转换的值
            
        Returns:
            转换后的值
        """
        if isinstance(value, str):
            # 处理布尔值
            if value.lower() in ('true', 'false'):
                return value.lower() == 'true'
            # 处理数字
            try:
                if '.' in value:
                    return float(value)
                return int(value)
            except (ValueError, TypeError):
                pass
        return value
    
    def replace_in_string(self, value: str) -> str:
        """替换字符串中的变量引用
        
        Args:
            value: 包含变量引用的字符串
            
        Returns:
            替换后的字符串
            
        Raises:
            KeyError: 当变量不存在时
        """
        if not isinstance(value, str) or '${' not in value:
            return value
            
        # 处理变量引用模式: ${variable} 或 ${variable.field.subfield}
        pattern = r'\$\{([a-zA-Z_\u4e00-\u9fa5][a-zA-Z0-9_\u4e00-\u9fa5]*(?:\.[a-zA-Z_\u4e00-\u9fa5][a-zA-Z0-9_\u4e00-\u9fa5]*)*)\}'
        
        result = value
        matches = list(re.finditer(pattern, result))
        
        # 从后向前替换，避免位置偏移
        for match in reversed(matches):
            var_ref = match.group(1)  # 例如: "api_test_data.user_id" 或 "variable"
            parts = var_ref.split('.')
            
            # 获取根变量
            root_var_name = parts[0]
            try:
                root_var = self.get_variable(root_var_name)
            except KeyError:
                raise KeyError(f"变量 '{root_var_name}' 不存在")
            
            # 递归访问嵌套属性
            var_value = root_var
            for part in parts[1:]:
                if isinstance(var_value, dict) and part in var_value:
                    var_value = var_value[part]
                else:
                    raise KeyError(f"无法访问属性 '{part}'，变量 '{root_var_name}' 的类型是 {type(var_value).__name__}")
            
            # 替换变量引用
            result = result[:match.start()] + str(var_value) + result[match.end():]
        
        return result
    
    def replace_in_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """递归替换字典中的变量引用
        
        Args:
            data: 包含变量引用的字典
            
        Returns:
            替换后的字典
            
        Raises:
            KeyError: 当变量不存在时
        """
        if not isinstance(data, dict):
            return data
            
        result = {}
        for key, value in data.items():
            # 替换键中的变量
            new_key = self.replace_in_string(key) if isinstance(key, str) else key
            # 替换值中的变量
            new_value = self.replace_in_value(value)
            result[new_key] = new_value
            
        return result
    
    def replace_in_list(self, data: List[Any]) -> List[Any]:
        """递归替换列表中的变量引用
        
        Args:
            data: 包含变量引用的列表
            
        Returns:
            替换后的列表
            
        Raises:
            KeyError: 当变量不存在时
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
            
        Raises:
            KeyError: 当变量不存在时
        """
        if isinstance(value, str):
            return self.replace_in_string(value)
        elif isinstance(value, dict):
            return self.replace_in_dict(value)
        elif isinstance(value, list):
            return self.replace_in_list(value)
        elif isinstance(value, (int, float, bool, type(None))):
            return value
        else:
            # 对于其他类型，尝试转换为字符串后替换
            try:
                str_value = str(value)
                if '${' in str_value:
                    replaced = self.replace_in_string(str_value)
                    # 尝试将替换后的字符串转换回原始类型
                    if isinstance(value, (int, float)):
                        return type(value)(replaced)
                    elif isinstance(value, bool):
                        return replaced.lower() == 'true'
                    return replaced
                return value
            except:
                return value
    
    def replace_in_json(self, json_str: str) -> str:
        """替换JSON字符串中的变量引用
        
        Args:
            json_str: 包含变量引用的JSON字符串
            
        Returns:
            替换后的JSON字符串
            
        Raises:
            KeyError: 当变量不存在时
            json.JSONDecodeError: 当JSON解析失败时
        """
        try:
            # 先解析JSON
            data = json.loads(json_str)
            # 替换变量
            replaced_data = self.replace_in_value(data)
            # 重新序列化为JSON
            return json.dumps(replaced_data, ensure_ascii=False)
        except json.JSONDecodeError:
            # 如果JSON解析失败，直接作为字符串处理
            return self.replace_in_string(json_str)
    
    def replace_in_yaml(self, yaml_str: str) -> str:
        """替换YAML字符串中的变量引用
        
        Args:
            yaml_str: 包含变量引用的YAML字符串
            
        Returns:
            替换后的YAML字符串
            
        Raises:
            KeyError: 当变量不存在时
        """
        try:
            import yaml
            # 先解析YAML
            data = yaml.safe_load(yaml_str)
            # 替换变量
            replaced_data = self.replace_in_value(data)
            # 重新序列化为YAML
            return yaml.dump(replaced_data, allow_unicode=True)
        except:
            # 如果YAML解析失败，直接作为字符串处理
            return self.replace_in_string(yaml_str) 