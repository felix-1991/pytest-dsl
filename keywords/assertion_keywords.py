"""断言关键字模块

该模块提供了针对不同数据类型的断言功能，以及JSON数据提取能力。
支持字符串、数字、布尔值、列表和JSON对象的比较和断言。
"""

import json
import re
import allure
from typing import Any, Dict, List, Union
import jsonpath_ng.ext as jsonpath
from core.keyword_manager import keyword_manager


def _extract_jsonpath(json_data: Union[Dict, List], path: str) -> Any:
    """使用JSONPath从JSON数据中提取值
    
    Args:
        json_data: 要提取数据的JSON对象或数组
        path: JSONPath表达式
        
    Returns:
        提取的值或值列表
    
    Raises:
        ValueError: 如果JSONPath表达式无效或找不到匹配项
    """
    try:
        if isinstance(json_data, str):
            json_data = json.loads(json_data)
        
        jsonpath_expr = jsonpath.parse(path)
        matches = [match.value for match in jsonpath_expr.find(json_data)]
        
        if not matches:
            return None
        elif len(matches) == 1:
            return matches[0]
        else:
            return matches
    except Exception as e:
        raise ValueError(f"JSONPath提取错误: {str(e)}")


def _compare_values(actual: Any, expected: Any, operator: str = "==") -> bool:
    """比较两个值
    
    Args:
        actual: 实际值（可以是表达式字符串）
        expected: 预期值
        operator: 比较运算符 (==, !=, >, <, >=, <=, contains, not_contains, matches)
        
    Returns:
        比较结果 (True/False)
    """
    # 尝试计算表达式（如果actual是字符串表达式）
    if isinstance(actual, str):
        # 检查是否是表达式
        if any(op in actual for op in ['+', '-', '*', '/', '%', '(', ')']):
            try:
                # 尝试计算表达式
                actual = eval(actual)
                allure.attach(
                    f"表达式: {actual}\n计算结果: {actual}",
                    name="表达式计算",
                    attachment_type=allure.attachment_type.TEXT
                )
            except Exception as e:
                # 如果无法计算，保持原样
                allure.attach(
                    f"表达式: {actual}\n计算失败: {str(e)}",
                    name="表达式计算失败",
                    attachment_type=allure.attachment_type.TEXT
                )
                pass
    
    # 将字符串形式的值转换为适当的类型
    if isinstance(expected, str) and expected.lower() in ['true', 'false']:
        if expected.lower() == 'true':
            expected = True
        else:
            expected = False
    
    # 如果实际值是字符串形式的布尔值，也要转换
    if isinstance(actual, str) and actual.lower() in ['true', 'false']:
        if actual.lower() == 'true':
            actual = True
        else:
            actual = False
            
    # 尝试将字符串转换为数字
    if isinstance(expected, str) and expected.replace('.', '', 1).isdigit():
        try:
            if '.' in expected:
                expected = float(expected)
            else:
                expected = int(expected)
        except (ValueError, TypeError):
            pass
            
    # 如果实际值是字符串但预期是数字，尝试转换实际值
    if isinstance(expected, (int, float)) and isinstance(actual, str):
        try:
            if '.' in actual or isinstance(expected, float):
                actual = float(actual)
            else:
                actual = int(actual)
        except (ValueError, TypeError):
            pass
            
    # 布尔值特殊处理：如果预期是布尔值且实际值是字符串表示的布尔值
    if isinstance(expected, bool) and isinstance(actual, str):
        actual_lower = actual.lower()
        if actual_lower == 'true':
            actual = True
        elif actual_lower == 'false':
            actual = False
    
    # 执行比较
    if operator == "==":
        return actual == expected
    elif operator == "!=":
        return actual != expected
    elif operator == ">":
        return actual > expected
    elif operator == "<":
        return actual < expected
    elif operator == ">=":
        return actual >= expected
    elif operator == "<=":
        return actual <= expected
    elif operator == "contains":
        if isinstance(actual, str) and isinstance(expected, str):
            return expected in actual
        elif isinstance(actual, (list, tuple, dict)):
            return expected in actual
        return False
    elif operator == "not_contains":
        if isinstance(actual, str) and isinstance(expected, str):
            return expected not in actual
        elif isinstance(actual, (list, tuple, dict)):
            return expected not in actual
        return True
    elif operator == "matches":
        if isinstance(actual, str) and isinstance(expected, str):
            try:
                return bool(re.match(expected, actual))
            except re.error:
                raise ValueError(f"无效的正则表达式: {expected}")
        return False
    else:
        raise ValueError(f"不支持的比较运算符: {operator}")


