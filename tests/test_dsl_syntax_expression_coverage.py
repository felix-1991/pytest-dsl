import pytest

from pytest_dsl.core.dsl_executor import DSLExecutor
from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import (
    parse_expression_fragment,
    parse_with_error_handling,
)


def _parse_dsl(dsl: str):
    ast, errors = parse_with_error_handling(dsl, lexer=get_lexer())
    assert errors == []
    assert ast is not None
    return ast


def _statements(ast):
    return next(child for child in ast.children if child.type == "Statements")


def _parse_assignment_expr(dsl: str):
    ast = _parse_dsl(dsl)
    assignment = _statements(ast).children[0]
    assert assignment.type == "Assignment"
    return assignment.children[0]


def _eval_expr(text: str, **variables):
    expr, errors = parse_expression_fragment(text, lexer=get_lexer())
    assert errors == []
    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)
    executor.variable_replacer.local_variables.update(variables)
    for name, value in variables.items():
        executor.test_context.set(name, value)
    return executor.eval_expression(expr)


def test_metadata_variants_parse_into_start_metadata_nodes():
    ast = _parse_dsl(
        '''
@name: "完整语法"
@description: "覆盖元信息"
@tags: ["syntax", fast]
@author: tester
@date: 2026-04-25
@data: "cases.csv" using csv
@import: "resources/common.resource"
@remote: "http://localhost:8270" as api
value = 1
'''
    )

    metadata = ast.children[0]
    items = {item.type: item.value for item in metadata.children}

    assert items["@name"] == "完整语法"
    assert items["@description"] == "覆盖元信息"
    assert [tag.value for tag in items["@tags"]] == ["syntax", "fast"]
    assert items["@author"] == "tester"
    assert items["@date"] == "2026-04-25"
    assert items["@data"] == {"file": "cases.csv", "format": "csv"}
    assert items["@import"] == "resources/common.resource"
    assert items["RemoteImport"] == {
        "url": "http://localhost:8270",
        "alias": "api",
    }


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        ("1 + 2 * 3", 7),
        ("(1 + 2) * 3", 9),
        ("10 / 4", 2.5),
        ("10 % 4", 2),
        ('"a" + 3', "a3"),
        ('"ha" * 3', "hahaha"),
        ("-2 * 3 + 1", -5),
    ],
)
def test_arithmetic_expression_operators_and_precedence(expr, expected):
    assert _eval_expr(expr) == expected


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        ("3 > 2", True),
        ("3 < 2", False),
        ("3 >= 3", True),
        ("2 <= 1", False),
        ('"10" == 10', True),
        ('"10" != "2"', True),
        ('"a" in ["a", "b"]', True),
        ('"c" not in ["a", "b"]', True),
        ('"key" in {"key": 1}', True),
        ('2 in "abc2"', True),
    ],
)
def test_comparison_and_membership_expression_operators(expr, expected):
    assert _eval_expr(expr) is expected


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        ("True and False or True", True),
        ("True and (False or False)", False),
        ("not False", True),
        ("not (True and False)", True),
        ("False or not False", True),
    ],
)
def test_logical_expression_operators_and_parentheses(expr, expected):
    assert _eval_expr(expr) is expected


def test_collection_literals_support_nested_values_access_and_empty_values():
    expr = _parse_assignment_expr(
        'value = {"users": [{"name": "张三"}, {"name": "李四"}], '
        '"empty_list": [], "empty_dict": {}}'
    )

    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)
    result = executor.eval_expression(expr)

    assert result == {
        "users": [{"name": "张三"}, {"name": "李四"}],
        "empty_list": [],
        "empty_dict": {},
    }
    executor.variable_replacer.local_variables["data"] = result
    executor.test_context.set("data", result)
    access_expr = _parse_assignment_expr("name = data.users[1].name")
    assert executor.eval_expression(access_expr) == "李四"


def test_control_flow_syntax_parses_if_elif_else_and_loop_controls():
    ast = _parse_dsl(
        '''
items = {"a": 1, "b": 2}
for key, value in items do
    if value == 1 do
        continue
    elif value == 2 do
        break
    else
        value = 0
    end
end
'''
    )

    statements = _statements(ast).children
    loop = statements[1]
    if_stmt = loop.children[1].children[0]

    assert loop.type == "ForKeyValueLoop"
    assert loop.value == {"key_var": "key", "value_var": "value"}
    assert if_stmt.type == "IfStatement"
    assert if_stmt.children[2].type == "ElifClause"
    assert if_stmt.children[3].type == "Statements"
    assert if_stmt.children[1].children[0].type == "Continue"
    assert if_stmt.children[2].children[1].children[0].type == "Break"


def test_retry_custom_keyword_return_remote_call_and_teardown_syntax_parse():
    ast = _parse_dsl(
        '''
function build_message(name="guest", count=1) do
    return name + ":" + count
end

retry 3 times every 0 until True do
    result = ${api_alias}|[fetch], id: 1
end

teardown do
end
'''
    )

    statements = _statements(ast).children
    custom_keyword = statements[0]
    retry = statements[1]
    remote_assignment = retry.children[3].children[0]
    teardown = ast.children[2]

    assert custom_keyword.type == "CustomKeyword"
    assert [param.value for param in custom_keyword.children[0]] == [
        "name",
        "count",
    ]
    assert custom_keyword.children[1].children[0].type == "Return"
    assert retry.type == "Retry"
    assert [child.type if child is not None else None for child in retry.children] == [
        "NumberLiteral",
        "NumberLiteral",
        "BooleanExpr",
        "Statements",
    ]
    assert remote_assignment.type == "AssignmentRemoteKeywordCall"
    assert remote_assignment.children[0].value == {
        "alias": "${api_alias}",
        "keyword": "fetch",
    }
    assert teardown.type == "Teardown"
    assert teardown.children[0].children == []
