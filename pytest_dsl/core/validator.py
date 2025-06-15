"""
pytest-dsl DSL格式校验模块

提供DSL语法验证、语义验证、关键字验证等功能
"""

import re
from typing import List, Dict, Optional, Tuple
from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import get_parser, Node, parse_with_error_handling
from pytest_dsl.core.keyword_manager import keyword_manager


class DSLValidationError:
    """DSL验证错误"""

    def __init__(
            self,
            error_type: str,
            message: str,
            line: Optional[int] = None,
            column: Optional[int] = None,
            suggestion: Optional[str] = None):
        self.error_type = error_type
        self.message = message
        self.line = line
        self.column = column
        self.suggestion = suggestion

    def __str__(self):
        location = ""
        if self.line is not None:
            location = f"第{self.line}行"
            if self.column is not None:
                location += f"第{self.column}列"
            location += ": "

        result = f"{location}{self.error_type}: {self.message}"
        if self.suggestion:
            result += f"\n建议: {self.suggestion}"
        return result


class DSLValidator:
    """DSL格式校验器"""

    def __init__(self):
        self.errors: List[DSLValidationError] = []
        self.warnings: List[DSLValidationError] = []

    def validate(self, content: str, dsl_id: Optional[str] = None
                 ) -> Tuple[bool, List[DSLValidationError]]:
        """验证DSL内容

        Args:
            content: DSL内容
            dsl_id: DSL标识符（可选）

        Returns:
            (是否验证通过, 错误列表)
        """
        self.errors = []
        self.warnings = []

        # 基础验证
        self._validate_basic_format(content)

        # 语法验证
        ast = self._validate_syntax(content)

        # 如果语法验证通过，进行语义验证
        if ast and not self.errors:
            self._validate_semantics(ast)

        # 元数据验证
        if ast and not self.errors:
            self._validate_metadata(ast)

        # 关键字验证
        if ast and not self.errors:
            self._validate_keywords(ast)

        return len(self.errors) == 0, self.errors + self.warnings

    def _validate_basic_format(self, content: str) -> None:
        """基础格式验证"""
        if not content or not content.strip():
            self.errors.append(DSLValidationError(
                "格式错误", "DSL内容不能为空"
            ))
            return

        lines = content.split('\n')

        # 检查编码
        try:
            content.encode('utf-8')
        except UnicodeEncodeError as e:
            self.errors.append(DSLValidationError(
                "编码错误", f"DSL内容包含无效字符: {str(e)}"
            ))

        # 检查行长度
        for i, line in enumerate(lines, 1):
            if len(line) > 1000:
                self.warnings.append(DSLValidationError(
                    "格式警告", f"第{i}行过长，建议控制在1000字符以内", line=i
                ))

        # 检查嵌套层级
        max_indent = 0
        for i, line in enumerate(lines, 1):
            if line.strip():
                indent = len(line) - len(line.lstrip())
                if indent > max_indent:
                    max_indent = indent

        if max_indent > 40:  # 假设每层缩进4个空格，最多10层
            self.warnings.append(DSLValidationError(
                "格式警告", f"嵌套层级过深（{max_indent//4}层），建议简化结构"
            ))

    def _validate_syntax(self, content: str) -> Optional[Node]:
        """语法验证"""
        try:
            lexer = get_lexer()
            ast, parse_errors = parse_with_error_handling(content, lexer)

            # 如果有解析错误，添加到错误列表
            if parse_errors:
                for error in parse_errors:
                    self.errors.append(DSLValidationError(
                        "语法错误",
                        error['message'],
                        line=error['line'],
                        suggestion=self._suggest_syntax_fix(error['message'])
                    ))
                return None

            return ast

        except Exception as e:
            error_msg = str(e)
            line_num = self._extract_line_number(error_msg)

            self.errors.append(DSLValidationError(
                "语法错误",
                error_msg,
                line=line_num,
                suggestion=self._suggest_syntax_fix(error_msg)
            ))
            return None

    def _validate_semantics(self, ast: Node) -> None:
        """语义验证"""
        self._check_node_semantics(ast)

    def _check_node_semantics(self, node: Node) -> None:
        """检查节点语义"""
        if node.type == 'Assignment':
            # 检查变量名
            var_name = node.value
            if not self._is_valid_variable_name(var_name):
                self.errors.append(DSLValidationError(
                    "语义错误",
                    f"无效的变量名: {var_name}",
                    suggestion="变量名应以字母或下划线开头，只包含字母、数字、下划线或中文字符"
                ))

        elif node.type == 'ForLoop':
            # 检查循环变量名
            loop_var = node.value
            if not self._is_valid_variable_name(loop_var):
                self.errors.append(DSLValidationError(
                    "语义错误",
                    f"无效的循环变量名: {loop_var}",
                    suggestion="循环变量名应以字母或下划线开头，只包含字母、数字、下划线或中文字符"
                ))

        elif node.type == 'Expression':
            # 检查表达式中的变量引用
            if isinstance(node.value, str):
                self._validate_variable_references(node.value)

        # 递归检查子节点
        for child in node.children:
            if isinstance(child, Node):
                self._check_node_semantics(child)

    def _validate_metadata(self, ast: Node) -> None:
        """验证元数据"""
        metadata_node = None
        for child in ast.children:
            if child.type == 'Metadata':
                metadata_node = child
                break

        if not metadata_node:
            self.warnings.append(DSLValidationError(
                "元数据警告", "建议添加@name元数据以描述测试用例名称"
            ))
            return

        has_name = False
        has_description = False

        for item in metadata_node.children:
            if item.type == '@name':
                has_name = True
                if not item.value or not item.value.strip():
                    self.errors.append(DSLValidationError(
                        "元数据错误", "@name不能为空"
                    ))
            elif item.type == '@description':
                has_description = True
                if not item.value or not item.value.strip():
                    self.warnings.append(DSLValidationError(
                        "元数据警告", "@description不应为空"
                    ))
            elif item.type == '@tags':
                # 验证标签格式
                if not item.value or len(item.value) == 0:
                    self.warnings.append(DSLValidationError(
                        "元数据警告", "@tags不应为空列表"
                    ))

        if not has_name:
            self.warnings.append(DSLValidationError(
                "元数据警告", "建议添加@name元数据以描述测试用例名称"
            ))

        if not has_description:
            self.warnings.append(DSLValidationError(
                "元数据警告", "建议添加@description元数据以描述测试用例功能"
            ))

    def _validate_keywords(self, ast: Node) -> None:
        """验证关键字"""
        self._check_node_keywords(ast)

    def _check_node_keywords(self, node: Node) -> None:
        """检查节点中的关键字"""
        if node.type == 'KeywordCall':
            keyword_name = node.value
            keyword_info = keyword_manager.get_keyword_info(keyword_name)

            if not keyword_info:
                self.errors.append(DSLValidationError(
                    "关键字错误",
                    f"未注册的关键字: {keyword_name}",
                    suggestion=self._suggest_similar_keyword(keyword_name)
                ))
            else:
                # 验证参数
                self._validate_keyword_parameters(node, keyword_info)

        # 递归检查子节点
        for child in node.children:
            if isinstance(child, Node):
                self._check_node_keywords(child)

    def _validate_keyword_parameters(self, keyword_node: Node,
                                     keyword_info: Dict) -> None:
        """验证关键字参数"""
        if not keyword_node.children or not keyword_node.children[0]:
            return

        provided_params = set()
        for param in keyword_node.children[0]:
            param_name = param.value
            provided_params.add(param_name)

            # 检查参数名是否有效
            mapping = keyword_info.get('mapping', {})
            if param_name not in mapping:
                self.errors.append(DSLValidationError(
                    "参数错误",
                    f"关键字 {keyword_node.value} 不支持参数: {param_name}",
                    suggestion=f"支持的参数: {', '.join(mapping.keys())}"
                ))

        # 检查必需参数（这里简化处理，实际可能需要更复杂的逻辑）
        required_params = set()
        parameters = keyword_info.get('parameters', [])
        for param in parameters:
            if not hasattr(param, 'default') or param.default is None:
                required_params.add(param.name)

        missing_params = required_params - provided_params
        if missing_params:
            self.warnings.append(DSLValidationError(
                "参数警告",
                f"关键字 {keyword_node.value} 缺少建议参数: "
                f"{', '.join(missing_params)}"
            ))

    def _is_valid_variable_name(self, name: str) -> bool:
        """检查变量名是否有效"""
        if not name:
            return False
        # 支持中文、英文、数字、下划线，以字母或下划线开头
        pattern = r'^[a-zA-Z_\u4e00-\u9fa5][a-zA-Z0-9_\u4e00-\u9fa5]*$'
        return bool(re.match(pattern, name))

    def _validate_variable_references(self, text: str) -> None:
        """验证文本中的变量引用"""
        # 匹配 ${变量名} 格式
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, text)

        for var_ref in matches:
            # 检查变量引用格式是否正确
            if not self._is_valid_variable_reference(var_ref):
                self.errors.append(DSLValidationError(
                    "变量引用错误",
                    f"无效的变量引用格式: ${{{var_ref}}}",
                    suggestion="变量引用应为 ${变量名} 格式，支持点号访问和数组索引"
                ))

    def _is_valid_variable_reference(self, var_ref: str) -> bool:
        """检查变量引用是否有效"""
        # 支持: variable, obj.prop, arr[0], dict["key"] 等格式
        pattern = (r'^[a-zA-Z_\u4e00-\u9fa5][a-zA-Z0-9_\u4e00-\u9fa5]*'
                   r'(?:(?:\.[a-zA-Z_\u4e00-\u9fa5][a-zA-Z0-9_\u4e00-\u9fa5]*)'
                   r'|(?:\[[^\]]+\]))*$')
        return bool(re.match(pattern, var_ref))

    def _extract_line_number(self, error_msg: str) -> Optional[int]:
        """从错误消息中提取行号"""
        # 尝试匹配常见的行号模式
        patterns = [
            r'line (\d+)',
            r'第(\d+)行',
            r'在行 (\d+)',
            r'at line (\d+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, error_msg)
            if match:
                return int(match.group(1))
        return None

    def _suggest_syntax_fix(self, error_msg: str) -> Optional[str]:
        """根据错误消息建议语法修复"""
        suggestions = {
            "Syntax error": "检查语法是否正确，特别是括号、引号的匹配",
            "unexpected token": "检查是否有多余或缺失的符号",
            "Unexpected end of input": "检查是否缺少end关键字或右括号",
            "illegal character": "检查是否有非法字符，确保使用UTF-8编码"
        }

        for key, suggestion in suggestions.items():
            if key.lower() in error_msg.lower():
                return suggestion
        return None

    def _suggest_similar_keyword(self, keyword_name: str) -> Optional[str]:
        """建议相似的关键字"""
        all_keywords = list(keyword_manager._keywords.keys())

        # 简单的相似度匹配（可以使用更复杂的算法）
        similar_keywords = []
        for kw in all_keywords:
            similarity = self._calculate_similarity(
                keyword_name.lower(), kw.lower())
            if similarity > 0.6:
                similar_keywords.append(kw)

        if similar_keywords:
            return f"您是否想使用: {', '.join(similar_keywords[:3])}"
        return None

    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """计算字符串相似度（简单的Jaccard相似度）"""
        if not s1 or not s2:
            return 0.0

        set1 = set(s1)
        set2 = set(s2)
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        return intersection / union if union > 0 else 0.0


def validate_dsl(content: str, dsl_id: Optional[str] = None
                 ) -> Tuple[bool, List[DSLValidationError]]:
    """验证DSL内容的便捷函数

    Args:
        content: DSL内容
        dsl_id: DSL标识符（可选）

    Returns:
        (是否验证通过, 错误列表)
    """
    validator = DSLValidator()
    return validator.validate(content, dsl_id)


def check_dsl_syntax(content: str) -> bool:
    """快速检查DSL语法是否正确

    Args:
        content: DSL内容

    Returns:
        语法是否正确
    """
    try:
        lexer = get_lexer()
        parser = get_parser()
        parser.parse(content, lexer=lexer)
        return True
    except Exception:
        return False
