import allure
import csv
import os
import time
from typing import Dict, Any
from pytest_dsl.core.parser import Node
from pytest_dsl.core.execution import (
    BreakException,
    ContinueException,
    DSLExecutionError,
    ExecutionState,
    ExpressionEvaluator,
    DSLExecutionRunner,
    KeywordInvoker,
    LoopHandlers,
    NodeDispatcher,
    RemoteKeywordInvoker,
    ReturnException,
)
from pytest_dsl.core.execution_tracker import (
    ExecutionTracker
)


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
        self.state = ExecutionState()
        self.variables = self.state.variables
        self.test_context = self.state.test_context
        self.state.bind_executor(self)  # 让 test_context 能够访问到 executor

        # 设置变量提供者，实现YAML变量等外部变量源的注入
        self._setup_variable_providers()

        self.variable_replacer = self.state.variable_replacer
        self.expression_evaluator = ExpressionEvaluator(self)
        self.dispatcher = NodeDispatcher(self)
        self.runner = DSLExecutionRunner(self)
        self.keyword_invoker = KeywordInvoker(self)
        self.loop_handlers = LoopHandlers(self)
        self.remote_invoker = RemoteKeywordInvoker(self)
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

        # 设置线程本地的执行器引用，供远程关键字客户端使用
        self._set_thread_local_executor()

    def _set_thread_local_executor(self):
        """设置线程本地的执行器引用"""
        import threading
        threading.current_thread().dsl_executor = self

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
        self.state.set_current_data(data)

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
        """对表达式节点进行求值，返回表达式的值。"""
        return self.expression_evaluator.evaluate(expr_node)

    def _get_variable(self, var_name):
        """获取变量值，优先从本地变量获取，如果不存在则尝试从全局上下文获取"""
        return self.expression_evaluator.get_variable(var_name)

    def _replace_variables_in_string(self, value):
        """替换字符串中的变量引用"""
        return self.expression_evaluator.replace_variables_in_string(value)

    def _handle_remote_import(self, node):
        """处理远程关键字导入

        Args:
            node: RemoteImport节点
        """
        return self.remote_invoker.handle_import(node)

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
        teardown_node = None

        try:
            metadata = {}

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
            # 如果是语法错误，记录并抛出（让finally块执行）
            if "语法错误" in str(e):
                print(f"DSL语法错误: {str(e)}")
                raise
            # DSLExecutionError 已经是友好错误信息，由上层（CLI/调用方）负责打印，避免重复日志
            if isinstance(e, DSLExecutionError):
                raise
            # 其他错误，记录并抛出（让finally块执行）
            print(f"测试执行错误: {str(e)}")
            raise
        finally:
            # 确保teardown在任何情况下都执行
            if teardown_node:
                try:
                    self.execute(teardown_node)
                except Exception as e:
                    print(f"🚨 清理操作发生严重错误: {str(e)}")
                    allure.attach(
                        f"清理严重失败: {str(e)}",
                        name="清理严重错误",
                        attachment_type=allure.attachment_type.TEXT
                    )

            # 测试用例执行完成后清空上下文/变量
            self._clear_execution_state()

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

    def _handle_statements(self, node):
        """处理语句列表"""
        for stmt in node.children:
            if stmt is None:
                # 防御性处理，跳过空语句节点
                continue
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

                scope = self.state.set_variable(var_name, expr_value)
                if scope == "global":
                    # 记录全局变量赋值，包含行号信息
                    allure.attach(
                        f"全局变量: {var_name}\n值: {expr_value}{line_info}",
                        name="全局变量赋值",
                        attachment_type=allure.attachment_type.TEXT
                    )
                else:
                    # 记录变量赋值，包含行号信息
                    allure.attach(
                        f"变量: {var_name}\n值: {expr_value}{line_info}",
                        name="赋值详情",
                        attachment_type=allure.attachment_type.TEXT
                    )

                # 注释：移除变量变化通知，因为远程关键字执行前的实时同步已经足够
                # self._notify_remote_servers_variable_changed(var_name, expr_value)

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

    def _handle_retry(self, node):
        """处理 retry 语句块"""
        count_expr, interval_expr, until_expr, body = node.children

        # 默认间隔 1 秒（若未提供 every）
        default_interval = 1.0
        try:
            retry_count = int(self.eval_expression(count_expr))
        except Exception as e:
            raise DSLExecutionError(
                f"重试次数无效: {e}", line_number=getattr(node, 'line_number', None),
                node_type='Retry', original_exception=e)

        retry_interval = default_interval
        if interval_expr is not None:
            try:
                retry_interval = float(self.eval_expression(interval_expr))
            except Exception as e:
                raise DSLExecutionError(
                    f"重试间隔无效: {e}",
                    line_number=getattr(node, 'line_number', None),
                    node_type='Retry', original_exception=e)

        def _check_until():
            if until_expr is None:
                return True
            result = self.eval_expression(until_expr)
            return bool(result)

        last_error = None
        for attempt in range(1, retry_count + 1):
            try:
                # 执行块体
                self.execute(body)
                # 块体成功后，如果没有 until 条件，直接结束；有 until 则检查
                if _check_until():
                    return
                last_error = AssertionError("retry until 条件未满足")
            except (BreakException, ContinueException, ReturnException):
                # 保持控制流语义
                raise
            except Exception as e:
                last_error = e

            # 未成功且还有剩余次数 -> 等待后继续
            if attempt < retry_count:
                try:
                    time.sleep(max(0.0, retry_interval))
                except Exception:
                    # sleep 异常不应阻断重试流程
                    pass

        # 重试用尽仍未成功
        if last_error:
            raise last_error
        # 理论上不会到这里，但防御性处理
        raise AssertionError("retry 块未成功且未捕获错误")

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

                scope = self.state.set_variable(var_name, result)
                if scope == "global":
                    allure.attach(
                        f"全局变量: {var_name}\n值: {result}{line_info}",
                        name="关键字赋值详情",
                        attachment_type=allure.attachment_type.TEXT
                    )
                else:
                    # 记录关键字赋值，包含行号信息
                    allure.attach(
                        f"变量: {var_name}\n值: {result}{line_info}",
                        name="关键字赋值详情",
                        attachment_type=allure.attachment_type.TEXT
                    )

                # 注释：移除变量变化通知，因为远程关键字执行前的实时同步已经足够
                # self._notify_remote_servers_variable_changed(var_name, result)

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
        return self.remote_invoker.notify_variable_changed(var_name, var_value)

    def _handle_for_loop(self, node):
        """处理传统for循环（向后兼容）"""
        return self.loop_handlers.handle_for_loop(node)

    def _handle_for_range_loop(self, node):
        """处理range类型的for循环: for i in range(0, 5) do ... end"""
        return self.loop_handlers.handle_for_range_loop(node)

    def _handle_for_item_loop(self, node):
        """处理单变量遍历循环: for item in array do ... end"""
        return self.loop_handlers.handle_for_item_loop(node)

    def _handle_for_key_value_loop(self, node):
        """处理键值对遍历循环: for key, value in dict do ... end"""
        return self.loop_handlers.handle_for_key_value_loop(node)

    def _execute_keyword_call(self, node):
        """执行关键字调用"""
        return self.keyword_invoker.execute(node)

    def _prepare_keyword_params(self, node, keyword_info):
        """准备关键字调用参数"""
        return self.keyword_invoker.prepare_params(node, keyword_info)

    def _handle_teardown(self, node):
        """处理清理操作 - 强制执行所有清理关键字，即使某些失败"""
        if not node.children:
            return

        teardown_errors = []

        # teardown块只有一个子节点：Statements节点
        # 直接遍历Statements节点的所有子节点，确保即使某个语句失败也继续执行后续语句
        statements_node = node.children[0]

        # 处理不同类型的teardown块结构
        if statements_node is None:
            # 空的teardown块，什么都不做
            return
        elif hasattr(statements_node, 'type') and statements_node.type == 'Statements':
            # 正常的Statements节点，遍历所有子语句
            for stmt in statements_node.children:
                # 跳过None节点（可能由空的statements块产生）
                if stmt is None:
                    continue
                try:
                    self.execute(stmt)
                except Exception as e:
                    # 记录错误但继续执行下一个清理操作
                    error_info = {
                        'line_number': getattr(stmt, 'line_number', None),
                        'error': str(e),
                        'statement_type': getattr(stmt, 'type', 'Unknown')
                    }
                    teardown_errors.append(error_info)

                    # 记录到allure报告中
                    error_msg = f"清理操作失败 (行{error_info['line_number'] if error_info['line_number'] else '未知'}): {str(e)}"
                    allure.attach(
                        error_msg,
                        name="清理操作警告",
                        attachment_type=allure.attachment_type.TEXT
                    )
        else:
            # 其他类型的节点（如单个语句），直接执行
            try:
                self.execute(statements_node)
            except Exception as e:
                error_info = {
                    'line_number': getattr(statements_node, 'line_number', None),
                    'error': str(e),
                    'statement_type': getattr(statements_node, 'type', 'Unknown')
                }
                teardown_errors.append(error_info)

                error_msg = f"清理操作失败 (行{error_info['line_number'] if error_info['line_number'] else '未知'}): {str(e)}"
                allure.attach(
                    error_msg,
                    name="清理操作警告",
                    attachment_type=allure.attachment_type.TEXT
                )

        # 如果有清理错误，打印汇总信息但不抛出异常
        if teardown_errors:
            error_count = len(teardown_errors)
            print(f"⚠️  清理操作完成，但有 {error_count} 个操作失败:")
            for i, error in enumerate(teardown_errors, 1):
                line_info = f"行{error['line_number']}" if error['line_number'] else "未知行号"
                print(f"   {i}. [{error['statement_type']}] {line_info}: {error['error']}")
            print("📋 注意：清理操作失败不会影响测试结果，所有清理步骤都已尝试执行")

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
        return self.remote_invoker.execute_keyword_call(node)

    def _handle_assignment_remote_keyword_call(self, node):
        """处理远程关键字调用赋值

        Args:
            node: AssignmentRemoteKeywordCall节点
        """
        return self.remote_invoker.handle_assignment_keyword_call(node)

    def execute(self, node):
        """执行AST节点"""
        return self.dispatcher.execute(node)

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
            'Retry': "重试块",
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

    def ensure_hooks_updated(self):
        """确保hook系统是最新的，用于在pytest环境下检测新插件"""
        if not self.enable_hooks:
            return

        try:
            from .hook_manager import hook_manager
            from .hookable_keyword_manager import hookable_keyword_manager

            # 检查是否需要重新初始化（比如在pytest环境下新插件被加载）
            if (hasattr(self, 'hook_manager') and self.hook_manager and
                hasattr(self, 'hookable_keyword_manager') and self.hookable_keyword_manager):

                # 重新执行hook关键字注册，确保新插件的hook被调用
                try:
                    hook_manager.pm.hook.dsl_register_custom_keywords()
                except Exception as e:
                    print(f"重新执行hook关键字注册时出现警告: {e}")

        except Exception as e:
            print(f"确保hook系统更新时出现警告: {e}")

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
        return self.runner.execute_from_content(
            content,
            dsl_id=dsl_id,
            context=context,
        )

    def _parse_dsl_content(self, content: str) -> Node:
        """解析DSL内容为AST（公共方法）

        Args:
            content: DSL文本内容

        Returns:
            Node: 解析后的AST根节点

        Raises:
            Exception: 解析失败时抛出异常
        """
        return self.runner.parse_dsl_content(content)

    def _clear_execution_state(self):
        """在teardown完成后清理执行状态"""
        import os

        keep_variables = os.environ.get('PYTEST_DSL_KEEP_VARIABLES', '0') == '1'
        self.state.clear(keep_variables=keep_variables)


def read_file(filename):
    """读取 DSL 文件内容"""
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()
