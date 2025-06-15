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
        self.variable_replacer = VariableReplacer(
            self.variables, self.test_context)
        self.imported_files = set()  # 跟踪已导入的文件，避免循环导入

        # Hook相关配置
        self.enable_hooks = enable_hooks
        self.current_dsl_id = None  # 当前执行的DSL标识符

        # 执行跟踪配置
        self.enable_tracking = enable_tracking
        self.execution_tracker: ExecutionTracker = None

        if self.enable_hooks:
            self._init_hooks()

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
        :raises Exception: 当遇到未定义变量或无法求值的类型时抛出异常
        """
        if expr_node.type == 'Expression':
            value = self._eval_expression_value(expr_node.value)
            # 统一处理变量替换
            return self.variable_replacer.replace_in_value(value)
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

    def _eval_expression_value(self, value):
        """处理表达式值的具体逻辑"""
        if isinstance(value, Node):
            return self.eval_expression(value)
        elif isinstance(value, str):
            # 如果是ID类型的变量名
            if value in self.variable_replacer.local_variables:
                return self.variable_replacer.local_variables[value]

            # 定义扩展的变量引用模式，支持数组索引和字典键访问
            pattern = (
                r'\$\{([a-zA-Z_\u4e00-\u9fa5][a-zA-Z0-9_\u4e00-\u9fa5]*'
                r'(?:(?:\.[a-zA-Z_\u4e00-\u9fa5][a-zA-Z0-9_\u4e00-\u9fa5]*)'
                r'|(?:\[[^\]]+\]))*)\}'
            )
            # 检查整个字符串是否完全匹配单一变量引用模式
            match = re.fullmatch(pattern, value)
            if match:
                var_ref = match.group(1)
                # 使用新的变量路径解析器
                return self.variable_replacer._parse_variable_path(var_ref)
            else:
                # 如果不是单一变量，则替换字符串中的所有变量引用
                return self.variable_replacer.replace_in_string(value)
        return value

    def _eval_comparison_expr(self, expr_node):
        """
        对比较表达式进行求值

        :param expr_node: 比较表达式节点
        :return: 比较结果（布尔值）
        """
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

    def _eval_arithmetic_expr(self, expr_node):
        """
        对算术表达式进行求值

        :param expr_node: 算术表达式节点
        :return: 计算结果
        """
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
            # 清空上下文，确保每个测试用例都有一个新的上下文
            self.test_context.clear()
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
        line_info = (f"\n行号: {node.line_number}"
                     if hasattr(node, 'line_number') and node.line_number
                     else "")

        with allure.step(step_name):
            try:
                var_name = node.value
                expr_value = self.eval_expression(node.children[0])

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
            except Exception as e:
                # 记录赋值失败，包含行号信息
                allure.attach(
                    f"变量: {var_name}\n错误: {str(e)}{line_info}",
                    name="赋值失败",
                    attachment_type=allure.attachment_type.TEXT
                )
                raise

    def _handle_assignment_keyword_call(self, node):
        """处理关键字调用赋值"""
        step_name = f"关键字调用赋值: {node.value}"
        line_info = (f"\n行号: {node.line_number}"
                     if hasattr(node, 'line_number') and node.line_number
                     else "")

        with allure.step(step_name):
            try:
                var_name = node.value
                keyword_call_node = node.children[0]
                result = self.execute(keyword_call_node)

                if result is not None:
                    # 处理新的统一返回格式（支持远程关键字模式）
                    if isinstance(result, dict) and 'result' in result:
                        # 提取主要返回值
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
                            f"全局变量: {var_name}\n值: {actual_result}"
                            f"{line_info}",
                            name="关键字调用赋值",
                            attachment_type=allure.attachment_type.TEXT
                        )
                    else:
                        # 存储在本地变量字典和测试上下文中
                        self.variable_replacer.local_variables[
                            var_name] = actual_result
                        self.test_context.set(var_name, actual_result)
                        allure.attach(
                            f"变量: {var_name}\n值: {actual_result}"
                            f"{line_info}",
                            name="关键字调用赋值",
                            attachment_type=allure.attachment_type.TEXT
                        )
                else:
                    error_msg = f"关键字 {keyword_call_node.value} 没有返回结果"
                    allure.attach(
                        f"变量: {var_name}\n错误: {error_msg}{line_info}",
                        name="关键字调用赋值失败",
                        attachment_type=allure.attachment_type.TEXT
                    )
                    raise Exception(error_msg)
            except Exception as e:
                # 如果异常不是我们刚才抛出的，记录异常信息
                if "没有返回结果" not in str(e):
                    allure.attach(
                        f"变量: {var_name}\n错误: {str(e)}{line_info}",
                        name="关键字调用赋值失败",
                        attachment_type=allure.attachment_type.TEXT
                    )
                raise

    def _handle_for_loop(self, node):
        """处理for循环"""
        step_name = f"For循环: {node.value}"
        line_info = (f"\n行号: {node.line_number}"
                     if hasattr(node, 'line_number') and node.line_number
                     else "")

        with allure.step(step_name):
            try:
                var_name = node.value
                start = self.eval_expression(node.children[0])
                end = self.eval_expression(node.children[1])

                # 记录循环信息，包含行号
                allure.attach(
                    f"循环变量: {var_name}\n范围: {start} 到 {end}{line_info}",
                    name="For循环",
                    attachment_type=allure.attachment_type.TEXT
                )
            except Exception as e:
                # 记录循环初始化失败
                allure.attach(
                    f"循环变量: {var_name}\n错误: {str(e)}{line_info}",
                    name="For循环初始化失败",
                    attachment_type=allure.attachment_type.TEXT
                )
                raise

            for i in range(int(start), int(end)):
                # 存储在本地变量字典和测试上下文中
                self.variable_replacer.local_variables[var_name] = i
                self.test_context.set(var_name, i)
                with allure.step(f"循环轮次: {var_name} = {i}"):
                    try:
                        self.execute(node.children[2])
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

    def _execute_keyword_call(self, node):
        """执行关键字调用"""
        keyword_name = node.value
        line_info = (f"\n行号: {node.line_number}"
                     if hasattr(node, 'line_number') and node.line_number
                     else "")

        # 先检查关键字是否存在
        keyword_info = keyword_manager.get_keyword_info(keyword_name)
        if not keyword_info:
            error_msg = f"未注册的关键字: {keyword_name}"
            allure.attach(
                f"关键字: {keyword_name}\n错误: {error_msg}{line_info}",
                name="关键字调用失败",
                attachment_type=allure.attachment_type.TEXT
            )
            raise Exception(error_msg)

        kwargs = self._prepare_keyword_params(node, keyword_info)
        step_name = f"调用关键字: {keyword_name}"

        with allure.step(step_name):
            try:
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
                # 记录关键字执行失败，包含行号信息
                allure.attach(
                    f"关键字: {keyword_name}\n错误: {str(e)}{line_info}",
                    name="关键字调用失败",
                    attachment_type=allure.attachment_type.TEXT
                )
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
                # 对参数值进行变量替换
                param_value = self.eval_expression(param.children[0])
                kwargs[english_param_name] = param_value

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
                    with allure.step(f"执行elif分支 {i-1}"):
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
        line_info = (f"\n行号: {node.line_number}"
                     if hasattr(node, 'line_number') and node.line_number
                     else "")

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

        with allure.step(f"执行远程关键字: {alias}|{keyword_name}"):
            try:
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
                # 记录错误并重新抛出
                allure.attach(
                    f"远程关键字执行失败: {str(e)}{line_info}",
                    name="远程关键字错误",
                    attachment_type=allure.attachment_type.TEXT
                )
                raise

    def _handle_assignment_remote_keyword_call(self, node):
        """处理远程关键字调用赋值

        Args:
            node: AssignmentRemoteKeywordCall节点
        """
        var_name = node.value
        line_info = (f"\n行号: {node.line_number}"
                     if hasattr(node, 'line_number') and node.line_number
                     else "")

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
                            self.test_context.set(capture_var, capture_value)

                    # 将主要结果赋值给指定变量
                    actual_result = main_result
                else:
                    # 传统格式或已经处理过的格式，直接使用结果
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
            else:
                error_msg = "远程关键字没有返回结果"
                allure.attach(
                    f"变量: {var_name}\n错误: {error_msg}{line_info}",
                    name="远程关键字赋值失败",
                    attachment_type=allure.attachment_type.TEXT
                )
                raise Exception(error_msg)
        except Exception as e:
            # 如果异常不是我们刚才抛出的，记录异常信息
            if "没有返回结果" not in str(e):
                allure.attach(
                    f"变量: {var_name}\n错误: {str(e)}{line_info}",
                    name="远程关键字赋值失败",
                    attachment_type=allure.attachment_type.TEXT
                )
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
            'ForLoop': self._handle_for_loop,
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
            raise Exception(error_msg)

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
            raise

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

    def _init_hooks(self):
        """初始化hook机制"""
        try:
            from .hook_manager import hook_manager
            hook_manager.initialize()
            # 调用hook注册自定义关键字
            hook_manager.pm.hook.dsl_register_custom_keywords()
            self.hook_manager = hook_manager
        except ImportError:
            # 如果没有安装pluggy，禁用hook
            self.enable_hooks = False
            self.hook_manager = None

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