@keyword_manager.register('断言', [
    {'name': '条件', 'mapping': 'condition', 'description': '断言条件表达式，例如: "${value} == 100" 或 "1 + 1 == 2"'},
    {'name': '消息', 'mapping': 'message', 'description': '断言失败时的错误消息'},
])
def assert_condition(**kwargs):
    """执行表达式断言
    
    Args:
        condition: 断言条件表达式
        message: 断言失败时的错误消息
        
    Returns:
        断言结果 (True/False)
    
    Raises:
        AssertionError: 如果断言失败
    """
    condition = kwargs.get('condition')
    message = kwargs.get('message', '断言失败')
    
    # 简单解析表达式，支持 ==, !=, >, <, >=, <=, contains, not_contains, matches
    # 格式: "${value} operator expected" 或 "expression operator expected"
    operators = ["==", "!=", ">", "<", ">=", "<=", "contains", "not_contains", "matches"]
    
    # 先检查是否包含这些操作符
    operator_used = None
    for op in operators:
        if f" {op} " in condition:
            operator_used = op
            break
    
    if not operator_used:
        # 尝试评估表达式条件
        try:
            result = eval(condition)
            # 记录执行结果
            allure.attach(
                f"条件: {condition}\n结果: {result}",
                name="表达式计算",
                attachment_type=allure.attachment_type.TEXT
            )
            
            if not result:
                allure.attach(
                    f"条件: {condition}\n结果: {result}",
                    name="断言失败",
                    attachment_type=allure.attachment_type.TEXT
                )
                raise AssertionError(message)
            return True
        except Exception as e:
            raise AssertionError(f"{message}. 执行条件时出错: {str(e)}")
    
    # 解析左值和右值
    left_value, right_value = condition.split(f" {operator_used} ", 1)
    left_value = left_value.strip()
    right_value = right_value.strip()
    
    # 移除引号（如果有）
    if right_value.startswith('"') and right_value.endswith('"'):
        right_value = right_value[1:-1]
    elif right_value.startswith("'") and right_value.endswith("'"):
        right_value = right_value[1:-1]
    
    # 比较值（left_value可能包含表达式）
    result = _compare_values(left_value, right_value, operator_used)
    
    # 记录和处理断言结果
    if not result:
        allure.attach(
            f"实际值: {left_value}\n预期值: {right_value}\n操作符: {operator_used}",
            name="断言失败",
            attachment_type=allure.attachment_type.TEXT
        )
        raise AssertionError(message)
    
    # 记录成功的断言
    allure.attach(
        f"实际值: {left_value}\n预期值: {right_value}\n操作符: {operator_used}",
        name="断言成功",
        attachment_type=allure.attachment_type.TEXT
    )
    return True


@keyword_manager.register('JSON断言', [
    {'name': 'JSON数据', 'mapping': 'json_data', 'description': 'JSON数据（字符串或对象）'},
    {'name': 'JSONPath', 'mapping': 'jsonpath', 'description': 'JSONPath表达式'},
    {'name': '预期值', 'mapping': 'expected_value', 'description': '预期的值'},
    {'name': '操作符', 'mapping': 'operator', 'description': '比较操作符，默认为"=="'},
    {'name': '消息', 'mapping': 'message', 'description': '断言失败时的错误消息'},
])
def assert_json(**kwargs):
    """执行JSON断言
    
    Args:
        json_data: JSON数据（字符串或对象）
        jsonpath: JSONPath表达式
        expected_value: 预期的值
        operator: 比较操作符，默认为"=="
        message: 断言失败时的错误消息
        
    Returns:
        断言结果 (True/False)
        
    Raises:
        AssertionError: 如果断言失败
        ValueError: 如果JSONPath无效或找不到匹配项
    """
    json_data = kwargs.get('json_data')
    path = kwargs.get('jsonpath')
    expected_value = kwargs.get('expected_value')
    operator = kwargs.get('operator', '==')
    message = kwargs.get('message', 'JSON断言失败')
    
    # 解析JSON（如果需要）
    if isinstance(json_data, str):
        try:
            json_data = json.loads(json_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"无效的JSON数据: {str(e)}")
    
    # 使用JSONPath提取值
    actual_value = _extract_jsonpath(json_data, path)
    
    # 记录提取的值
    allure.attach(
        f"JSONPath: {path}\n提取值: {actual_value}",
        name="JSONPath提取结果",
        attachment_type=allure.attachment_type.TEXT
    )
    
    # 比较值
    result = _compare_values(actual_value, expected_value, operator)
    
    # 记录和处理断言结果
    if not result:
        allure.attach(
            f"实际值: {actual_value}\n预期值: {expected_value}\n操作符: {operator}",
            name="JSON断言失败",
            attachment_type=allure.attachment_type.TEXT
        )
        raise AssertionError(message)
    
    # 记录成功的断言
    allure.attach(
        f"实际值: {actual_value}\n预期值: {expected_value}\n操作符: {operator}",
        name="JSON断言成功",
        attachment_type=allure.attachment_type.TEXT
    )
    return True


