"""Expression evaluation for parsed DSL AST nodes."""

import re

from pytest_dsl.core.expression_utils import (
    evaluate_arithmetic_operation,
    evaluate_comparison_operation,
    evaluate_logical_operation,
    evaluate_unary_operation,
)
from pytest_dsl.core.parser import Node


class ExpressionEvaluator:
    """Evaluates expression nodes against a DSL executor runtime."""

    def __init__(self, executor):
        self.executor = executor

    @property
    def variable_replacer(self):
        return self.executor.variable_replacer

    def evaluate(self, expr_node):
        """Evaluate an expression node and return its runtime value."""
        def _eval_expression_impl():
            if expr_node.type == 'Expression':
                value = self._eval_expression_value(expr_node.value)
                return self.variable_replacer.replace_in_value(value)
            if expr_node.type == 'StringLiteral':
                if '${' in expr_node.value:
                    return self.variable_replacer.replace_in_string(
                        expr_node.value,
                        expression_evaluator=(
                            self._eval_interpolation_expression
                        ),
                    )
                return expr_node.value
            if expr_node.type == 'NumberLiteral':
                return expr_node.value
            if expr_node.type == 'VariableRef':
                var_name = expr_node.value
                try:
                    return self.variable_replacer.get_variable(var_name)
                except KeyError:
                    raise KeyError(f"变量 '{var_name}' 不存在")
            if expr_node.type == 'PlaceholderRef':
                return self.variable_replacer.replace_in_string(
                    expr_node.value,
                    expression_evaluator=self._eval_interpolation_expression,
                )
            if expr_node.type == 'KeywordCall':
                return self.executor.execute(expr_node)
            if expr_node.type == 'ListExpr':
                return [self.evaluate(item) for item in expr_node.children]
            if expr_node.type == 'DictExpr':
                return {
                    self.evaluate(item.children[0]):
                    self.evaluate(item.children[1])
                    for item in expr_node.children
                }
            if expr_node.type == 'BooleanExpr':
                return expr_node.value
            if expr_node.type == 'ComparisonExpr':
                return self._eval_comparison_expr(expr_node)
            if expr_node.type == 'ArithmeticExpr':
                return self._eval_arithmetic_expr(expr_node)
            if expr_node.type == 'UnaryExpr':
                return self._eval_unary_expr(expr_node)
            if expr_node.type == 'IndexAccessExpr':
                return self._eval_index_access_expr(expr_node)
            if expr_node.type == 'PropertyAccessExpr':
                return self._eval_property_access_expr(expr_node)
            if expr_node.type == 'LogicalExpr':
                return self._eval_logical_expr(expr_node)

            raise Exception(f"无法求值的表达式类型: {expr_node.type}")

        return self.executor._execute_with_error_handling(
            _eval_expression_impl,
            expr_node,
        )

    def _eval_expression_value(self, value):
        """Evaluate a raw expression payload."""
        try:
            if isinstance(value, Node):
                return self.evaluate(value)
            if isinstance(value, str):
                if '${' in value:
                    return self.variable_replacer.replace_in_string(
                        value,
                        expression_evaluator=(
                            self._eval_interpolation_expression
                        ),
                    )

                var_pattern = (r'^[a-zA-Z_\u4e00-\u9fa5]'
                               r'[a-zA-Z0-9_\u4e00-\u9fa5]*$')
                if (re.match(var_pattern, value) and
                        value in self.variable_replacer.local_variables):
                    return self.variable_replacer.local_variables[value]
                return value
            return value
        except Exception as e:
            context_info = f"解析表达式值 '{value}'"
            self.executor._handle_exception_with_line_info(
                e,
                context_info=context_info,
            )

    def _eval_interpolation_expression(self, expr_text: str):
        """Evaluate a ${...} body with the DSL expression parser."""
        from pytest_dsl.core.lexer import get_lexer
        from pytest_dsl.core.parser import parse_expression_fragment

        expr_node, errors = parse_expression_fragment(
            expr_text,
            lexer=get_lexer(),
        )
        if errors:
            messages = "; ".join(error.get('message', str(error))
                                 for error in errors)
            raise ValueError(f"无效的占位符表达式 '{expr_text}': {messages}")
        if expr_node is None:
            raise ValueError(f"无效的占位符表达式 '{expr_text}'")

        return self.evaluate(expr_node)

    def _eval_index_access_expr(self, expr_node):
        collection = self.evaluate(expr_node.children[0])
        key = self.evaluate(expr_node.children[1])
        return self.variable_replacer.access_by_key(collection, key)

    def _eval_property_access_expr(self, expr_node):
        current_value = self.evaluate(expr_node.children[0])
        return self.variable_replacer.access_property(
            current_value,
            expr_node.value,
        )

    def _eval_comparison_expr(self, expr_node):
        operator = "未知"
        try:
            left_value = self.evaluate(expr_node.children[0])
            right_value = self.evaluate(expr_node.children[1])
            operator = expr_node.value
            return evaluate_comparison_operation(
                left_value,
                right_value,
                operator,
            )
        except Exception as e:
            context_info = f"比较表达式求值 '{operator}'"
            self.executor._handle_exception_with_line_info(
                e,
                expr_node,
                context_info,
            )

    def _eval_arithmetic_expr(self, expr_node):
        operator = "未知"
        try:
            left_value = self.evaluate(expr_node.children[0])
            right_value = self.evaluate(expr_node.children[1])
            operator = expr_node.value
            return evaluate_arithmetic_operation(
                left_value,
                right_value,
                operator,
            )
        except Exception as e:
            context_info = f"算术表达式求值 '{operator}'"
            self.executor._handle_exception_with_line_info(
                e,
                expr_node,
                context_info,
            )

    def _eval_logical_expr(self, expr_node):
        operator = "未知"
        try:
            operator = expr_node.value
            return evaluate_logical_operation(
                expr_node.children,
                operator,
                self.evaluate,
            )
        except Exception as e:
            context_info = f"逻辑表达式求值 '{operator}'"
            self.executor._handle_exception_with_line_info(
                e,
                expr_node,
                context_info,
            )

    def _eval_unary_expr(self, expr_node):
        operator = "未知"
        try:
            operator = expr_node.value
            operand_value = self.evaluate(expr_node.children[0])
            return evaluate_unary_operation(operand_value, operator)
        except Exception as e:
            context_info = f"一元表达式求值 '{operator}'"
            self.executor._handle_exception_with_line_info(
                e,
                expr_node,
                context_info,
            )

    def get_variable(self, var_name):
        return self.variable_replacer.get_variable(var_name)

    def replace_variables_in_string(self, value):
        return self.variable_replacer.replace_in_string(value)
