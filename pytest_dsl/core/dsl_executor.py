import re
import allure
import csv
import os
from typing import Dict, Any
from pytest_dsl.core.parser import Node
from pytest_dsl.core.keyword_manager import keyword_manager
from pytest_dsl.core.global_context import global_context
from pytest_dsl.core.context import TestContext
from pytest_dsl.core.variable_utils import VariableReplacer
from pytest_dsl.core.execution_tracker import (
    get_or_create_tracker, ExecutionTracker
)


class BreakException(Exception):
    """Break控制流异常"""
    pass


class ContinueException(Exception):
    """Continue控制流异常"""
    pass


class ReturnException(Exception):
    """Return控制流异常"""

    def __init__(self, return_value=None):
        self.return_value = return_value
        super().__init__(f"Return with value: {return_value}")


class DSLExecutionError(Exception):
    """DSL执行异常，包含行号信息"""

    def __init__(self, message: str, line_number: int = None,
                 node_type: str = None, original_exception: Exception = None):
        self.line_number = line_number
        self.node_type = node_type
        self.original_exception = original_exception

        # 构建详细的错误消息
        error_parts = [message]
        if line_number:
            error_parts.append(f"行号: {line_number}")
        if node_type:
            error_parts.append(f"节点类型: {node_type}")
        if original_exception:
            error_parts.append(
                f"原始异常: {type(original_exception).__name__}: "
                f"{str(original_exception)}"
            )

        super().__init__(" | ".join(error_parts))


