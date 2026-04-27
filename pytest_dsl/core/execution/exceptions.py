"""Runtime exceptions used by the DSL executor."""


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


class DSLExecutionError(Exception):
    """DSL执行异常，包含行号信息"""

    def __init__(self, message: str, line_number: int = None,
                 node_type: str = None, original_exception: Exception = None):
        self.line_number = line_number
        self.node_type = node_type
        self.original_exception = original_exception

        error_parts = [message]
        if line_number:
            error_parts.append(f"行号: {line_number}")
        if original_exception:
            original_text = (
                f"{type(original_exception).__name__}: "
                f"{str(original_exception)}"
            )
            if (str(original_exception) not in message and
                    original_text not in message):
                error_parts.append(f"原因: {original_text}")

        super().__init__(" \n ".join(error_parts))
