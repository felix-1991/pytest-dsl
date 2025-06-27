"""工具函数模块

该模块提供了各种共享的工具函数。
"""

import re
from typing import Dict, Any, Union, List

from pytest_dsl.core.global_context import global_context


def replace_variables_in_string(value: str) -> str:
    """替换字符串中的变量引用

    支持多种访问语法：
    - 基本变量: ${variable}
    - 点号访问: ${object.property}
    - 数组索引: ${array[0]}, ${array[-1]}
    - 字典键访问: ${dict["key"]}, ${dict['key']}
    - 混合访问: ${users[0].name}, ${data["users"][0]["name"]}

    Args:
        value: 包含变量引用的字符串

    Returns:
        替换后的字符串
    """
    if not isinstance(value, str):
        return value

    # 使用新的变量替换器
    from pytest_dsl.core.variable_utils import VariableReplacer
    replacer = VariableReplacer()

    try:
        return replacer.replace_in_string(value)
    except KeyError:
        # 如果新的替换器失败，回退到旧的逻辑以保持兼容性
        return _legacy_replace_variables_in_string(value)


def _legacy_replace_variables_in_string(value: str) -> str:
    """旧版变量替换逻辑（保持向后兼容性）"""
    # 基本变量引用模式: ${variable}
    basic_pattern = r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}'

    # 嵌套引用模式: ${variable.field.subfield}
    nested_pattern = r'\$\{([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+)\}'

    # 先处理嵌套引用
    matches = list(re.finditer(nested_pattern, value))
    for match in reversed(matches):
        var_ref = match.group(1)  # 例如: "api_test_data.user_id"
        parts = var_ref.split('.')

        # 获取根变量
        root_var_name = parts[0]
        if context_has_variable(root_var_name):
            root_var = get_variable(root_var_name)

            # 递归访问嵌套属性
            var_value = root_var
            for part in parts[1:]:
                if isinstance(var_value, dict) and part in var_value:
                    var_value = var_value[part]
                else:
                    # 无法解析的属性路径
                    var_value = f"${{{var_ref}}}"  # 保持原样
                    break

            # 替换变量引用
            value = value[:match.start()] + str(var_value) + \
                value[match.end():]

    # 再处理基本引用
    matches = list(re.finditer(basic_pattern, value))
    for match in reversed(matches):
        var_name = match.group(1)
        if context_has_variable(var_name):
            var_value = get_variable(var_name)
            value = value[:match.start()] + str(var_value) + \
                value[match.end():]

    return value


def replace_variables_in_dict(data: Union[Dict, List, str]) -> Union[Dict, List, str]:
    """递归替换字典中的变量引用

    Args:
        data: 包含变量引用的字典、列表或字符串

    Returns:
        替换变量后的数据
    """
    if isinstance(data, dict):
        return {k: replace_variables_in_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [replace_variables_in_dict(item) for item in data]
    elif isinstance(data, str) and '${' in data:
        return replace_variables_in_string(data)
    else:
        return data


def context_has_variable(var_name: str) -> bool:
    """检查变量是否存在于上下文中

    检查顺序：
    1. 测试上下文
    2. 全局上下文（包含YAML变量）
    """
    # 检查测试上下文
    try:
        from pytest_dsl.core.keyword_manager import keyword_manager
        current_context = getattr(keyword_manager, 'current_context', None)
        if current_context and current_context.has(var_name):
            return True
    except ImportError:
        pass

    # 检查全局上下文（包含YAML变量的统一访问）
    return global_context.has_variable(var_name)


def get_variable(var_name: str) -> Any:
    """获取变量值

    获取顺序：
    1. 测试上下文
    2. 全局上下文（包含YAML变量）
    """
    # 先从测试上下文获取
    try:
        from pytest_dsl.core.keyword_manager import keyword_manager
        current_context = getattr(keyword_manager, 'current_context', None)
        if current_context and current_context.has(var_name):
            return current_context.get(var_name)
    except ImportError:
        pass

    # 再从全局上下文获取（包含对YAML变量的统一访问）
    if global_context.has_variable(var_name):
        return global_context.get_variable(var_name)

    # 如果都没有找到，返回变量引用本身
    return f"${{{var_name}}}"


def deep_merge(base: Dict, override: Dict) -> Dict:
    """深度合并两个字典

    Args:
        base: 基础字典
        override: 覆盖字典

    Returns:
        合并后的字典
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # 递归合并嵌套字典
            result[key] = deep_merge(result[key], value)
        elif key in result and isinstance(result[key], list) and isinstance(value, list):
            # 合并列表
            result[key] = result[key] + value
        else:
            # 覆盖或添加值
            result[key] = value

    return result
