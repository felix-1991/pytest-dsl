"""变量替换工具模块

该模块提供了高级的变量替换功能，支持复杂的变量访问语法。
"""

import json
from typing import Any, Dict, List, Optional
from pytest_dsl.core.global_context import global_context
from pytest_dsl.core.context import TestContext
from pytest_dsl.core.expression_utils import (
    evaluate_arithmetic_operation,
    evaluate_comparison_operation,
    evaluate_logical_operation,
    evaluate_unary_operation,
)
from pytest_dsl.core.serialization_utils import XMLRPCSerializer


class VariableReplacer:
    """变量替换器，支持高级变量访问语法"""

    def __init__(self, local_variables: Dict[str, Any] = None, test_context: TestContext = None):
        """初始化变量替换器

        Args:
            local_variables: 本地变量字典
            test_context: 测试上下文
        """
        self.local_variables = (
            local_variables if local_variables is not None else {}
        )
        self._test_context = test_context

    @property
    def test_context(self) -> TestContext:
        """获取测试上下文，如果没有提供则尝试从关键字管理器获取"""
        if self._test_context:
            return self._test_context

        # 尝试从关键字管理器获取当前上下文
        try:
            from pytest_dsl.core.keyword_manager import keyword_manager
            return getattr(keyword_manager, 'current_context', None)
        except ImportError:
            return None

    def get_variable(self, var_name: str) -> Any:
        """获取变量值，按优先级顺序查找

        查找顺序：
        1. 本地变量
        2. 测试上下文
        3. 全局上下文（包含YAML变量的访问）

        Args:
            var_name: 变量名

        Returns:
            变量值

        Raises:
            KeyError: 当变量不存在时
        """
        # 从本地变量获取
        if var_name in self.local_variables:
            value = self.local_variables[var_name]
            return self._convert_value(value)

        # 从测试上下文中获取（优先级高于YAML变量）
        context = self.test_context
        if context and context.has(var_name):
            value = context.get(var_name)
            return self._convert_value(value)

        # 从全局上下文获取（包含对YAML变量的统一访问）
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
                int_value = int(value)
                # 避免将超出XML-RPC范围的整数字符串转换为int
                if (XMLRPCSerializer.MIN_INT_VALUE <= int_value <=
                        XMLRPCSerializer.MAX_INT_VALUE):
                    return int_value
                return value
            except (ValueError, TypeError):
                pass
        return value

    def replace_in_string(self, value: str, expression_evaluator=None) -> Any:
        """替换字符串中的变量引用

        支持多种访问语法：
        - 基本变量: ${variable}
        - 点号访问: ${object.property}
        - 数组索引: ${array[0]}, ${array[-1]}
        - 字典键访问: ${dict["key"]}, ${dict['key']}
        - 混合访问: ${users[0].name}, ${data["users"][0]["name"]}

        Args:
            value: 包含变量引用的字符串
            expression_evaluator: 可选的表达式求值回调。提供时，占位符
                内容会按 DSL 表达式语法求值，而不是只按变量路径解析。

        Returns:
            替换后的字符串或原始对象（如果整个值是单一变量引用）

        Raises:
            KeyError: 当变量不存在时
        """
        if not isinstance(value, str) or '${' not in value:
            return value

        matches = self._find_placeholders(value)
        if not matches:
            return value

        # 检查是否整个字符串就是一个变量引用
        is_single_placeholder = (
            len(matches) == 1 and
            matches[0][0] == 0 and
            matches[0][1] == len(value)
        )
        if is_single_placeholder:
            # 如果整个字符串就是一个变量引用，直接返回变量值（保持原始类型）
            var_ref = matches[0][2]
            try:
                return self._evaluate_placeholder(
                    var_ref, expression_evaluator)
            except (KeyError, IndexError, TypeError, ValueError) as e:
                raise KeyError(f"无法解析变量引用 '${{{var_ref}}}': {str(e)}")

        # 如果字符串中包含多个变量引用或混合了字面量，进行字符串替换
        result = value

        # 从后向前替换，避免位置偏移
        for start, end, var_ref in reversed(matches):

            try:
                var_value = self._evaluate_placeholder(
                    var_ref, expression_evaluator)
                # 替换变量引用，转换为字符串
                result = result[:start] + str(var_value) + result[end:]
            except (KeyError, IndexError, TypeError, ValueError) as e:
                raise KeyError(f"无法解析变量引用 '${{{var_ref}}}': {str(e)}")

        return result

    def _find_placeholders(self, value: str) -> List[tuple]:
        """扫描字符串中的 ${...} 占位符边界。"""
        matches = []
        index = 0

        while index < len(value):
            start = value.find('${', index)
            if start == -1:
                break

            end = self._find_placeholder_end(value, start)
            if end is None:
                break

            matches.append((start, end, value[start + 2:end - 1]))
            index = end

        return matches

    def _find_placeholder_end(self, value: str, start: int) -> Optional[int]:
        """找到从 start 开始的占位符结束位置。"""
        depth = 1
        index = start + 2
        quote = None

        while index < len(value):
            char = value[index]

            if quote:
                if char == '\\':
                    index += 2
                    continue
                if char == quote:
                    quote = None
            else:
                if char in ("'", '"'):
                    quote = char
                elif value.startswith('${', index):
                    depth += 1
                    index += 2
                    continue
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        return index + 1

            index += 1

        return None

    def _evaluate_placeholder(self, var_ref: str, expression_evaluator=None):
        """求值占位符内部表达式。"""
        if expression_evaluator:
            return expression_evaluator(var_ref)

        return self._evaluate_expression_text(var_ref)

    def _evaluate_expression_text(self, expr_text: str):
        """通过 parser 解析并求值占位符表达式。"""
        from pytest_dsl.core.parser import parse_expression_fragment

        expr_node, errors = parse_expression_fragment(expr_text)
        if errors:
            messages = "; ".join(error.get('message', str(error))
                                 for error in errors)
            raise ValueError(f"无效的占位符表达式 '{expr_text}': {messages}")
        if expr_node is None:
            raise ValueError(f"无效的占位符表达式 '{expr_text}'")

        return self._eval_expression_node(expr_node)

    def _eval_expression_node(self, expr_node):
        """求值 parser 生成的表达式节点。"""
        if expr_node.type == 'Expression':
            return self.replace_in_value(expr_node.value)
        if expr_node.type == 'StringLiteral':
            if '${' in expr_node.value:
                return self.replace_in_string(expr_node.value)
            return expr_node.value
        if expr_node.type == 'NumberLiteral':
            return expr_node.value
        if expr_node.type == 'BooleanExpr':
            return expr_node.value
        if expr_node.type == 'VariableRef':
            return self.get_variable(expr_node.value)
        if expr_node.type == 'PlaceholderRef':
            return self.replace_in_string(expr_node.value)
        if expr_node.type == 'ListExpr':
            return [self._eval_expression_node(item)
                    for item in expr_node.children]
        if expr_node.type == 'DictExpr':
            return {
                self._eval_expression_node(item.children[0]):
                self._eval_expression_node(item.children[1])
                for item in expr_node.children
            }
        if expr_node.type == 'IndexAccessExpr':
            collection = self._eval_expression_node(expr_node.children[0])
            key = self._eval_expression_node(expr_node.children[1])
            return self.access_by_key(collection, key)
        if expr_node.type == 'PropertyAccessExpr':
            current_value = self._eval_expression_node(expr_node.children[0])
            return self.access_property(current_value, expr_node.value)
        if expr_node.type == 'UnaryExpr':
            value = self._eval_expression_node(expr_node.children[0])
            return evaluate_unary_operation(value, expr_node.value)
        if expr_node.type == 'ArithmeticExpr':
            return self._eval_arithmetic_expr(expr_node)
        if expr_node.type == 'ComparisonExpr':
            return self._eval_comparison_expr(expr_node)
        if expr_node.type == 'LogicalExpr':
            return self._eval_logical_expr(expr_node)

        raise ValueError(f"无法求值的表达式类型: {expr_node.type}")

    def _eval_arithmetic_expr(self, expr_node):
        left_value = self._eval_expression_node(expr_node.children[0])
        right_value = self._eval_expression_node(expr_node.children[1])
        return evaluate_arithmetic_operation(
            left_value, right_value, expr_node.value)

    def _eval_comparison_expr(self, expr_node):
        left_value = self._eval_expression_node(expr_node.children[0])
        right_value = self._eval_expression_node(expr_node.children[1])
        return evaluate_comparison_operation(
            left_value, right_value, expr_node.value)

    def _eval_logical_expr(self, expr_node):
        return evaluate_logical_operation(
            expr_node.children, expr_node.value, self._eval_expression_node)

    def access_by_key(self, current_value, key):
        """使用求值后的索引或键访问集合。"""
        if isinstance(current_value, (list, tuple)):
            if not isinstance(key, int):
                raise TypeError(
                    f"无法在 {type(current_value).__name__} 类型上使用字符串键访问")
            if key >= len(current_value) or key < -len(current_value):
                raise IndexError(
                    f"数组索引 {key} 超出范围，数组长度为 {len(current_value)}")
            return current_value[key]

        if isinstance(current_value, dict):
            if isinstance(key, int):
                str_key = str(key)
                if key not in current_value and str_key not in current_value:
                    raise KeyError(f"字典中不存在键 '{key}' 或 '{str_key}'")
                return current_value.get(key, current_value.get(str_key))

            if key not in current_value:
                raise KeyError(f"字典中不存在键 '{key}'")
            return current_value[key]

        if isinstance(key, int):
            raise TypeError(
                f"无法在 {type(current_value).__name__} 类型上使用索引访问")

        raise TypeError(
            f"无法在 {type(current_value).__name__} 类型上使用字符串键访问")

    def access_property(self, current_value, property_name: str):
        """使用点号语法访问字典属性。"""
        if isinstance(current_value, dict) and property_name in current_value:
            return current_value[property_name]

        raise KeyError(
            f"无法访问属性 '{property_name}'，当前值类型是 {type(current_value).__name__}")

    def replace_in_dict(self, data: Dict[str, Any], visited: Optional[set] = None) -> Dict[str, Any]:
        """递归替换字典中的变量引用

        Args:
            data: 包含变量引用的字典
            visited: 已访问对象的集合，用于检测循环引用

        Returns:
            替换后的字典

        Raises:
            KeyError: 当变量不存在时
        """
        if not isinstance(data, dict):
            return data

        # 初始化访问集合
        if visited is None:
            visited = set()

        # 检测循环引用
        data_id = id(data)
        if data_id in visited:
            return {"<循环引用>": f"字典对象 {type(data).__name__}"}

        visited.add(data_id)
        try:
            result = {}
            for key, value in data.items():
                # 替换键中的变量
                new_key = self.replace_in_string(
                    key) if isinstance(key, str) else key
                # 替换值中的变量
                new_value = self.replace_in_value(value, visited)
                result[new_key] = new_value

            return result
        finally:
            visited.discard(data_id)

    def replace_in_list(self, data: List[Any], visited: Optional[set] = None) -> List[Any]:
        """递归替换列表中的变量引用

        Args:
            data: 包含变量引用的列表
            visited: 已访问对象的集合，用于检测循环引用

        Returns:
            替换后的列表

        Raises:
            KeyError: 当变量不存在时
        """
        if not isinstance(data, list):
            return data

        # 初始化访问集合
        if visited is None:
            visited = set()

        # 检测循环引用
        data_id = id(data)
        if data_id in visited:
            return [f"<循环引用: 列表对象 {type(data).__name__}>"]

        visited.add(data_id)
        try:
            return [self.replace_in_value(item, visited) for item in data]
        finally:
            visited.discard(data_id)

    def replace_in_value(self, value: Any, visited: Optional[set] = None) -> Any:
        """递归替换任意值中的变量引用

        Args:
            value: 任意值，可能是字符串、字典、列表等
            visited: 已访问对象的集合，用于检测循环引用

        Returns:
            替换后的值

        Raises:
            KeyError: 当变量不存在时
        """
        if isinstance(value, str):
            return self.replace_in_string(value)
        elif isinstance(value, dict):
            return self.replace_in_dict(value, visited)
        elif isinstance(value, list):
            return self.replace_in_list(value, visited)
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
