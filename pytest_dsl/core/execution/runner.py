"""Content-level execution orchestration for DSL programs."""

from typing import Any, Dict

from pytest_dsl.core.execution_tracker import get_or_create_tracker
from pytest_dsl.core.parser import Node


class DSLExecutionRunner:
    """Runs full DSL documents through parser, hooks, and tracking."""

    def __init__(self, executor):
        self.executor = executor

    def execute_from_content(self, content: str, dsl_id: str = None,
                             context: Dict[str, Any] = None) -> Any:
        executor = self.executor
        executor.current_dsl_id = dsl_id

        executor.ensure_hooks_updated()

        if executor.enable_tracking:
            executor.execution_tracker = get_or_create_tracker(dsl_id)
            executor.execution_tracker.start_execution()

        if (not content and dsl_id and executor.enable_hooks and
                hasattr(executor, 'hook_manager') and executor.hook_manager):
            content_results = executor.hook_manager.pm.hook.dsl_load_content(
                dsl_id=dsl_id)
            for result in content_results:
                if result is not None:
                    content = result
                    break

        if not content:
            raise ValueError(f"无法获取DSL内容: {dsl_id}")

        if context:
            executor.state.apply_context(context)

        if executor.enable_hooks and executor.hook_manager:
            executor.hook_manager.pm.hook.dsl_before_execution(
                dsl_id=dsl_id, context=context or {}
            )

        result = None
        exception = None

        try:
            ast = self.parse_dsl_content(content)
            result = executor.execute(ast)

        except Exception as e:
            exception = e
            if executor.enable_hooks and executor.hook_manager:
                try:
                    executor.hook_manager.pm.hook.dsl_after_execution(
                        dsl_id=dsl_id,
                        context=context or {},
                        result=result,
                        exception=exception,
                    )
                except Exception as hook_error:
                    print(f"Hook执行失败: {hook_error}")
            raise
        else:
            if executor.enable_hooks and executor.hook_manager:
                try:
                    executor.hook_manager.pm.hook.dsl_after_execution(
                        dsl_id=dsl_id,
                        context=context or {},
                        result=result,
                        exception=None,
                    )
                except Exception as hook_error:
                    print(f"Hook执行失败: {hook_error}")
        finally:
            if executor.enable_tracking and executor.execution_tracker:
                executor.execution_tracker.finish_execution()

        return result

    def parse_dsl_content(self, content: str) -> Node:
        """Parse DSL source content into an AST root node."""
        from pytest_dsl.core.parser import parse_with_error_handling
        from pytest_dsl.core.lexer import get_lexer

        lexer = get_lexer()
        ast, parse_errors = parse_with_error_handling(content, lexer)

        if parse_errors:
            error_messages = [error['message'] for error in parse_errors]
            raise Exception(f"DSL解析失败: {'; '.join(error_messages)}")

        return ast
