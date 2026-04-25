import pytest

from pytest_dsl.core.dsl_executor import DSLExecutor
from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import parse_expression_fragment, parse_with_error_handling


def _execute_dsl(dsl: str, monkeypatch):
    ast, errors = parse_with_error_handling(dsl, lexer=get_lexer())
    assert errors == []
    assert ast is not None

    monkeypatch.setenv("PYTEST_DSL_KEEP_VARIABLES", "1")
    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)
    executor.execute(ast)
    return executor


def _eval_expr(text: str, **variables):
    expr, errors = parse_expression_fragment(text, lexer=get_lexer())
    assert errors == []

    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)
    executor.variable_replacer.local_variables.update(variables)
    for name, value in variables.items():
        executor.test_context.set(name, value)

    return executor.eval_expression(expr)


def test_logical_expressions_short_circuit_missing_variables():
    assert _eval_expr("False and missing_value") is False
    assert _eval_expr("True or missing_value") is True


def test_if_elif_else_executes_only_first_matching_branch(monkeypatch):
    executor = _execute_dsl(
        '''
score = 85
branch = "unset"

if score >= 90 do
    branch = "excellent"
elif score >= 80 do
    branch = "good"
elif score >= 60 do
    branch = "pass"
else
    branch = "fail"
end
''',
        monkeypatch,
    )

    assert executor.variable_replacer.local_variables["branch"] == "good"


def test_for_range_loop_honors_continue_and_break(monkeypatch):
    executor = _execute_dsl(
        '''
total = 0
visited = ""

for i in range(1, 6) do
    if i == 2 do
        continue
    end
    if i == 5 do
        break
    end
    total = total + i
    visited = visited + i + ","
end
''',
        monkeypatch,
    )

    variables = executor.variable_replacer.local_variables
    assert variables["total"] == 8
    assert variables["visited"] == "1,3,4,"


def test_for_item_and_key_value_loops_evaluate_runtime_collections(monkeypatch):
    executor = _execute_dsl(
        '''
items = ["a", "b", "c"]
joined = ""

for item in items do
    joined = joined + item
end

mapping = {"x": 1, "y": 2}
pairs = ""

for key, value in mapping do
    pairs = pairs + key + ":" + value + ";"
end
''',
        monkeypatch,
    )

    variables = executor.variable_replacer.local_variables
    assert variables["joined"] == "abc"
    assert variables["pairs"] == "x:1;y:2;"


def test_retry_repeats_until_condition_becomes_true(monkeypatch):
    executor = _execute_dsl(
        '''
attempts = 0

retry 5 times every 0 until attempts == 3 do
    attempts = attempts + 1
end
''',
        monkeypatch,
    )

    assert executor.variable_replacer.local_variables["attempts"] == 3


def test_retry_raises_after_exhausting_until_condition(monkeypatch):
    ast, errors = parse_with_error_handling(
        '''
attempts = 0

retry 2 times every 0 until attempts == 3 do
    attempts = attempts + 1
end
''',
        lexer=get_lexer(),
    )
    assert errors == []

    monkeypatch.setenv("PYTEST_DSL_KEEP_VARIABLES", "1")
    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)

    with pytest.raises(AssertionError, match="retry until 条件未满足"):
        executor.execute(ast)

    assert executor.variable_replacer.local_variables["attempts"] == 2


def test_teardown_runs_after_main_statement_failure(monkeypatch):
    ast, errors = parse_with_error_handling(
        '''
started = True
[不存在的关键字]

teardown do
    cleanup = "done"
end
''',
        lexer=get_lexer(),
    )
    assert errors == []

    monkeypatch.setenv("PYTEST_DSL_KEEP_VARIABLES", "1")
    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)

    with pytest.raises(Exception, match="未注册的关键字"):
        executor.execute(ast)

    variables = executor.variable_replacer.local_variables
    assert variables["started"] is True
    assert variables["cleanup"] == "done"


def test_custom_keyword_defaults_overrides_and_return_values(monkeypatch):
    executor = _execute_dsl(
        '''
function format_user(name="guest", count=1) do
    return name + ":" + count
end

default_result = [format_user]
override_result = [format_user], name: "alice", count: 3
''',
        monkeypatch,
    )

    variables = executor.variable_replacer.local_variables
    assert variables["default_result"] == "guest:1"
    assert variables["override_result"] == "alice:3"
