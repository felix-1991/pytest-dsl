from pytest_dsl.core.dsl_executor import DSLExecutionError, DSLExecutor
from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import parse_expression_fragment


def test_execution_exceptions_are_exported_from_runtime_module():
    from pytest_dsl.core.execution.exceptions import (
        BreakException,
        ContinueException,
        DSLExecutionError as RuntimeDSLExecutionError,
        ReturnException,
    )
    from pytest_dsl.core.dsl_executor import (
        BreakException as ExecutorBreakException,
        ContinueException as ExecutorContinueException,
        ReturnException as ExecutorReturnException,
    )

    assert RuntimeDSLExecutionError is DSLExecutionError
    assert BreakException is ExecutorBreakException
    assert ContinueException is ExecutorContinueException
    assert ReturnException is ExecutorReturnException


def test_execution_state_sets_local_variables_and_context():
    from pytest_dsl.core.execution.state import ExecutionState

    state = ExecutionState()

    state.set_variable("name", "alice")

    assert state.variables["name"] == "alice"
    assert state.test_context.get("name") == "alice"
    assert state.variable_replacer.local_variables is state.variables


def test_executor_uses_expression_evaluator_component():
    from pytest_dsl.core.execution.expression import ExpressionEvaluator

    expr, errors = parse_expression_fragment("count + 1", lexer=get_lexer())
    assert errors == []

    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)
    executor.state.set_variable("count", 2)

    assert isinstance(executor.expression_evaluator, ExpressionEvaluator)
    assert executor.eval_expression(expr) == 3


def test_executor_delegates_node_execution_to_dispatcher():
    from pytest_dsl.core.execution.dispatcher import NodeDispatcher

    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)

    assert isinstance(executor.dispatcher, NodeDispatcher)


def test_executor_delegates_content_execution_to_runner():
    from pytest_dsl.core.execution.runner import DSLExecutionRunner

    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)

    assert isinstance(executor.runner, DSLExecutionRunner)


def test_executor_delegates_local_keyword_calls_to_invoker():
    from pytest_dsl.core.execution.keyword_invoker import KeywordInvoker

    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)

    assert isinstance(executor.keyword_invoker, KeywordInvoker)


def test_executor_delegates_loop_nodes_to_loop_handlers():
    from pytest_dsl.core.execution.loops import LoopHandlers

    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)

    assert isinstance(executor.loop_handlers, LoopHandlers)


def test_executor_delegates_remote_keyword_calls_to_invoker():
    from pytest_dsl.core.execution.remote_invoker import RemoteKeywordInvoker

    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)

    assert isinstance(executor.remote_invoker, RemoteKeywordInvoker)
