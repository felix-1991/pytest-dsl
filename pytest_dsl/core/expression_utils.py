"""Shared helpers for evaluating DSL expression operations."""


def coerce_arithmetic_operand(value):
    """Convert numeric strings the same way DSL arithmetic expressions do."""
    if (isinstance(value, str) and
            value.replace('.', '', 1).isdigit()):
        converted = float(value)
        if converted.is_integer():
            return int(converted)
        return converted
    return value


def coerce_comparison_operand(value):
    """Convert integer strings the same way DSL comparison expressions do."""
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return value


def evaluate_arithmetic_operation(left_value, right_value, operator):
    """Evaluate a DSL arithmetic operation."""
    left_value = coerce_arithmetic_operand(left_value)
    right_value = coerce_arithmetic_operand(right_value)

    if operator == '+':
        if isinstance(left_value, str) or isinstance(right_value, str):
            return str(left_value) + str(right_value)
        return left_value + right_value
    if operator == '-':
        return left_value - right_value
    if operator == '*':
        if (isinstance(left_value, str) and
                isinstance(right_value, (int, float))):
            return left_value * int(right_value)
        if (isinstance(right_value, str) and
                isinstance(left_value, (int, float))):
            return right_value * int(left_value)
        return left_value * right_value
    if operator == '/':
        if right_value == 0:
            raise ValueError("除法错误: 除数不能为0")
        return left_value / right_value
    if operator == '%':
        if right_value == 0:
            raise ValueError("模运算错误: 除数不能为0")
        return left_value % right_value

    raise ValueError(f"未知的算术操作符: {operator}")


def evaluate_comparison_operation(left_value, right_value, operator):
    """Evaluate a DSL comparison or membership operation."""
    left_value = coerce_comparison_operand(left_value)
    right_value = coerce_comparison_operand(right_value)

    if operator == '>':
        return left_value > right_value
    if operator == '<':
        return left_value < right_value
    if operator == '>=':
        return left_value >= right_value
    if operator == '<=':
        return left_value <= right_value
    if operator == '==':
        return left_value == right_value
    if operator == '!=':
        return left_value != right_value
    if operator == 'in':
        if isinstance(right_value, dict):
            return left_value in right_value.keys()
        if isinstance(right_value, str):
            return str(left_value) in right_value
        if isinstance(right_value, (list, tuple, set)):
            return left_value in right_value
        return str(left_value) in str(right_value)
    if operator == 'not in':
        if isinstance(right_value, dict):
            return left_value not in right_value.keys()
        if isinstance(right_value, str):
            return str(left_value) not in right_value
        if isinstance(right_value, (list, tuple, set)):
            return left_value not in right_value
        return str(left_value) not in str(right_value)

    raise ValueError(f"未知的比较操作符: {operator}")


def evaluate_logical_operation(children, operator, evaluate_child):
    """Evaluate a DSL logical operation."""
    if operator == 'not':
        return not bool(evaluate_child(children[0]))
    if operator == 'and':
        return bool(evaluate_child(children[0])) and bool(evaluate_child(children[1]))
    if operator == 'or':
        return bool(evaluate_child(children[0])) or bool(evaluate_child(children[1]))

    raise ValueError(f"未知的逻辑操作符: {operator}")


def evaluate_unary_operation(value, operator):
    """Evaluate a DSL unary operation."""
    value = coerce_arithmetic_operand(value)

    if operator == '-':
        return -value

    raise ValueError(f"未知的一元操作符: {operator}")