class DSLExecutor:
    """DSL执行器，负责执行解析后的AST

    环境变量控制:
    - PYTEST_DSL_KEEP_VARIABLES=1: 执行完成后保留变量，用于单元测试中检查变量值
    - PYTEST_DSL_KEEP_VARIABLES=0: (默认) 执行完成后清空变量，用于正常DSL执行
    """

    def __init__(self, enable_hooks: bool = True,
                 enable_tracking: bool = True):
        """初始化DSL执行器

        Args:
            enable_hooks: 是否启用hook机制，默认True
            enable_tracking: 是否启用执行跟踪，默认True
        """
        self.variables = {}
        self.test_context = TestContext()
        self.test_context.executor = self  # 让 test_context 能够访问到 executor

        # 设置变量提供者，实现YAML变量等外部变量源的注入
        self._setup_variable_providers()

        self.variable_replacer = VariableReplacer(
            self.variables, self.test_context)
        self.imported_files = set()  # 跟踪已导入的文件，避免循环导入

        # Hook相关配置
        self.enable_hooks = enable_hooks
        self.current_dsl_id = None  # 当前执行的DSL标识符

        # 执行跟踪配置
        self.enable_tracking = enable_tracking
        self.execution_tracker: ExecutionTracker = None

        # 当前执行节点（用于异常处理时获取行号）
        self._current_node = None
        # 节点调用栈，用于追踪有行号信息的节点
        self._node_stack = []

        if self.enable_hooks:
            self._init_hooks()

    def _get_line_info(self, node=None):
        """获取行号信息字符串

        Args:
            node: 可选的节点，如果不提供则使用当前节点

        Returns:
            包含行号信息的字符串
        """
        target_node = node or self._current_node

        # 尝试从当前节点获取行号
        if (target_node and hasattr(target_node, 'line_number') and
                target_node.line_number):
            return f"\n行号: {target_node.line_number}"

        # 如果当前节点没有行号，从节点栈中查找最近的有行号的节点
        for stack_node in reversed(self._node_stack):
            if hasattr(stack_node, 'line_number') and stack_node.line_number:
                return f"\n行号: {stack_node.line_number}"

        # 如果当前节点没有行号，尝试从当前执行的节点获取
        if (self._current_node and
                hasattr(self._current_node, 'line_number') and
                self._current_node.line_number):
            return f"\n行号: {self._current_node.line_number}"

        return ""

    def _handle_exception_with_line_info(self, e: Exception, node=None,
                                         context_info: str = "",
                                         skip_allure_logging: bool = False):
        """统一处理异常并记录行号信息

        Args:
            e: 原始异常
            node: 可选的节点，用于获取行号
            context_info: 额外的上下文信息
            skip_allure_logging: 是否跳过Allure日志记录，避免重复记录

        Raises:
            DSLExecutionError: 包含行号信息的DSL执行异常
        """
        target_node = node or self._current_node
        line_number = None
        node_type = None

        # 尝试从目标节点获取行号
        if target_node:
            line_number = getattr(target_node, 'line_number', None)
            node_type = getattr(target_node, 'type', None)

        # 如果目标节点没有行号，从节点栈中查找最近的有行号的节点
        if not line_number:
            for stack_node in reversed(self._node_stack):
                stack_line = getattr(stack_node, 'line_number', None)
                if stack_line:
                    line_number = stack_line
                    if not node_type:
                        node_type = getattr(stack_node, 'type', None)
                    break

        # 如果还是没有行号，尝试从当前执行节点获取
        if not line_number and self._current_node:
            line_number = getattr(self._current_node, 'line_number', None)
            if not node_type:
                node_type = getattr(self._current_node, 'type', None)

        # 构建错误消息
        error_msg = str(e)
        if context_info:
            error_msg = f"{context_info}: {error_msg}"

        # 只有在没有跳过Allure日志记录时才记录到Allure
        if not skip_allure_logging:
            # 记录到Allure
            line_info = self._get_line_info(target_node)
            error_details = f"{error_msg}{line_info}"
            if context_info:
                error_details += f"\n上下文: {context_info}"

            allure.attach(
                error_details,
                name="DSL执行异常",
                attachment_type=allure.attachment_type.TEXT
            )

        # 如果原始异常已经是DSLExecutionError，不要重复封装
        if isinstance(e, DSLExecutionError):
            raise e

        # 对于控制流异常，直接重抛，不封装
        if isinstance(e, (BreakException, ContinueException, ReturnException)):
            raise e

        # 对于断言错误，保持原样但添加行号信息
        if isinstance(e, AssertionError):
            enhanced_msg = f"{str(e)}{self._get_line_info(target_node)}"
            raise AssertionError(enhanced_msg) from e

        # 其他异常封装为DSLExecutionError
        raise DSLExecutionError(
            message=error_msg,
            line_number=line_number,
            node_type=node_type,
            original_exception=e
        ) from e

    def _execute_with_error_handling(self, func, node, *args, **kwargs):
        """在错误处理包装器中执行函数

        Args:
            func: 要执行的函数
            node: 当前节点
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            函数执行结果
        """
        old_node = self._current_node
        self._current_node = node

        try:
            return func(*args, **kwargs)
        except Exception as e:
            self._handle_exception_with_line_info(
                e, node, f"执行{getattr(node, 'type', '未知节点')}")
        finally:
            self._current_node = old_node

    def set_current_data(self, data):
        """设置当前测试数据集"""
        if data:
            self.variables.update(data)
            # 同时将数据添加到测试上下文
            for key, value in data.items():
                self.test_context.set(key, value)

    def _load_test_data(self, data_source):
        """加载测试数据

        :param data_source: 数据源配置，包含 file 和 format 字段
        :return: 包含测试数据的列表
        """
        if not data_source:
            return [{}]  # 如果没有数据源，返回一个空的数据集

        file_path = data_source['file']
        format_type = data_source['format']

        if not os.path.exists(file_path):
            raise Exception(f"数据文件不存在: {file_path}")

        if format_type.lower() == 'csv':
            return self._load_csv_data(file_path)
        else:
            raise Exception(f"不支持的数据格式: {format_type}")

    def _load_csv_data(self, file_path):
        """加载CSV格式的测试数据

        :param file_path: CSV文件路径
        :return: 包含测试数据的列表
        """
        data_sets = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data_sets.append(row)
        return data_sets

    def eval_expression(self, expr_node):
        """
        对表达式节点进行求值，返回表达式的值。

        :param expr_node: AST中的表达式节点
        :return: 表达式求值后的结果
        :raises DSLExecutionError: 当遇到未定义变量或无法求值的类型时抛出异常
        """
        def _eval_expression_impl():
            if expr_node.type == 'Expression':
                value = self._eval_expression_value(expr_node.value)
                # 统一处理变量替换
                return self.variable_replacer.replace_in_value(value)
            elif expr_node.type == 'StringLiteral':
                # 字符串字面量，如果包含变量占位符则进行替换，否则直接返回
                if '${' in expr_node.value:
                    return self.variable_replacer.replace_in_string(
                        expr_node.value)
                else:
                    return expr_node.value
            elif expr_node.type == 'NumberLiteral':
                # 数字字面量，直接返回值
                return expr_node.value
            elif expr_node.type == 'VariableRef':
                # 变量引用，从变量存储中获取值
                var_name = expr_node.value
                try:
                    return self.variable_replacer.get_variable(var_name)
                except KeyError:
                    raise KeyError(f"变量 '{var_name}' 不存在")
            elif expr_node.type == 'PlaceholderRef':
                # 变量占位符 ${var}，进行变量替换
                return self.variable_replacer.replace_in_string(
                    expr_node.value)
            elif expr_node.type == 'KeywordCall':
                return self.execute(expr_node)
            elif expr_node.type == 'ListExpr':
                # 处理列表表达式
                result = []
                for item in expr_node.children:
                    item_value = self.eval_expression(item)
                    result.append(item_value)
                return result
            elif expr_node.type == 'DictExpr':
                # 处理字典表达式
                result = {}
                for item in expr_node.children:
                    # 每个item是DictItem节点，包含键和值
                    key_value = self.eval_expression(item.children[0])
                    value_value = self.eval_expression(item.children[1])
                    result[key_value] = value_value
                return result
            elif expr_node.type == 'BooleanExpr':
                # 处理布尔值表达式
                return expr_node.value
            elif expr_node.type == 'ComparisonExpr':
                # 处理比较表达式
                return self._eval_comparison_expr(expr_node)
            elif expr_node.type == 'ArithmeticExpr':
                # 处理算术表达式
                return self._eval_arithmetic_expr(expr_node)
            else:
                raise Exception(f"无法求值的表达式类型: {expr_node.type}")

        return self._execute_with_error_handling(
            _eval_expression_impl, expr_node)

    def _eval_expression_value(self, value):
        """处理表达式值的具体逻辑"""
        try:
            if isinstance(value, Node):
                return self.eval_expression(value)
            elif isinstance(value, str):
                # 定义扩展的变量引用模式，支持数组索引和字典键访问
                pattern = (
                    r'\$\{([a-zA-Z_\u4e00-\u9fa5]'
                    r'[a-zA-Z0-9_\u4e00-\u9fa5]*'
                    r'(?:(?:\.[a-zA-Z_\u4e00-\u9fa5]'
                    r'[a-zA-Z0-9_\u4e00-\u9fa5]*)'
                    r'|(?:\[[^\]]+\]))*)\}'
                )
                # 检查整个字符串是否完全匹配单一变量引用模式
                match = re.fullmatch(pattern, value)
                if match:
                    var_ref = match.group(1)
                    # 使用新的变量路径解析器
                    return self.variable_replacer._parse_variable_path(var_ref)
                elif '${' in value:
                    # 如果包含变量占位符，则替换字符串中的所有变量引用
                    return self.variable_replacer.replace_in_string(value)
                else:
                    # 对于不包含 ${} 的普通字符串，检查是否为单纯的变量名
                    # 只有当字符串是有效的变量名格式且确实存在该变量时，才当作变量处理
                    var_pattern = (r'^[a-zA-Z_\u4e00-\u9fa5]'
                                   r'[a-zA-Z0-9_\u4e00-\u9fa5]*$')
                    if (re.match(var_pattern, value) and
                            value in self.variable_replacer.local_variables):
                        return self.variable_replacer.local_variables[value]
                    else:
                        # 否则当作字符串字面量处理
                        return value
            return value
        except Exception as e:
            # 为变量解析异常添加更多上下文信息
            context_info = f"解析表达式值 '{value}'"
            self._handle_exception_with_line_info(
                e, context_info=context_info)

    def _eval_comparison_expr(self, expr_node):
        """
        对比较表达式进行求值

        :param expr_node: 比较表达式节点
        :return: 比较结果（布尔值）
        """
        operator = "未知"  # 设置默认值，避免UnboundLocalError
        try:
            left_value = self.eval_expression(expr_node.children[0])
            right_value = self.eval_expression(expr_node.children[1])
            operator = expr_node.value  # 操作符: >, <, >=, <=, ==, !=

            # 尝试类型转换
            if isinstance(left_value, str) and str(left_value).isdigit():
                left_value = int(left_value)
            if isinstance(right_value, str) and str(right_value).isdigit():
                right_value = int(right_value)

            # 根据操作符执行相应的比较操作
            if operator == '>':
                return left_value > right_value
            elif operator == '<':
                return left_value < right_value
            elif operator == '>=':
                return left_value >= right_value
            elif operator == '<=':
                return left_value <= right_value
            elif operator == '==':
                return left_value == right_value
            elif operator == '!=':
                return left_value != right_value
            else:
                raise Exception(f"未知的比较操作符: {operator}")
        except Exception as e:
            context_info = f"比较表达式求值 '{operator}'"
            self._handle_exception_with_line_info(e, expr_node, context_info)

    def _eval_arithmetic_expr(self, expr_node):
        """
        对算术表达式进行求值

        :param expr_node: 算术表达式节点
        :return: 计算结果
        """
        operator = "未知"  # 设置默认值，避免UnboundLocalError
        try:
            left_value = self.eval_expression(expr_node.children[0])
            right_value = self.eval_expression(expr_node.children[1])
            operator = expr_node.value  # 操作符: +, -, *, /, %

            # 尝试类型转换 - 如果是字符串数字则转为数字
            if (isinstance(left_value, str) and
                    str(left_value).replace('.', '', 1).isdigit()):
                left_value = float(left_value)
                # 如果是整数则转为整数
                if left_value.is_integer():
                    left_value = int(left_value)

            if (isinstance(right_value, str) and
                    str(right_value).replace('.', '', 1).isdigit()):
                right_value = float(right_value)
                # 如果是整数则转为整数
                if right_value.is_integer():
                    right_value = int(right_value)

            # 进行相应的算术运算
            if operator == '+':
                # 对于字符串，+是连接操作
                if isinstance(left_value, str) or isinstance(right_value, str):
                    return str(left_value) + str(right_value)
                return left_value + right_value
            elif operator == '-':
                return left_value - right_value
            elif operator == '*':
                # 如果其中一个是字符串，另一个是数字，则进行字符串重复
                if (isinstance(left_value, str) and
                        isinstance(right_value, (int, float))):
                    return left_value * int(right_value)
                elif (isinstance(right_value, str) and
                      isinstance(left_value, (int, float))):
                    return right_value * int(left_value)
                return left_value * right_value
            elif operator == '/':
                # 除法时检查除数是否为0
                if right_value == 0:
                    raise Exception("除法错误: 除数不能为0")
                return left_value / right_value
            elif operator == '%':
                # 模运算时检查除数是否为0
                if right_value == 0:
                    raise Exception("模运算错误: 除数不能为0")
                return left_value % right_value
            else:
                raise Exception(f"未知的算术操作符: {operator}")
        except Exception as e:
            context_info = f"算术表达式求值 '{operator}'"
            self._handle_exception_with_line_info(e, expr_node, context_info)

    def _get_variable(self, var_name):
        """获取变量值，优先从本地变量获取，如果不存在则尝试从全局上下文获取"""
        return self.variable_replacer.get_variable(var_name)

    def _replace_variables_in_string(self, value):
        """替换字符串中的变量引用"""
        return self.variable_replacer.replace_in_string(value)

    def _handle_remote_import(self, node):
        """处理远程关键字导入

        Args:
            node: RemoteImport节点
        """
        from pytest_dsl.remote.keyword_client import remote_keyword_manager

        remote_info = node.value
        url = self._replace_variables_in_string(remote_info['url'])
        alias = remote_info['alias']

        print(f"正在连接远程关键字服务器: {url}, 别名: {alias}")

        # 注册远程服务器
        success = remote_keyword_manager.register_remote_server(url, alias)

        if not success:
            print(f"无法连接到远程关键字服务器: {url}")
            raise Exception(f"无法连接到远程关键字服务器: {url}")

        print(f"已成功连接到远程关键字服务器: {url}, 别名: {alias}")

        allure.attach(
            f"已连接到远程关键字服务器: {url}\n"
            f"别名: {alias}",
            name="远程关键字导入",
            attachment_type=allure.attachment_type.TEXT
        )

    def _handle_custom_keywords_in_file(self, node):
        """处理文件中的自定义关键字定义

        Args:
            node: Start节点
        """
        if len(node.children) > 1 and node.children[1].type == 'Statements':
            statements_node = node.children[1]
            for stmt in statements_node.children:
                if stmt.type == 'CustomKeyword':
                    # 导入自定义关键字管理器
                    from pytest_dsl.core.custom_keyword_manager import (
                        custom_keyword_manager)
                    # 注册自定义关键字
                    custom_keyword_manager._register_custom_keyword(
                        stmt, "current_file")

    def _handle_start(self, node):
        """处理开始节点"""
        try:
            metadata = {}
            teardown_node = None

            # 自动导入项目中的resources目录
            self._auto_import_resources()

            # 先处理元数据和找到teardown节点
            for child in node.children:
                if child.type == 'Metadata':
                    for item in child.children:
                        metadata[item.type] = item.value
                        # 处理导入指令
                        if item.type == '@import':
                            self._handle_import(item.value)
                        # 处理远程关键字导入
                        elif item.type == 'RemoteImport':
                            self._handle_remote_import(item)
                elif child.type == 'Teardown':
                    teardown_node = child

            # 在_execute_test_iteration之前添加
            self._handle_custom_keywords_in_file(node)
            # 执行测试
            self._execute_test_iteration(metadata, node, teardown_node)

        except Exception as e:
            # 如果是断言错误，直接抛出
            if isinstance(e, AssertionError):
                raise
            # 如果是语法错误，记录并抛出
            if "语法错误" in str(e):
                print(f"DSL语法错误: {str(e)}")
                raise
            # 其他错误，记录并抛出
            print(f"测试执行错误: {str(e)}")
            raise
        finally:
            # 测试用例执行完成后清空上下文
            self.test_context.clear()

    def _auto_import_resources(self):
        """自动导入项目中的resources目录"""
        # 首先尝试通过hook获取资源列表
        if (self.enable_hooks and hasattr(self, 'hook_manager') and
                self.hook_manager):
            try:
                cases = []
                case_results = self.hook_manager.pm.hook.dsl_list_cases()
                for result in case_results:
                    if result:
                        cases.extend(result)

                # 如果hook返回了资源，导入它们
                for case in cases:
                    case_id = case.get('id') or case.get('file_path', '')
                    if case_id and case_id not in self.imported_files:
                        try:
                            print(f"通过hook自动导入资源: {case_id}")
                            self._handle_import(case_id)
                        except Exception as e:
                            print(f"通过hook自动导入资源失败: {case_id}, 错误: {str(e)}")
                            continue
            except Exception as e:
                print(f"通过hook自动导入资源时出现警告: {str(e)}")

        # 然后进行传统的文件系统自动导入
        try:
            from pytest_dsl.core.custom_keyword_manager import (
                custom_keyword_manager
            )

            # 尝试从多个可能的项目根目录位置导入resources
            possible_roots = [
                os.getcwd(),  # 当前工作目录
                os.path.dirname(os.getcwd()),  # 上级目录
            ]

            # 如果在pytest环境中，尝试获取pytest的根目录
            try:
                import pytest
                if hasattr(pytest, 'config') and pytest.config:
                    pytest_root = pytest.config.rootdir
                    if pytest_root:
                        possible_roots.insert(0, str(pytest_root))
            except Exception:
                pass

            # 尝试每个可能的根目录
            for project_root in possible_roots:
                if project_root and os.path.exists(project_root):
                    resources_dir = os.path.join(project_root, "resources")
                    if (os.path.exists(resources_dir) and
                            os.path.isdir(resources_dir)):
                        custom_keyword_manager.auto_import_resources_directory(
                            project_root)
                        break

        except Exception as e:
            # 自动导入失败不应该影响测试执行，只记录警告
            print(f"自动导入resources目录时出现警告: {str(e)}")

    def _handle_import(self, file_path):
        """处理导入指令

        Args:
            file_path: 资源文件路径
        """
        # 防止循环导入
        if file_path in self.imported_files:
            return

        try:
            # 尝试通过hook加载内容
            content = None
            if (self.enable_hooks and hasattr(self, 'hook_manager') and
                    self.hook_manager):
                content_results = (
                    self.hook_manager.pm.hook.dsl_load_content(
                        dsl_id=file_path
                    )
                )
                for result in content_results:
                    if result is not None:
                        content = result
                        break

            # 如果hook返回了内容，直接使用DSL解析方式处理
            if content is not None:
                ast = self._parse_dsl_content(content)

                # 只处理自定义关键字，不执行测试流程
                self._handle_custom_keywords_in_file(ast)
                self.imported_files.add(file_path)
            else:
                # 使用传统方式导入文件
                from pytest_dsl.core.custom_keyword_manager import (
                    custom_keyword_manager
                )
                custom_keyword_manager.load_resource_file(file_path)
                self.imported_files.add(file_path)
        except Exception as e:
            print(f"导入资源文件失败: {file_path}, 错误: {str(e)}")
            raise

    def _execute_test_iteration(self, metadata, node, teardown_node):
        """执行测试迭代"""
        try:
            # 设置 Allure 报告信息
            if '@name' in metadata:
                test_name = metadata['@name']
                allure.dynamic.title(test_name)
            if '@description' in metadata:
                description = metadata['@description']
                allure.dynamic.description(description)
            if '@tags' in metadata:
                for tag in metadata['@tags']:
                    allure.dynamic.tag(tag.value)

            # 执行所有非teardown节点
            for child in node.children:
                if child.type != 'Teardown' and child.type != 'Metadata':
                    self.execute(child)

            # 执行teardown
            if teardown_node:
                with allure.step("执行清理操作"):
                    try:
                        self.execute(teardown_node)
                    except Exception as e:
                        allure.attach(
                            f"清理失败: {str(e)}",
                            name="清理失败",
                            attachment_type=allure.attachment_type.TEXT
                        )
        finally:
            # 使用环境变量控制是否清空变量
            # 当 PYTEST_DSL_KEEP_VARIABLES=1 时，保留变量（用于单元测试）
            # 否则清空变量（用于正常DSL执行）
            import os
            keep_variables = os.environ.get(
                'PYTEST_DSL_KEEP_VARIABLES', '0') == '1'

            if not keep_variables:
                self.variables.clear()
                # 同时清空测试上下文
                self.test_context.clear()

    def _handle_statements(self, node):
        """处理语句列表"""
        for stmt in node.children:
            try:
                self.execute(stmt)
            except ReturnException as e:
                # 将return异常向上传递，不在这里处理
                raise e

    def _handle_assignment(self, node):
        """处理赋值语句"""
        step_name = f"变量赋值: {node.value}"
        line_info = self._get_line_info(node)

        with allure.step(step_name):
            try:
                var_name = node.value
                # 在求值表达式之前，确保当前节点设置正确
                old_current_node = self._current_node
                self._current_node = node
                try:
                    expr_value = self.eval_expression(node.children[0])
                finally:
                    self._current_node = old_current_node

                # 检查变量名是否以g_开头，如果是则设置为全局变量
                if var_name.startswith('g_'):
                    global_context.set_variable(var_name, expr_value)
                    # 记录全局变量赋值，包含行号信息
                    allure.attach(
                        f"全局变量: {var_name}\n值: {expr_value}{line_info}",
                        name="全局变量赋值",
                        attachment_type=allure.attachment_type.TEXT
                    )
                else:
                    # 存储在本地变量字典和测试上下文中
                    self.variable_replacer.local_variables[
                        var_name] = expr_value
                    self.test_context.set(var_name, expr_value)
                    # 记录变量赋值，包含行号信息
                    allure.attach(
                        f"变量: {var_name}\n值: {expr_value}{line_info}",
                        name="赋值详情",
                        attachment_type=allure.attachment_type.TEXT
                    )

                # 通知远程服务器变量已更新
                self._notify_remote_servers_variable_changed(
                    var_name, expr_value)

            except Exception as e:
                # 在步骤内部记录异常详情
                error_details = (f"执行Assignment节点: {str(e)}{line_info}\n"
                                 f"上下文: 执行Assignment节点")
                allure.attach(
                    error_details,
                    name="DSL执行异常",
                    attachment_type=allure.attachment_type.TEXT
                )
                # 重新抛出异常，让外层的统一异常处理机制处理
                raise

    def _handle_assignment_keyword_call(self, node):
        """处理关键字调用赋值

        Args:
            node: AssignmentKeywordCall节点
        """
        var_name = node.value
        line_info = self._get_line_info(node)

        with allure.step(f"关键字赋值: {var_name}"):
            try:
                keyword_call_node = node.children[0]
                result = self.execute(keyword_call_node)

                # 检查变量名是否以g_开头，如果是则设置为全局变量
                if var_name.startswith('g_'):
                    global_context.set_variable(var_name, result)
                    allure.attach(
                        f"全局变量: {var_name}\n值: {result}{line_info}",
                        name="关键字赋值详情",
                        attachment_type=allure.attachment_type.TEXT
                    )
                else:
                    # 存储在本地变量字典和测试上下文中
                    self.variable_replacer.local_variables[var_name] = result
                    self.test_context.set(var_name, result)
                    # 记录关键字赋值，包含行号信息
                    allure.attach(
                        f"变量: {var_name}\n值: {result}{line_info}",
                        name="关键字赋值详情",
                        attachment_type=allure.attachment_type.TEXT
                    )

                # 通知远程服务器变量已更新
                self._notify_remote_servers_variable_changed(var_name, result)

            except Exception as e:
                # 在步骤内部记录异常详情
                error_details = (f"执行AssignmentKeywordCall节点: {str(e)}"
                                 f"{line_info}\n"
                                 f"上下文: 执行AssignmentKeywordCall节点")
                allure.attach(
                    error_details,
                    name="DSL执行异常",
                    attachment_type=allure.attachment_type.TEXT
                )
                # 重新抛出异常，让外层的统一异常处理机制处理
                raise

    def _notify_remote_servers_variable_changed(self, var_name, var_value):
        """通知远程服务器变量已发生变化

        Args:
            var_name: 变量名
            var_value: 变量值
        """
        try:
            # 使用统一的序列化工具进行变量过滤
            from .serialization_utils import XMLRPCSerializer

            variables_to_filter = {var_name: var_value}
            filtered_variables = XMLRPCSerializer.filter_variables(
                variables_to_filter)

            if not filtered_variables:
                # 变量被过滤掉了（敏感变量或不可序列化）
                return

            # 导入远程关键字管理器
            from pytest_dsl.remote.keyword_client import remote_keyword_manager

            # 获取所有已连接的远程服务器客户端
            for alias, client in remote_keyword_manager.clients.items():
                try:
                    # 调用远程服务器的变量同步接口
                    result = client.server.sync_variables_from_client(
                        filtered_variables, client.api_key)

                    if result.get('status') == 'success':
                        print(f"🔄 变量 {var_name} 已同步到远程服务器 {alias}")
                    else:
                        error_msg = result.get('error', '未知错误')
                        print(f"❌ 变量 {var_name} 同步到远程服务器 {alias} "
                              f"失败: {error_msg}")

                except Exception as e:
                    print(f"❌ 通知远程服务器 {alias} 变量变化失败: {str(e)}")

        except ImportError:
            # 如果没有导入远程模块，跳过通知
            pass
        except Exception as e:
            print(f"❌ 通知远程服务器变量变化时发生错误: {str(e)}")

    def _handle_for_loop(self, node):
        """处理传统for循环（向后兼容）"""
        # 将传统的ForLoop转换为ForRangeLoop处理
        return self._handle_for_range_loop(node)

    def _handle_for_range_loop(self, node):
        """处理range类型的for循环: for i in range(0, 5) do ... end"""
        step_name = f"执行范围循环: {node.value}"
        line_info = self._get_line_info(node)

        with allure.step(step_name):
            try:
                var_name = node.value
                # 计算循环范围
                start_range = self.eval_expression(node.children[0])
                end_range = self.eval_expression(node.children[1])

                # 构造range对象
                loop_items = list(range(start_range, end_range))

                allure.attach(
                    f"循环变量: {var_name}\n循环范围: {start_range} 到 {end_range}\n循环项: {loop_items}{line_info}",
                    name="范围循环信息",
                    attachment_type=allure.attachment_type.TEXT
                )

                statements_node = node.children[2]

                for i in loop_items:
                    # 设置循环变量
                    self.variable_replacer.local_variables[var_name] = i
                    self.test_context.set(var_name, i)

                    # 通知远程服务器循环变量已更新
                    self._notify_remote_servers_variable_changed(var_name, i)

                    with allure.step(f"循环轮次: {var_name} = {i}"):
                        try:
                            self.execute(statements_node)
                        except BreakException:
                            # 遇到break语句，退出循环
                            allure.attach(
                                f"在 {var_name} = {i} 时遇到break语句，退出循环",
                                name="循环Break",
                                attachment_type=allure.attachment_type.TEXT
                            )
                            break
                        except ContinueException:
                            # 遇到continue语句，跳过本次循环
                            allure.attach(
                                f"在 {var_name} = {i} 时遇到continue语句，跳过本次循环",
                                name="循环Continue",
                                attachment_type=allure.attachment_type.TEXT
                            )
                            continue
                        except ReturnException as e:
                            # 遇到return语句，将异常向上传递
                            allure.attach(
                                f"在 {var_name} = {i} 时遇到return语句，退出函数",
                                name="循环Return",
                                attachment_type=allure.attachment_type.TEXT
                            )
                            raise e
                        except Exception as e:
                            # 在循环轮次内部记录异常详情
                            error_details = (f"循环执行异常 ({var_name} = {i}): "
                                             f"{str(e)}{line_info}\n"
                                             f"上下文: 执行ForRangeLoop节点")
                            allure.attach(
                                error_details,
                                name="DSL执行异常",
                                attachment_type=allure.attachment_type.TEXT
                            )
                            # 重新抛出异常
                            raise
            except (BreakException, ContinueException, ReturnException):
                # 这些控制流异常应该继续向上传递
                raise
            except Exception as e:
                # 在步骤内部记录异常详情
                error_details = (f"执行ForRangeLoop节点: {str(e)}{line_info}\n"
                                 f"上下文: 执行ForRangeLoop节点")
                allure.attach(
                    error_details,
                    name="DSL执行异常",
                    attachment_type=allure.attachment_type.TEXT
                )
                # 重新抛出异常，让外层的统一异常处理机制处理
                raise

    def _handle_for_item_loop(self, node):
        """处理单变量遍历循环: for item in array do ... end"""
        step_name = f"执行遍历循环: {node.value}"
        line_info = self._get_line_info(node)

        with allure.step(step_name):
            try:
                var_name = node.value
                # 获取要遍历的集合
                collection = self.eval_expression(node.children[0])

                # 确保collection是可迭代的
                if not hasattr(collection, '__iter__'):
                    raise TypeError(f"对象不可迭代: {type(collection).__name__}")

                # 将collection转换为列表以便记录
                loop_items = list(collection) if not isinstance(collection, list) else collection

                allure.attach(
                    f"循环变量: {var_name}\n遍历集合: {collection}\n集合类型: {type(collection).__name__}\n集合长度: {len(loop_items)}{line_info}",
                    name="遍历循环信息",
                    attachment_type=allure.attachment_type.TEXT
                )

                statements_node = node.children[1]

                for item in collection:
                    # 设置循环变量
                    self.variable_replacer.local_variables[var_name] = item
                    self.test_context.set(var_name, item)

                    # 通知远程服务器循环变量已更新
                    self._notify_remote_servers_variable_changed(var_name, item)

                    with allure.step(f"循环轮次: {var_name} = {item}"):
                        try:
                            self.execute(statements_node)
                        except BreakException:
                            # 遇到break语句，退出循环
                            allure.attach(
                                f"在 {var_name} = {item} 时遇到break语句，退出循环",
                                name="循环Break",
                                attachment_type=allure.attachment_type.TEXT
                            )
                            break
                        except ContinueException:
                            # 遇到continue语句，跳过本次循环
                            allure.attach(
                                f"在 {var_name} = {item} 时遇到continue语句，跳过本次循环",
                                name="循环Continue",
                                attachment_type=allure.attachment_type.TEXT
                            )
                            continue
                        except ReturnException as e:
                            # 遇到return语句，将异常向上传递
                            allure.attach(
                                f"在 {var_name} = {item} 时遇到return语句，退出函数",
                                name="循环Return",
                                attachment_type=allure.attachment_type.TEXT
                            )
                            raise e
                        except Exception as e:
                            # 在循环轮次内部记录异常详情
                            error_details = (f"循环执行异常 ({var_name} = {item}): "
                                             f"{str(e)}{line_info}\n"
                                             f"上下文: 执行ForItemLoop节点")
                            allure.attach(
                                error_details,
                                name="DSL执行异常",
                                attachment_type=allure.attachment_type.TEXT
                            )
                            # 重新抛出异常
                            raise
            except (BreakException, ContinueException, ReturnException):
                # 这些控制流异常应该继续向上传递
                raise
            except Exception as e:
                # 在步骤内部记录异常详情
                error_details = (f"执行ForItemLoop节点: {str(e)}{line_info}\n"
                                 f"上下文: 执行ForItemLoop节点")
                allure.attach(
                    error_details,
                    name="DSL执行异常",
                    attachment_type=allure.attachment_type.TEXT
                )
                # 重新抛出异常，让外层的统一异常处理机制处理
                raise

    def _handle_for_key_value_loop(self, node):
        """处理键值对遍历循环: for key, value in dict do ... end"""
        variables = node.value  # 包含 key_var 和 value_var
        key_var = variables['key_var']
        value_var = variables['value_var']
        step_name = f"执行键值对循环: {key_var}, {value_var}"
        line_info = self._get_line_info(node)

        with allure.step(step_name):
            try:
                # 获取要遍历的字典
                collection = self.eval_expression(node.children[0])

                # 确保collection是字典类型
                if not isinstance(collection, dict):
                    raise TypeError(f"键值对遍历要求字典类型，得到: {type(collection).__name__}")

                allure.attach(
                    f"键变量: {key_var}\n值变量: {value_var}\n遍历字典: {collection}\n字典长度: {len(collection)}{line_info}",
                    name="键值对循环信息",
                    attachment_type=allure.attachment_type.TEXT
                )

                statements_node = node.children[1]

                for key, value in collection.items():
                    # 设置循环变量
                    self.variable_replacer.local_variables[key_var] = key
                    self.variable_replacer.local_variables[value_var] = value
                    self.test_context.set(key_var, key)
                    self.test_context.set(value_var, value)

                    # 通知远程服务器循环变量已更新 [[memory:3307036]]
                    self._notify_remote_servers_variable_changed(key_var, key)
                    self._notify_remote_servers_variable_changed(value_var, value)

                    with allure.step(f"循环轮次: {key_var} = {key}, {value_var} = {value}"):
                        try:
                            self.execute(statements_node)
                        except BreakException:
                            # 遇到break语句，退出循环
                            allure.attach(
                                f"在 {key_var} = {key}, {value_var} = {value} 时遇到break语句，退出循环",
                                name="循环Break",
                                attachment_type=allure.attachment_type.TEXT
                            )
                            break
                        except ContinueException:
                            # 遇到continue语句，跳过本次循环
                            allure.attach(
                                f"在 {key_var} = {key}, {value_var} = {value} 时遇到continue语句，跳过本次循环",
                                name="循环Continue",
                                attachment_type=allure.attachment_type.TEXT
                            )
                            continue
                        except ReturnException as e:
                            # 遇到return语句，将异常向上传递
                            allure.attach(
                                f"在 {key_var} = {key}, {value_var} = {value} 时遇到return语句，退出函数",
                                name="循环Return",
                                attachment_type=allure.attachment_type.TEXT
                            )
                            raise e
                        except Exception as e:
                            # 在循环轮次内部记录异常详情
                            error_details = (f"循环执行异常 ({key_var} = {key}, {value_var} = {value}): "
                                             f"{str(e)}{line_info}\n"
                                             f"上下文: 执行ForKeyValueLoop节点")
                            allure.attach(
                                error_details,
                                name="DSL执行异常",
                                attachment_type=allure.attachment_type.TEXT
                            )
                            # 重新抛出异常
                            raise
            except (BreakException, ContinueException, ReturnException):
                # 这些控制流异常应该继续向上传递
                raise
            except Exception as e:
                # 在步骤内部记录异常详情
                error_details = (f"执行ForKeyValueLoop节点: {str(e)}{line_info}\n"
                                 f"上下文: 执行ForKeyValueLoop节点")
                allure.attach(
                    error_details,
                    name="DSL执行异常",
                    attachment_type=allure.attachment_type.TEXT
                )
                # 重新抛出异常，让外层的统一异常处理机制处理
                raise

    def _execute_keyword_call(self, node):
        """执行关键字调用"""
        keyword_name = node.value
        line_info = self._get_line_info(node)

        # 先检查关键字是否存在
        keyword_info = keyword_manager.get_keyword_info(keyword_name)
        if not keyword_info:
            error_msg = f"未注册的关键字: {keyword_name}"
            # 在步骤内部记录异常
            with allure.step(f"调用关键字: {keyword_name}"):
                allure.attach(
                    f"执行KeywordCall节点: 未注册的关键字: {keyword_name}"
                    f"{line_info}\n上下文: 执行KeywordCall节点",
                    name="DSL执行异常",
                    attachment_type=allure.attachment_type.TEXT
                )
            raise Exception(error_msg)

        step_name = f"调用关键字: {keyword_name}"

        with allure.step(step_name):
            try:
                # 准备参数（这里可能抛出参数解析异常）
                kwargs = self._prepare_keyword_params(node, keyword_info)

                # 传递自定义步骤名称给KeywordManager，避免重复的allure步骤嵌套
                kwargs['step_name'] = keyword_name  # 内层步骤只显示关键字名称
                # 避免KeywordManager重复记录，由DSL执行器统一记录
                kwargs['skip_logging'] = True

                result = keyword_manager.execute(keyword_name, **kwargs)

                # 执行成功后记录关键字信息，包含行号
                allure.attach(
                    f"关键字: {keyword_name}\n执行结果: 成功{line_info}",
                    name="关键字调用",
                    attachment_type=allure.attachment_type.TEXT
                )

                return result
            except Exception as e:
                # 统一在关键字调用层级记录异常，包含行号信息
                if "参数解析异常" in str(e) or "无法解析变量引用" in str(e):
                    # 参数解析异常，提取核心错误信息
                    core_error = str(e)
                    if "参数解析异常" in core_error:
                        # 提取参数名和具体错误
                        import re
                        match = re.search(
                            r'参数解析异常 \(([^)]+)\): (.+)', core_error)
                        if match:
                            param_name, detailed_error = match.groups()
                            error_details = (f"参数解析失败 ({param_name}): "
                                             f"{detailed_error}{line_info}\n"
                                             f"上下文: 执行KeywordCall节点")
                        else:
                            error_details = (f"参数解析失败: {core_error}"
                                             f"{line_info}\n"
                                             f"上下文: 执行KeywordCall节点")
                    else:
                        error_details = (f"参数解析失败: {core_error}"
                                         f"{line_info}\n"
                                         f"上下文: 执行KeywordCall节点")
                else:
                    # 其他异常
                    error_details = (f"执行KeywordCall节点: {str(e)}{line_info}\n"
                                     f"上下文: 执行KeywordCall节点")

                allure.attach(
                    error_details,
                    name="DSL执行异常",
                    attachment_type=allure.attachment_type.TEXT
                )
                # 重新抛出异常，让外层的统一异常处理机制处理
                raise

    def _prepare_keyword_params(self, node, keyword_info):
        """准备关键字调用参数"""
        mapping = keyword_info.get('mapping', {})
        kwargs = {'context': self.test_context}  # 默认传入context参数

        # 检查是否有参数列表
        if node.children[0]:
            for param in node.children[0]:
                param_name = param.value
                english_param_name = mapping.get(param_name, param_name)

                # 在子步骤中处理参数值解析，但不记录异常详情
                with allure.step(f"解析参数: {param_name}"):
                    try:
                        # 对参数值进行变量替换
                        param_value = self.eval_expression(param.children[0])
                        kwargs[english_param_name] = param_value

                        # 只记录参数解析成功的简要信息
                        allure.attach(
                            f"参数名: {param_name}\n"
                            f"参数值: {param_value}",
                            name="参数解析详情",
                            attachment_type=allure.attachment_type.TEXT
                        )
                    except Exception as e:
                        # 将异常重新包装，添加参数名信息，但不在这里记录到allure
                        raise Exception(
                            f"参数解析异常 ({param_name}): {str(e)}")

        return kwargs

    @allure.step("执行清理操作")
    def _handle_teardown(self, node):
        """处理清理操作"""
        self.execute(node.children[0])

    @allure.step("执行返回语句")
    def _handle_return(self, node):
        """处理return语句

        Args:
            node: Return节点

        Raises:
            ReturnException: 抛出异常来实现return控制流
        """
        expr_node = node.children[0]
        return_value = self.eval_expression(expr_node)
        raise ReturnException(return_value)

    @allure.step("执行break语句")
    def _handle_break(self, node):
        """处理break语句

        Args:
            node: Break节点

        Raises:
            BreakException: 抛出异常来实现break控制流
        """
        raise BreakException()

    @allure.step("执行continue语句")
    def _handle_continue(self, node):
        """处理continue语句

        Args:
            node: Continue节点

        Raises:
            ContinueException: 抛出异常来实现continue控制流
        """
        raise ContinueException()

    @allure.step("执行条件语句")
    def _handle_if_statement(self, node):
        """处理if-elif-else语句

        Args:
            node: IfStatement节点，包含条件表达式、if分支、可选的elif分支和可选的else分支
        """
        # 首先检查if条件
        condition = self.eval_expression(node.children[0])

        if condition:
            # 执行if分支
            with allure.step("执行if分支"):
                self.execute(node.children[1])
                return

        # 如果if条件为假，检查elif分支
        for i in range(2, len(node.children)):
            child = node.children[i]

            # 如果是ElifClause节点
            if hasattr(child, 'type') and child.type == 'ElifClause':
                elif_condition = self.eval_expression(child.children[0])
                if elif_condition:
                    with allure.step(f"执行elif分支 {i - 1}"):
                        self.execute(child.children[1])
                        return

            # 如果是普通的statements节点（else分支）
            elif not hasattr(child, 'type') or child.type == 'Statements':
                # 这是else分支，只有在所有前面的条件都为假时才执行
                with allure.step("执行else分支"):
                    self.execute(child)
                    return

        # 如果所有条件都为假且没有else分支，则不执行任何操作
        return None

    def _execute_remote_keyword_call(self, node):
        """执行远程关键字调用

        Args:
            node: RemoteKeywordCall节点

        Returns:
            执行结果
        """
        from pytest_dsl.remote.keyword_client import remote_keyword_manager

        call_info = node.value
        alias = call_info['alias']
        keyword_name = call_info['keyword']
        line_info = self._get_line_info(node)

        with allure.step(f"执行远程关键字: {alias}|{keyword_name}"):
            try:
                # 准备参数
                params = []
                if node.children and node.children[0]:
                    params = node.children[0]

                kwargs = {}
                for param in params:
                    param_name = param.value
                    param_value = self.eval_expression(param.children[0])
                    kwargs[param_name] = param_value

                # 添加测试上下文
                kwargs['context'] = self.test_context

                # 执行远程关键字
                result = remote_keyword_manager.execute_remote_keyword(
                    alias, keyword_name, **kwargs)
                allure.attach(
                    f"远程关键字参数: {kwargs}\n"
                    f"远程关键字结果: {result}{line_info}",
                    name="远程关键字执行详情",
                    attachment_type=allure.attachment_type.TEXT
                )
                return result
            except Exception as e:
                # 在步骤内部记录异常详情
                error_details = (f"执行RemoteKeywordCall节点: {str(e)}"
                                 f"{line_info}\n上下文: 执行RemoteKeywordCall节点")
                allure.attach(
                    error_details,
                    name="DSL执行异常",
                    attachment_type=allure.attachment_type.TEXT
                )
                # 重新抛出异常，让外层的统一异常处理机制处理
                raise

    def _handle_assignment_remote_keyword_call(self, node):
        """处理远程关键字调用赋值

        Args:
            node: AssignmentRemoteKeywordCall节点
        """
        var_name = node.value
        line_info = self._get_line_info(node)

        with allure.step(f"远程关键字赋值: {var_name}"):
            try:
                remote_keyword_call_node = node.children[0]
                result = self.execute(remote_keyword_call_node)

                if result is not None:
                    # 注意：远程关键字客户端已经处理了新格式的返回值，
                    # 这里接收到的result应该已经是主要返回值，而不是完整的字典格式
                    # 但为了保险起见，我们仍然检查是否为新格式
                    if isinstance(result, dict) and 'result' in result:
                        # 如果仍然是新格式（可能是嵌套的远程调用），提取主要返回值
                        main_result = result['result']

                        # 处理captures字段中的变量
                        captures = result.get('captures', {})
                        for capture_var, capture_value in captures.items():
                            if capture_var.startswith('g_'):
                                global_context.set_variable(
                                    capture_var, capture_value)
                            else:
                                self.variable_replacer.local_variables[
                                    capture_var] = capture_value
                                self.test_context.set(
                                    capture_var, capture_value)

                        # 将主要结果赋值给指定变量
                        actual_result = main_result
                    else:
                        # 传统格式，直接使用结果
                        actual_result = result

                    # 检查变量名是否以g_开头，如果是则设置为全局变量
                    if var_name.startswith('g_'):
                        global_context.set_variable(var_name, actual_result)
                        allure.attach(
                            f"全局变量: {var_name}\n值: {actual_result}{line_info}",
                            name="远程关键字赋值",
                            attachment_type=allure.attachment_type.TEXT
                        )
                    else:
                        # 存储在本地变量字典和测试上下文中
                        self.variable_replacer.local_variables[
                            var_name] = actual_result
                        self.test_context.set(var_name, actual_result)
                        allure.attach(
                            f"变量: {var_name}\n值: {actual_result}{line_info}",
                            name="远程关键字赋值",
                            attachment_type=allure.attachment_type.TEXT
                        )

                    # 通知远程服务器变量已更新
                    self._notify_remote_servers_variable_changed(
                        var_name, actual_result)

                    # 同时处理captures中的变量同步
                    if isinstance(result, dict) and 'captures' in result:
                        captures = result.get('captures', {})
                        for capture_var, capture_value in captures.items():
                            # 通知远程服务器捕获的变量也已更新
                            self._notify_remote_servers_variable_changed(
                                capture_var, capture_value)
                else:
                    error_msg = "远程关键字没有返回结果"
                    raise Exception(error_msg)
            except Exception as e:
                # 在步骤内部记录异常详情
                error_details = (f"执行AssignmentRemoteKeywordCall节点: {str(e)}"
                                 f"{line_info}\n"
                                 f"上下文: 执行AssignmentRemoteKeywordCall节点")
                allure.attach(
                    error_details,
                    name="DSL执行异常",
                    attachment_type=allure.attachment_type.TEXT
                )
                # 重新抛出异常，让外层的统一异常处理机制处理
                raise

    def execute(self, node):
        """执行AST节点"""
        # 执行跟踪
        if self.enable_tracking and self.execution_tracker:
            line_number = getattr(node, 'line_number', None)
            if line_number:
                description = self._get_node_description(node)
                self.execution_tracker.start_step(
                    line_number, node.type, description)

        handlers = {
            'Start': self._handle_start,
            'Metadata': lambda _: None,
            'Statements': self._handle_statements,
            'Assignment': self._handle_assignment,
            'AssignmentKeywordCall': self._handle_assignment_keyword_call,
            'ForLoop': self._handle_for_loop,  # 向后兼容
            'ForRangeLoop': self._handle_for_range_loop,
            'ForItemLoop': self._handle_for_item_loop,
            'ForKeyValueLoop': self._handle_for_key_value_loop,
            'KeywordCall': self._execute_keyword_call,
            'Teardown': self._handle_teardown,
            'Return': self._handle_return,
            'IfStatement': self._handle_if_statement,
            'CustomKeyword': lambda _: None,  # 添加对CustomKeyword节点的处理，只需注册不需执行
            'RemoteImport': self._handle_remote_import,
            'RemoteKeywordCall': self._execute_remote_keyword_call,
            'AssignmentRemoteKeywordCall': (
                self._handle_assignment_remote_keyword_call),
            'Break': self._handle_break,
            'Continue': self._handle_continue
        }

        handler = handlers.get(node.type)
        if not handler:
            error_msg = f"未知的节点类型: {node.type}"
            if self.enable_tracking and self.execution_tracker:
                self.execution_tracker.finish_current_step(error=error_msg)
            # 使用统一的异常处理机制
            self._handle_exception_with_line_info(
                Exception(error_msg), node, f"执行节点 {node.type}")

        # 管理节点栈 - 将有行号的节点推入栈
        if hasattr(node, 'line_number') and node.line_number:
            self._node_stack.append(node)
            stack_pushed = True
        else:
            stack_pushed = False

        # 设置当前节点
        old_node = self._current_node
        self._current_node = node

        try:
            result = handler(node)
            # 执行成功
            if self.enable_tracking and self.execution_tracker:
                self.execution_tracker.finish_current_step(result=result)
            return result
        except Exception as e:
            # 执行失败
            if self.enable_tracking and self.execution_tracker:
                error_msg = f"{type(e).__name__}: {str(e)}"
                if hasattr(node, 'line_number') and node.line_number:
                    error_msg += f" (行{node.line_number})"
                self.execution_tracker.finish_current_step(error=error_msg)

            # 如果是控制流异常或已经是DSLExecutionError，直接重抛
            if isinstance(e, (BreakException, ContinueException,
                              ReturnException, DSLExecutionError)):
                raise

            # 如果是断言异常，保持原样但可能添加行号信息
            if isinstance(e, AssertionError):
                # 检查是否已经包含行号信息
                if not ("行号:" in str(e) or "行" in str(e)):
                    line_info = self._get_line_info(node)
                    if line_info:
                        enhanced_msg = f"{str(e)}{line_info}"
                        raise AssertionError(enhanced_msg) from e
                raise

            # 其他异常使用统一处理机制
            # 对于这些节点类型，异常已经在步骤中记录过了，跳过重复记录
            step_handled_nodes = {
                'KeywordCall', 'Assignment', 'AssignmentKeywordCall',
                'ForLoop', 'RemoteKeywordCall', 'AssignmentRemoteKeywordCall'
            }
            skip_logging = node.type in step_handled_nodes
            self._handle_exception_with_line_info(
                e, node, f"执行{node.type}节点", skip_allure_logging=skip_logging)
        finally:
            # 恢复之前的节点
            self._current_node = old_node
            # 从栈中弹出节点
            if stack_pushed:
                self._node_stack.pop()

    def _get_remote_keyword_description(self, node):
        """获取远程关键字调用的描述"""
        if isinstance(getattr(node, 'value', None), dict):
            keyword = node.value.get('keyword', '')
            return f"调用远程关键字: {keyword}"
        return "调用远程关键字"

    def _get_node_description(self, node):
        """获取节点的描述信息"""
        descriptions = {
            'Assignment': f"变量赋值: {getattr(node, 'value', '')}",
            'AssignmentKeywordCall': f"关键字赋值: {getattr(node, 'value', '')}",
            'AssignmentRemoteKeywordCall': (
                f"远程关键字赋值: {getattr(node, 'value', '')}"),
            'KeywordCall': f"调用关键字: {getattr(node, 'value', '')}",
            'RemoteKeywordCall': self._get_remote_keyword_description(node),
            'ForLoop': f"For循环: {getattr(node, 'value', '')}",
            'IfStatement': "条件分支",
            'Return': "返回语句",
            'Break': "Break语句",
            'Continue': "Continue语句",
            'Teardown': "清理操作",
            'Start': "开始执行",
            'Statements': "语句块"
        }

        return descriptions.get(node.type, f"执行{node.type}")

    def __repr__(self):
        """返回DSL执行器的字符串表示"""
        return (f"DSLExecutor(variables={len(self.variables)}, "
                f"hooks_enabled={self.enable_hooks}, "
                f"tracking_enabled={self.enable_tracking})")

    def _setup_variable_providers(self):
        """设置变量提供者，将外部变量源注入到TestContext中"""
        try:
            from .variable_providers import (
                setup_context_with_default_providers
            )
            setup_context_with_default_providers(self.test_context)

            # 同步常用变量到context中，提高访问性能
            self.test_context.sync_variables_from_external_sources()
        except ImportError as e:
            # 如果导入失败，记录警告但不影响正常功能
            print(f"警告：无法设置变量提供者: {e}")

    def _init_hooks(self):
        """初始化hook机制"""
        try:
            from .hook_manager import hook_manager
            from .hookable_keyword_manager import hookable_keyword_manager

            # 初始化Hook管理器
            hook_manager.initialize()

            # 初始化Hookable关键字管理器
            hookable_keyword_manager.initialize()

            # 调用hook注册自定义关键字
            hook_manager.pm.hook.dsl_register_custom_keywords()

            self.hook_manager = hook_manager
            self.hookable_keyword_manager = hookable_keyword_manager

        except ImportError:
            # 如果没有安装pluggy，禁用hook
            self.enable_hooks = False
            self.hook_manager = None
            self.hookable_keyword_manager = None

    def execute_from_content(self, content: str, dsl_id: str = None,
                             context: Dict[str, Any] = None) -> Any:
        """从内容执行DSL，支持hook扩展

        Args:
            content: DSL内容，如果为空字符串将尝试通过hook加载
            dsl_id: DSL标识符（可选）
            context: 执行上下文（可选）

        Returns:
            执行结果
        """
        self.current_dsl_id = dsl_id

        # 初始化执行跟踪器
        if self.enable_tracking:
            self.execution_tracker = get_or_create_tracker(dsl_id)
            self.execution_tracker.start_execution()

        # 如果content为空且有dsl_id，尝试通过hook加载内容
        if (not content and dsl_id and self.enable_hooks and
                hasattr(self, 'hook_manager') and self.hook_manager):
            content_results = self.hook_manager.pm.hook.dsl_load_content(
                dsl_id=dsl_id)
            for result in content_results:
                if result is not None:
                    content = result
                    break

        if not content:
            raise ValueError(f"无法获取DSL内容: {dsl_id}")

        # 应用执行上下文
        if context:
            self.variables.update(context)
            for key, value in context.items():
                self.test_context.set(key, value)
            self.variable_replacer = VariableReplacer(
                self.variables, self.test_context
            )

        # 执行前hook
        if self.enable_hooks and self.hook_manager:
            self.hook_manager.pm.hook.dsl_before_execution(
                dsl_id=dsl_id, context=context or {}
            )

        result = None
        exception = None

        try:
            # 解析并执行
            ast = self._parse_dsl_content(content)
            result = self.execute(ast)

        except Exception as e:
            exception = e
            # 执行后hook（在异常情况下）
            if self.enable_hooks and self.hook_manager:
                try:
                    self.hook_manager.pm.hook.dsl_after_execution(
                        dsl_id=dsl_id,
                        context=context or {},
                        result=result,
                        exception=exception
                    )
                except Exception as hook_error:
                    print(f"Hook执行失败: {hook_error}")
            raise
        else:
            # 执行后hook（在成功情况下）
            if self.enable_hooks and self.hook_manager:
                try:
                    self.hook_manager.pm.hook.dsl_after_execution(
                        dsl_id=dsl_id,
                        context=context or {},
                        result=result,
                        exception=None
                    )
                except Exception as hook_error:
                    print(f"Hook执行失败: {hook_error}")
        finally:
            # 完成执行跟踪
            if self.enable_tracking and self.execution_tracker:
                self.execution_tracker.finish_execution()

        return result

    def _parse_dsl_content(self, content: str) -> Node:
        """解析DSL内容为AST（公共方法）

        Args:
            content: DSL文本内容

        Returns:
            Node: 解析后的AST根节点

        Raises:
            Exception: 解析失败时抛出异常
        """
        from pytest_dsl.core.parser import parse_with_error_handling
        from pytest_dsl.core.lexer import get_lexer

        lexer = get_lexer()
        ast, parse_errors = parse_with_error_handling(content, lexer)

        if parse_errors:
            # 如果有解析错误，抛出异常
            error_messages = [error['message'] for error in parse_errors]
            raise Exception(f"DSL解析失败: {'; '.join(error_messages)}")

        return ast


def read_file(filename):
    """读取 DSL 文件内容"""
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()