@keyword_manager.register('JSON提取', [
    {'name': 'JSON数据', 'mapping': 'json_data', 'description': 'JSON数据（字符串或对象）'},
    {'name': 'JSONPath', 'mapping': 'jsonpath', 'description': 'JSONPath表达式'},
    {'name': '变量名', 'mapping': 'variable', 'description': '存储提取值的变量名'},
])
def extract_json(**kwargs):
    """从JSON数据中提取值并保存到变量
    
    Args:
        json_data: JSON数据（字符串或对象）
        jsonpath: JSONPath表达式
        variable: 存储提取值的变量名
        
    Returns:
        提取的值
        
    Raises:
        ValueError: 如果JSONPath无效或找不到匹配项
    """
    json_data = kwargs.get('json_data')
    path = kwargs.get('jsonpath')
    variable = kwargs.get('variable')
    
    # 解析JSON（如果需要）
    if isinstance(json_data, str):
        try:
            json_data = json.loads(json_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"无效的JSON数据: {str(e)}")
    
    # 使用JSONPath提取值
    value = _extract_jsonpath(json_data, path)
    
    # 记录提取的值
    allure.attach(
        f"JSONPath: {path}\n提取值: {value}\n保存到变量: {variable}",
        name="JSON数据提取",
        attachment_type=allure.attachment_type.TEXT
    )
    
    # 返回提取的值用于变量赋值
    return value


@keyword_manager.register('类型断言', [
    {'name': '值', 'mapping': 'value', 'description': '要检查的值'},
    {'name': '类型', 'mapping': 'type', 'description': '预期的类型 (string, number, boolean, list, object, null)'},
    {'name': '消息', 'mapping': 'message', 'description': '断言失败时的错误消息'},
])
def assert_type(**kwargs):
    """断言值的类型
    
    Args:
        value: 要检查的值
        type: 预期的类型 (string, number, boolean, list, object, null)
        message: 断言失败时的错误消息
        
    Returns:
        断言结果 (True/False)
        
    Raises:
        AssertionError: 如果断言失败
    """
    value = kwargs.get('value')
    expected_type = kwargs.get('type')
    message = kwargs.get('message', '类型断言失败')
    
    # 检查类型
    if expected_type == 'string':
        result = isinstance(value, str)
    elif expected_type == 'number':
        result = isinstance(value, (int, float))
    elif expected_type == 'boolean':
        result = isinstance(value, bool)
    elif expected_type == 'list':
        result = isinstance(value, list)
    elif expected_type == 'object':
        result = isinstance(value, dict)
    elif expected_type == 'null':
        result = value is None
    else:
        raise ValueError(f"不支持的类型: {expected_type}")
    
    # 记录和处理断言结果
    if not result:
        actual_type = type(value).__name__
        allure.attach(
            f"值: {value}\n实际类型: {actual_type}\n预期类型: {expected_type}",
            name="类型断言失败",
            attachment_type=allure.attachment_type.TEXT
        )
        raise AssertionError(message)
    
    # 记录成功的断言
    allure.attach(
        f"值: {value}\n类型: {expected_type}",
        name="类型断言成功",
        attachment_type=allure.attachment_type.TEXT
    )
    return True


@keyword_manager.register('数据比较', [
    {'name': '实际值', 'mapping': 'actual', 'description': '实际值'},
    {'name': '预期值', 'mapping': 'expected', 'description': '预期值'},
    {'name': '操作符', 'mapping': 'operator', 'description': '比较操作符，默认为"=="'},
    {'name': '消息', 'mapping': 'message', 'description': '断言失败时的错误消息'},
])
def compare_values(**kwargs):
    """比较两个值
    
    Args:
        actual: 实际值
        expected: 预期值
        operator: 比较操作符，默认为"=="
        message: 断言失败时的错误消息
        
    Returns:
        比较结果 (True/False)
        
    Raises:
        AssertionError: 如果比较失败
    """
    actual = kwargs.get('actual')
    expected = kwargs.get('expected')
    operator = kwargs.get('operator', '==')
    message = kwargs.get('message', '数据比较失败')
    
    # 比较值
    result = _compare_values(actual, expected, operator)
    
    # 记录和处理比较结果
    if not result:
        allure.attach(
            f"实际值: {actual}\n预期值: {expected}\n操作符: {operator}",
            name="数据比较失败",
            attachment_type=allure.attachment_type.TEXT
        )
        raise AssertionError(message)
    
    # 记录成功的比较
    allure.attach(
        f"实际值: {actual}\n预期值: {expected}\n操作符: {operator}",
        name="数据比较成功",
        attachment_type=allure.attachment_type.TEXT
    )
    return result 