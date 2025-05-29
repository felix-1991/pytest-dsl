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

        Raises:
            KeyError: 当变量不存在时
        """
        if not isinstance(value, str) or '${' not in value:
            return value

        # 扩展的变量引用模式，支持数组索引和字典键访问
        # 匹配: ${variable}, ${obj.prop}, ${arr[0]}, ${dict["key"]}, ${obj[0].prop} 等
        pattern = r'\$\{([a-zA-Z_\u4e00-\u9fa5][a-zA-Z0-9_\u4e00-\u9fa5]*(?:(?:\.[a-zA-Z_\u4e00-\u9fa5][a-zA-Z0-9_\u4e00-\u9fa5]*)|(?:\[[^\]]+\]))*)\}'

        result = value
        matches = list(re.finditer(pattern, result))

        # 从后向前替换，避免位置偏移
        for match in reversed(matches):
            var_ref = match.group(1)  # 例如: "users[0].name" 或 "data['key']"

            try:
                var_value = self._parse_variable_path(var_ref)
                # 替换变量引用
                result = result[:match.start()] + str(var_value) + result[match.end():]
            except (KeyError, IndexError, TypeError) as e:
                raise KeyError(f"无法解析变量引用 '${{{var_ref}}}': {str(e)}")

        return result

    def _parse_variable_path(self, var_ref: str):
        """解析复杂的变量访问路径

        支持的语法：
        - variable
        - object.property
        - array[0]
        - dict["key"]
        - users[0].name
        - data["users"][0]["name"]

        Args:
            var_ref: 变量引用路径，如 "users[0].name"

        Returns:
            解析后的变量值

        Raises:
            KeyError: 当变量不存在时
            IndexError: 当数组索引超出范围时
            TypeError: 当类型不匹配时
        """
        # 解析访问路径
        path_parts = self._tokenize_path(var_ref)

        # 获取根变量
        root_var_name = path_parts[0]
        try:
            current_value = self.get_variable(root_var_name)
        except KeyError:
            raise KeyError(f"变量 '{root_var_name}' 不存在")

        # 逐步访问路径
        for part in path_parts[1:]:
            current_value = self._access_value(current_value, part, root_var_name)

        return current_value

    def _tokenize_path(self, var_ref: str) -> list:
        """将变量路径分解为访问令牌

        例如：
        - "users[0].name" -> ["users", "[0]", "name"]
        - "data['key'].items[1]" -> ["data", "['key']", "items", "[1]"]

        Args:
            var_ref: 变量引用路径

        Returns:
            访问令牌列表
        """
        tokens = []
        current_token = ""
        i = 0

        while i < len(var_ref):
            char = var_ref[i]

            if char == '.':
                if current_token:
                    tokens.append(current_token)
                    current_token = ""
            elif char == '[':
                if current_token:
                    tokens.append(current_token)
                    current_token = ""

                # 找到匹配的右括号
                bracket_count = 1
                bracket_content = "["
                i += 1

                while i < len(var_ref) and bracket_count > 0:
                    char = var_ref[i]
                    bracket_content += char
                    if char == '[':
                        bracket_count += 1
                    elif char == ']':
                        bracket_count -= 1
                    i += 1

                tokens.append(bracket_content)
                i -= 1  # 回退一位，因为外层循环会自增
            else:
                current_token += char

            i += 1

        if current_token:
            tokens.append(current_token)

        return tokens

    def _access_value(self, current_value, access_token: str, root_var_name: str):
        """根据访问令牌获取值

        Args:
            current_value: 当前值
            access_token: 访问令牌，如 "name", "[0]", "['key']"
            root_var_name: 根变量名（用于错误信息）

        Returns:
            访问后的值

        Raises:
            KeyError: 当键不存在时
            IndexError: 当索引超出范围时
            TypeError: 当类型不匹配时
        """
        if access_token.startswith('[') and access_token.endswith(']'):
            # 数组索引或字典键访问
            key_content = access_token[1:-1].strip()

            # 处理字符串键（带引号）
            if (key_content.startswith('"') and key_content.endswith('"')) or \
               (key_content.startswith("'") and key_content.endswith("'")):
                key = key_content[1:-1]  # 去掉引号
                if isinstance(current_value, dict):
                    if key not in current_value:
                        raise KeyError(f"字典中不存在键 '{key}'")
                    return current_value[key]
                else:
                    raise TypeError(f"无法在 {type(current_value).__name__} 类型上使用字符串键访问")

            # 处理数字索引
            try:
                index = int(key_content)
                if isinstance(current_value, (list, tuple)):
                    if index >= len(current_value) or index < -len(current_value):
                        raise IndexError(f"数组索引 {index} 超出范围，数组长度为 {len(current_value)}")
                    return current_value[index]
                elif isinstance(current_value, dict):
                    # 字典也可以用数字键
                    str_key = str(index)
                    if str_key not in current_value and index not in current_value:
                        raise KeyError(f"字典中不存在键 '{index}' 或 '{str_key}'")
                    return current_value.get(index, current_value.get(str_key))
                else:
                    raise TypeError(f"无法在 {type(current_value).__name__} 类型上使用索引访问")
            except ValueError:
                raise ValueError(f"无效的索引格式: '{key_content}'")

        else:
            # 属性访问（点号语法）
            if isinstance(current_value, dict) and access_token in current_value:
                return current_value[access_token]
            else:
                raise KeyError(f"无法访问属性 '{access_token}'，当前值类型是 {type(current_value).__name__}")

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