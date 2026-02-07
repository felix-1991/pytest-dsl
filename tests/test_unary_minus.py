from pytest_dsl.core.dsl_executor import DSLExecutor
from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import parse_with_error_handling


def _parse_assignment_expr(dsl: str):
    ast, errors = parse_with_error_handling(dsl, lexer=get_lexer())
    assert errors == []
    assignment = ast.children[1].children[0]
    return assignment.children[0]


def test_assignment_supports_negative_number_literal():
    expr = _parse_assignment_expr("x = -1")
    assert expr.type == 'UnaryExpr'

    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)
    assert executor.eval_expression(expr) == -1


def test_unary_minus_precedence_with_binary_addition():
    expr = _parse_assignment_expr("x = -1 + 2")
    assert expr.type == 'ArithmeticExpr'
    assert expr.children[0].type == 'UnaryExpr'

    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)
    assert executor.eval_expression(expr) == 1


def test_unary_minus_with_parenthesized_expression():
    expr = _parse_assignment_expr("x = -(1 + 2)")
    assert expr.type == 'UnaryExpr'

    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)
    assert executor.eval_expression(expr) == -3
