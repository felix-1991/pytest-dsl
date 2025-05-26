"""断言关键字模块

该模块提供了针对不同数据类型的断言功能，以及JSON数据提取能力。
支持字符串、数字、布尔值、列表和JSON对象的比较和断言。
"""

import json
import re
import allure
from typing import Any, Dict, List, Union
import jsonpath_ng.ext as jsonpath
from pytest_dsl.core.keyword_manager import keyword_manager


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
        actual: 实际值
        expected: 预期值
        operator: 比较运算符 (==, !=, >, <, >=, <=, contains, not_contains, matches, and, or, not)

    Returns:
        比较结果 (True/False)
    """
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
    elif operator == "and":
        return bool(actual) and bool(expected)
    elif operator == "or":
        return bool(actual) or bool(expected)
    elif operator == "not":
        return not bool(actual)
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
    context = kwargs.get('context')

    # 简单解析表达式，支持 ==, !=, >, <, >=, <=, contains, not_contains, matches, in, and, or, not
    # 格式: "left_value operator right_value" 或 "boolean_expression"
    operators = ["==", "!=", ">", "<", ">=", "<=", "contains", "not_contains", "matches", "in", "and", "or", "not"]

    # 先检查是否包含这些操作符
    operator_used = None
    for op in operators:
        if f" {op} " in condition:
            operator_used = op
            break

    if not operator_used:
        # 如果没有找到操作符，尝试作为布尔表达式直接求值
        try:
            # 对条件进行变量替换
            if '${' in condition:
                condition = context.executor.variable_replacer.replace_in_string(condition)
            # 尝试直接求值
            result = eval(condition)
            if not isinstance(result, bool):
                raise ValueError(f"表达式结果不是布尔值: {result}")
            if not result:
                raise AssertionError(f"{message}. 布尔表达式求值为假: {condition}")
            return True
        except Exception as e:
            raise AssertionError(f"{message}. 无法解析条件表达式: {condition}. 错误: {str(e)}")

    # 解析左值和右值
    left_value, right_value = condition.split(f" {operator_used} ", 1)
    left_value = left_value.strip()
    right_value = right_value.strip()

    # 移除引号（如果有）
    if left_value.startswith('"') and left_value.endswith('"'):
        left_value = left_value[1:-1]
    elif left_value.startswith("'") and left_value.endswith("'"):
        left_value = left_value[1:-1]

    if right_value.startswith('"') and right_value.endswith('"'):
        right_value = right_value[1:-1]
    elif right_value.startswith("'") and right_value.endswith("'"):
        right_value = right_value[1:-1]

    # 记录原始值（用于调试）
    allure.attach(
        f"原始左值: {left_value}\n原始右值: {right_value}\n操作符: {operator_used}",
        name="表达式解析",
        attachment_type=allure.attachment_type.TEXT
    )

    # 对左值进行变量替换和表达式计算
    try:
        # 如果左值包含变量引用，先进行变量替换
        if '${' in left_value:
            left_value = context.executor.variable_replacer.replace_in_string(left_value)

        # 检查是否需要计算表达式
        if any(op in str(left_value) for op in ['+', '-', '*', '/', '%', '(', ')']):
            try:
                # 确保数字类型的变量可以参与计算
                if isinstance(left_value, (int, float)):
                    left_value = str(left_value)
                # 尝试计算表达式
                left_value = eval(str(left_value))
            except Exception as e:
                allure.attach(
                    f"表达式计算错误: {str(e)}\n表达式: {left_value}",
                    name="表达式计算错误",
                    attachment_type=allure.attachment_type.TEXT
                )
                raise ValueError(f"表达式计算错误: {str(e)}")

        # 处理布尔值字符串和数字字符串
        if isinstance(left_value, str):
            if left_value.lower() in ('true', 'false'):
                left_value = left_value.lower() == 'true'
            elif left_value.lower() in ('yes', 'no', '1', '0', 't', 'f', 'y', 'n'):
                left_value = left_value.lower() in ('yes', '1', 't', 'y')
            else:
                # 尝试转换为数字
                try:
                    if '.' in left_value:
                        left_value = float(left_value)
                    else:
                        left_value = int(left_value)
                except ValueError:
                    pass  # 如果不是数字，保持原样
    except Exception as e:
        allure.attach(
            f"左值处理异常: {str(e)}\n左值: {left_value}",
            name="左值处理异常",
            attachment_type=allure.attachment_type.TEXT
        )
        raise

    # 对右值进行变量替换和表达式计算
    try:
        # 如果右值包含变量引用，先进行变量替换
        if '${' in right_value:
            right_value = context.executor.variable_replacer.replace_in_string(right_value)

        # 检查是否需要计算表达式
        if any(op in str(right_value) for op in ['+', '-', '*', '/', '%', '(', ')']):
            try:
                # 确保数字类型的变量可以参与计算
                if isinstance(right_value, (int, float)):
                    right_value = str(right_value)
                # 尝试计算表达式
                right_value = eval(str(right_value))
            except Exception as e:
                allure.attach(
                    f"表达式计算错误: {str(e)}\n表达式: {right_value}",
                    name="表达式计算错误",
                    attachment_type=allure.attachment_type.TEXT
                )
                raise ValueError(f"表达式计算错误: {str(e)}")

        # 处理布尔值字符串
        if isinstance(right_value, str):
            if right_value.lower() in ('true', 'false'):
                right_value = right_value.lower() == 'true'
            elif right_value.lower() in ('yes', 'no', '1', '0', 't', 'f', 'y', 'n'):
                right_value = right_value.lower() in ('yes', '1', 't', 'y')
    except Exception as e:
        allure.attach(
            f"右值处理异常: {str(e)}\n右值: {right_value}",
            name="右值处理异常",
            attachment_type=allure.attachment_type.TEXT
        )
        raise

    # 类型转换和特殊处理
    if operator_used == "contains":
        # 特殊处理字符串包含操作
        if isinstance(left_value, str) and isinstance(right_value, str):
            result = right_value in left_value
        elif isinstance(left_value, (list, tuple, dict)):
            result = right_value in left_value
        elif isinstance(left_value, (int, float, bool)):
            # 将左值转换为字符串进行比较
            result = str(right_value) in str(left_value)
        else:
            result = False
    elif operator_used == "not_contains":
        # 特殊处理字符串不包含操作
        if isinstance(left_value, str) and isinstance(right_value, str):
            result = right_value not in left_value
        elif isinstance(left_value, (list, tuple, dict)):
            result = right_value not in left_value
        elif isinstance(left_value, (int, float, bool)):
            # 将左值转换为字符串进行比较
            result = str(right_value) not in str(left_value)
        else:
            result = True
    elif operator_used == "matches":
        # 特殊处理正则表达式匹配
        try:
            if isinstance(left_value, str) and isinstance(right_value, str):
                result = bool(re.match(right_value, left_value))
            else:
                result = False
        except re.error:
            raise ValueError(f"无效的正则表达式: {right_value}")
    elif operator_used == "in":
        # 特殊处理 in 操作符
        try:
            # 尝试将右值解析为列表或字典
            if isinstance(right_value, str):
                right_value = eval(right_value)

            # 如果是字典，检查键
            if isinstance(right_value, dict):
                result = left_value in right_value.keys()
            else:
                result = left_value in right_value
        except Exception as e:
            allure.attach(
                f"in 操作符处理异常: {str(e)}\n左值: {left_value}\n右值: {right_value}",
                name="in 操作符处理异常",
                attachment_type=allure.attachment_type.TEXT
            )
            raise ValueError(f"in 操作符处理异常: {str(e)}")
    else:
        # 其他操作符需要类型转换
        if isinstance(left_value, str) and isinstance(right_value, (int, float)):
            try:
                left_value = float(left_value)
            except:
                pass
        elif isinstance(right_value, str) and isinstance(left_value, (int, float)):
            try:
                right_value = float(right_value)
            except:
                pass

        # 记录类型转换后的值（用于调试）
        allure.attach(
            f"类型转换后左值: {left_value} ({type(left_value).__name__})\n类型转换后右值: {right_value} ({type(right_value).__name__})",
            name="类型转换",
            attachment_type=allure.attachment_type.TEXT
        )

        # 执行比较
        result = _compare_values(left_value, right_value, operator_used)

    # 记录和处理断言结果
    if not result:
        error_details = f"""
        断言失败详情:
        条件: {condition}
        实际值: {left_value} ({type(left_value).__name__})
        预期值: {right_value} ({type(right_value).__name__})
        操作符: {operator_used}
        消息: {message}
        """
        allure.attach(
            error_details,
            name="断言失败详情",
            attachment_type=allure.attachment_type.TEXT
        )
        raise AssertionError(error_details)

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
        context: 测试上下文

    Returns:
        提取的值或包含提取值的字典（远程模式）

    Raises:
        ValueError: 如果JSONPath无效或找不到匹配项
    """
    json_data = kwargs.get('json_data')
    path = kwargs.get('jsonpath')
    variable = kwargs.get('variable')
    context = kwargs.get('context')

    # 解析JSON（如果需要）
    if isinstance(json_data, str):
        try:
            json_data = json.loads(json_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"无效的JSON数据: {str(e)}")

    # 使用JSONPath提取值
    value = _extract_jsonpath(json_data, path)

    # 将提取的值设置到上下文中（本地模式）
    if context and variable:
        context.set(variable, value)

    # 记录提取的值
    allure.attach(
        f"JSONPath: {path}\n提取值: {value}\n保存到变量: {variable}",
        name="JSON数据提取",
        attachment_type=allure.attachment_type.TEXT
    )

    # 统一返回格式 - 支持远程关键字模式
    return {
        "result": value,  # 主要返回值保持兼容
        "captures": {variable: value} if variable else {},  # 明确的捕获变量
        "session_state": {},
        "metadata": {
            "jsonpath": path,
            "variable_name": variable
        }
    }


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
        # 如果是字符串，尝试转换为数字
        if not result and isinstance(value, str):
            try:
                float(value)  # 尝试转换为数字
                result = True
            except ValueError:
                pass
    elif expected_type == 'boolean':
        result = isinstance(value, bool)
        # 如果是字符串，检查是否是布尔值字符串
        if not result and isinstance(value, str):
            value_lower = value.lower()
            result = value_lower in ['true', 'false']
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

    # 处理布尔值字符串和表达式
    if isinstance(actual, str):
        # 检查是否需要计算表达式
        if any(op in actual for op in ['+', '-', '*', '/', '%', '(', ')']):
            try:
                actual = eval(actual)
            except Exception as e:
                allure.attach(
                    f"表达式计算错误: {str(e)}\n表达式: {actual}",
                    name="表达式计算错误",
                    attachment_type=allure.attachment_type.TEXT
                )
                raise ValueError(f"表达式计算错误: {str(e)}")
        elif actual.lower() in ('true', 'false'):
            actual = actual.lower() == 'true'
        elif actual.lower() in ('yes', 'no', '1', '0', 't', 'f', 'y', 'n'):
            actual = actual.lower() in ('yes', '1', 't', 'y')

    if isinstance(expected, str):
        # 检查是否需要计算表达式
        if any(op in expected for op in ['+', '-', '*', '/', '%', '(', ')']):
            try:
                expected = eval(expected)
            except Exception as e:
                allure.attach(
                    f"表达式计算错误: {str(e)}\n表达式: {expected}",
                    name="表达式计算错误",
                    attachment_type=allure.attachment_type.TEXT
                )
                raise ValueError(f"表达式计算错误: {str(e)}")
        elif expected.lower() in ('true', 'false'):
            expected = expected.lower() == 'true'
        elif expected.lower() in ('yes', 'no', '1', '0', 't', 'f', 'y', 'n'):
            expected = expected.lower() in ('yes', '1', 't', 'y')

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