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


def _is_safe_expression(value_str: str) -> bool:
    """检查字符串是否是安全的数学表达式

    Args:
        value_str: 要检查的字符串

    Returns:
        是否是安全的数学表达式
    """
    # 包含换行符、回车符等特殊字符时不是安全表达式
    if any(char in value_str for char in [
            '\n', '\r', '\t', ';', '\\', '"', "'"]):
        return False

    # 只包含数字、运算符、括号和空格的才是安全表达式
    import re
    safe_pattern = r'^[\d\+\-\*\/\%\(\)\.\s]+$'
    return bool(re.match(safe_pattern, value_str))



def _safe_eval_expression(value_str: str) -> Any:
    """安全地执行表达式计算

    Args:
        value_str: 表达式字符串

    Returns:
        计算结果，如果无法计算则返回原字符串
    """
    if not _is_safe_expression(value_str):
        return value_str

    try:
        return eval(value_str)
    except Exception:
        return value_str


def _compare_values(actual: Any, expected: Any, operator: str = "==") -> bool:
    """比较两个值

    Args:
        actual: 实际值
        expected: 预期值
        operator: 比较运算符 (==, !=, >, <, >=, <=, contains, not_contains,
                 matches, and, or, not)

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
        # 将实际值转换为字符串进行正则匹配
        actual_str = str(actual)
        if isinstance(expected, str):
            try:
                return bool(re.match(expected, actual_str))
            except re.error:
                raise ValueError(f"无效的正则表达式: {expected}")
        return False
    elif operator == "and":
        return bool(actual) and bool(expected)
    elif operator == "or":
        return bool(actual) or bool(expected)
    elif operator == "not in":
        if isinstance(actual, (list, tuple, dict)):
            return expected not in actual
        elif isinstance(actual, str) and isinstance(expected, str):
            return expected not in actual
        return True
    elif operator == "not":
        return not bool(actual)
    else:
        raise ValueError(f"不支持的比较运算符: {operator}")


@keyword_manager.register('断言', [
    {'name': '条件', 'mapping': 'condition',
     'description': '断言条件表达式，例如: "${value} == 100" 或 "1 + 1 == 2"'},
    {'name': '消息', 'mapping': 'message',
        'description': '断言失败时的错误消息', 'default': '断言失败'},
], category='系统/断言', tags=['验证', '条件'])
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

    # 简单解析表达式，支持 ==, !=, >, <, >=, <=, contains, not_contains,
    # matches, in, and, or, not
    # 格式: "left_value operator right_value" 或 "boolean_expression"
    operators = ["==", "!=", ">", "<", ">=", "<=", "contains", "not_contains",
                 "matches", "in", "and", "or", "not"]

    # 检查是否包含操作符，注意顺序：长操作符优先
    operator_used = None
    operators = ["not_contains", "not in", ">=", "<=", "==", "!=", ">", "<", "contains", "matches", "in"]
    
    for op in operators:
        if f" {op} " in condition:
            operator_used = op
            break

    # 调试输出
    allure.attach(
        f"原始条件: {condition}\n检测到的操作符: {operator_used}",
        name="条件解析调试",
        attachment_type=allure.attachment_type.TEXT
    )

    if not operator_used:
        # 如果没有找到操作符，尝试作为布尔表达式直接求值
        try:
            # 对条件进行变量替换
            if '${' in condition:
                condition = (context.executor.variable_replacer
                           .replace_in_string(condition))
            
            # 调试输出
            allure.attach(
                f"变量替换后的条件: {condition}",
                name="变量替换调试",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # 尝试直接求值
            result = eval(condition)
            if not isinstance(result, bool):
                raise ValueError(f"表达式结果不是布尔值: {result}")
            if not result:
                raise AssertionError(f"{message}. 布尔表达式求值为假: {condition}")
            return True
        except Exception as e:
            raise AssertionError(
                f"{message}. 无法解析条件表达式: {condition}. 错误: {str(e)}")

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
            left_value = context.executor.variable_replacer.replace_in_string(
                left_value)

        # 修复：只对安全的表达式执行eval
        if isinstance(left_value, str) and _is_safe_expression(left_value):
            left_value = _safe_eval_expression(left_value)

        # 处理布尔值字符串和数字字符串
        # 对于特定操作符（如正则匹配），保持字符串类型不转换
        if isinstance(left_value, str) and operator_used not in ['matches', 'not_matches', 'regex_match']:
            if left_value.lower() in ('true', 'false'):
                left_value = left_value.lower() == 'true'
            elif left_value.lower() in (
                    'yes', 'no', '1', '0', 't', 'f', 'y', 'n'):
                left_value = left_value.lower() in ('yes', '1', 't', 'y')
            else:
                # 尝试转换为数字
                try:
                    if ('.' in left_value and
                            left_value.replace('.', '').replace('-', '').isdigit()):
                        left_value = float(left_value)
                    elif left_value.replace('-', '').isdigit():
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
            right_value = context.executor.variable_replacer.replace_in_string(
                right_value)

        # 修复：只对安全的表达式执行eval
        if isinstance(right_value, str) and _is_safe_expression(right_value):
            right_value = _safe_eval_expression(right_value)

        # 处理布尔值字符串
        # 对于特定操作符（如正则匹配），保持字符串类型不转换
        if isinstance(right_value, str) and operator_used not in ['matches', 'not_matches', 'regex_match']:
            if right_value.lower() in ('true', 'false'):
                right_value = right_value.lower() == 'true'
            elif right_value.lower() in (
                    'yes', 'no', '1', '0', 't', 'f', 'y', 'n'):
                right_value = right_value.lower() in ('yes', '1', 't', 'y')
            else:
                # 尝试转换为数字
                try:
                    if ('.' in right_value and
                            right_value.replace('.', '').replace('-', '').isdigit()):
                        right_value = float(right_value)
                    elif right_value.replace('-', '').isdigit():
                        right_value = int(right_value)
                except ValueError:
                    pass  # 如果不是数字，保持原样
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
            # 强制转换为字符串，确保正则匹配正常工作
            # 这样可以处理数字字符串被自动转换为整数的情况
            left_str = str(left_value)
            right_str = str(right_value)
            result = bool(re.match(right_str, left_str))
        except re.error:
            raise ValueError(f"无效的正则表达式: {right_value}")
    elif operator_used == "in":
        # 修复：特殊处理 in 操作符，避免对变量引用执行eval
        try:
            # 如果右值是字符串且看起来像变量名，直接使用
            if isinstance(right_value, str):
                # 检查是否是简单的变量名（不包含特殊字符）
                if right_value.isidentifier():
                    # 这是一个变量名，需要从上下文获取值
                    if hasattr(context, 'get') and callable(context.get):
                        right_value = context.get(right_value, right_value)
                    # 如果仍然是字符串，按字符串的in操作处理
                    if isinstance(right_value, str):
                        result = str(left_value) in right_value
                    else:
                        result = left_value in right_value
                else:
                    # 尝试解析为列表或字典，但要安全处理
                    if (right_value.startswith('[') and
                            right_value.endswith(']')):
                        try:
                            right_value = eval(right_value)
                            result = left_value in right_value
                        except Exception:
                            # 解析失败，按字符串处理
                            result = str(left_value) in right_value
                    elif (right_value.startswith('{') and
                          right_value.endswith('}')):
                        try:
                            right_value = eval(right_value)
                            result = (left_value in right_value.keys()
                                      if isinstance(right_value, dict)
                                      else left_value in right_value)
                        except Exception:
                            # 解析失败，按字符串处理
                            result = str(left_value) in right_value
                    else:
                        # 按字符串的in操作处理
                        result = str(left_value) in right_value
            else:
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
            # 降级为字符串包含检查
            result = str(left_value) in str(right_value)
    else:
        # 其他操作符需要类型转换
        if (isinstance(left_value, str) and
                isinstance(right_value, (int, float))):
            try:
                left_value = float(left_value)
            except Exception:
                pass
        elif (isinstance(right_value, str) and 
              isinstance(left_value, (int, float))):
            try:
                right_value = float(right_value)
            except Exception:
                pass

        # 记录类型转换后的值（用于调试）
        allure.attach(
            f"类型转换后左值: {left_value} ({type(left_value).__name__})\n"
            f"类型转换后右值: {right_value} ({type(right_value).__name__})",
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
    {'name': 'JSON数据', 'mapping': 'json_data', 
     'description': 'JSON数据（字符串或对象）'},
    {'name': 'JSONPath', 'mapping': 'jsonpath', 'description': 'JSONPath表达式'},
    {'name': '预期值', 'mapping': 'expected_value', 'description': '预期的值'},
    {'name': '操作符', 'mapping': 'operator', 
     'description': '比较操作符', 'default': '=='},
    {'name': '消息', 'mapping': 'message',
        'description': '断言失败时的错误消息', 'default': 'JSON断言失败'},
], category='系统/断言', tags=['验证', 'JSON'])
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
    {'name': 'JSON数据', 'mapping': 'json_data', 
     'description': 'JSON数据（字符串或对象）'},
    {'name': 'JSONPath', 'mapping': 'jsonpath', 'description': 'JSONPath表达式'},
    {'name': '变量名', 'mapping': 'variable', 'description': '存储提取值的变量名'},
], category='系统/数据提取', tags=['JSON', '提取'])
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

    # 检查是否是远程关键字调用（通过检查调用栈或特殊标记）
    # 这里简化处理：如果context存在且不是远程调用，返回简单值
    if context and hasattr(context, '__class__') and 'TestContext' in context.__class__.__name__:
        # 本地模式，返回简单值
        return value
    else:
        # 远程模式或无法确定时，返回完整格式以保持兼容性
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
    {'name': '类型', 'mapping': 'type',
        'description': '预期的类型 (string, number, boolean, list, object, null)'},
    {'name': '消息', 'mapping': 'message',
        'description': '断言失败时的错误消息', 'default': '类型断言失败'},
], category='系统/断言', tags=['类型', '验证'])
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
        # 如果是字符串，检查是否是列表格式的字符串
        if not result and isinstance(value, str):
            value_stripped = value.strip()
            if value_stripped.startswith('[') and value_stripped.endswith(']'):
                try:
                    import json
                    parsed = json.loads(value_stripped)
                    result = isinstance(parsed, list)
                except (json.JSONDecodeError, ValueError):
                    pass
    elif expected_type == 'object':
        result = isinstance(value, dict)
        # 如果是字符串，检查是否是对象格式的字符串
        if not result and isinstance(value, str):
            value_stripped = value.strip()
            if value_stripped.startswith('{') and value_stripped.endswith('}'):
                try:
                    import json
                    # 首先尝试标准JSON解析
                    parsed = json.loads(value_stripped)
                    result = isinstance(parsed, dict)
                except (json.JSONDecodeError, ValueError):
                    # 如果标准JSON解析失败，尝试使用eval（安全性检查）
                    try:
                        # 简单检查是否只包含安全字符
                        safe_chars = set("{}[]'\",:0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_中文字符 \t\n")
                        if all(c in safe_chars or ord(c) > 127 for c in value_stripped):
                            parsed = eval(value_stripped)
                            result = isinstance(parsed, dict)
                    except Exception:
                        pass
    elif expected_type == 'null':
        result = value is None
        # 如果是字符串，检查是否是null字符串
        if not result and isinstance(value, str):
            result = value.lower() in ['null', 'none']
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
    {'name': '操作符', 'mapping': 'operator', 
     'description': '比较操作符', 'default': '=='},
    {'name': '消息', 'mapping': 'message',
        'description': '断言失败时的错误消息', 'default': '数据比较失败'},
], category='系统/断言', tags=['比较', '验证'])
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

    # 修复：改进表达式检测和处理
    if isinstance(actual, str):
        # 只对安全的表达式执行eval
        if _is_safe_expression(actual):
            actual = _safe_eval_expression(actual)
        elif actual.lower() in ('true', 'false'):
            actual = actual.lower() == 'true'
        elif actual.lower() in ('yes', 'no', '1', '0', 't', 'f', 'y', 'n'):
            actual = actual.lower() in ('yes', '1', 't', 'y')

    if isinstance(expected, str):
        # 只对安全的表达式执行eval
        if _is_safe_expression(expected):
            expected = _safe_eval_expression(expected)
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
