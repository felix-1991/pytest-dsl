"""AST node dispatch for the DSL executor."""

from pytest_dsl.core.execution.exceptions import (
    BreakException,
    ContinueException,
    DSLExecutionError,
    ReturnException,
)


class NodeDispatcher:
    """Dispatches AST nodes to executor handler methods."""

    def __init__(self, executor):
        self.executor = executor

    def execute(self, node):
        """Execute one AST node through the owning executor."""
        executor = self.executor

        if node is None:
            raise DSLExecutionError("收到空节点，可能是解析失败或语法错误导致",
                                    line_number=None, node_type=None)

        if executor.enable_tracking and executor.execution_tracker:
            line_number = getattr(node, 'line_number', None)
            if line_number:
                description = executor._get_node_description(node)
                executor.execution_tracker.start_step(
                    line_number, node.type, description)

        handler = self._get_handler(node.type)
        if not handler:
            error_msg = f"未知的节点类型: {node.type}"
            if executor.enable_tracking and executor.execution_tracker:
                executor.execution_tracker.finish_current_step(error=error_msg)
            executor._handle_exception_with_line_info(
                Exception(error_msg), node, f"执行节点 {node.type}")

        if hasattr(node, 'line_number') and node.line_number:
            executor._node_stack.append(node)
            stack_pushed = True
        else:
            stack_pushed = False

        old_node = executor._current_node
        executor._current_node = node

        try:
            result = handler(node)
            if executor.enable_tracking and executor.execution_tracker:
                executor.execution_tracker.finish_current_step(result=result)
            return result
        except Exception as e:
            if executor.enable_tracking and executor.execution_tracker:
                error_msg = f"{type(e).__name__}: {str(e)}"
                if hasattr(node, 'line_number') and node.line_number:
                    error_msg += f" (行{node.line_number})"
                executor.execution_tracker.finish_current_step(error=error_msg)

            if isinstance(e, (BreakException, ContinueException,
                              ReturnException, DSLExecutionError)):
                raise

            if isinstance(e, AssertionError):
                if not ("行号:" in str(e) or "行" in str(e)):
                    line_info = executor._get_line_info(node)
                    if line_info:
                        enhanced_msg = f"{str(e)}{line_info}"
                        raise AssertionError(enhanced_msg) from e
                raise

            step_handled_nodes = {
                'KeywordCall', 'Assignment', 'AssignmentKeywordCall',
                'ForLoop', 'RemoteKeywordCall', 'AssignmentRemoteKeywordCall'
            }
            skip_logging = node.type in step_handled_nodes
            executor._handle_exception_with_line_info(
                e, node, f"执行{node.type}节点",
                skip_allure_logging=skip_logging)
        finally:
            executor._current_node = old_node
            if stack_pushed:
                executor._node_stack.pop()

    def _get_handler(self, node_type):
        executor = self.executor
        handlers = {
            'Start': executor._handle_start,
            'Metadata': lambda _: None,
            'Statements': executor._handle_statements,
            'Assignment': executor._handle_assignment,
            'AssignmentKeywordCall': executor._handle_assignment_keyword_call,
            'ForLoop': executor._handle_for_loop,
            'ForRangeLoop': executor._handle_for_range_loop,
            'ForItemLoop': executor._handle_for_item_loop,
            'ForKeyValueLoop': executor._handle_for_key_value_loop,
            'Retry': executor._handle_retry,
            'KeywordCall': executor._execute_keyword_call,
            'Teardown': executor._handle_teardown,
            'Return': executor._handle_return,
            'IfStatement': executor._handle_if_statement,
            'CustomKeyword': lambda _: None,
            'RemoteImport': executor._handle_remote_import,
            'RemoteKeywordCall': executor._execute_remote_keyword_call,
            'AssignmentRemoteKeywordCall': (
                executor._handle_assignment_remote_keyword_call),
            'Break': executor._handle_break,
            'Continue': executor._handle_continue,
        }
        return handlers.get(node_type)
