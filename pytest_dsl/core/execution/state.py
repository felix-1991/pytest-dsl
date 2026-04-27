"""Mutable execution state for DSL runs."""

from typing import Any, Dict

from pytest_dsl.core.context import TestContext
from pytest_dsl.core.global_context import global_context
from pytest_dsl.core.variable_utils import VariableReplacer


class ExecutionState:
    """Holds variables and context for a DSL execution."""

    def __init__(self, variables: Dict[str, Any] = None,
                 test_context: TestContext = None):
        self.variables = variables if variables is not None else {}
        self.test_context = test_context or TestContext()
        self.variable_replacer = VariableReplacer(
            self.variables,
            self.test_context,
        )

    def bind_executor(self, executor) -> None:
        """Expose the executor to keyword context consumers."""
        self.test_context.executor = executor

    def set_current_data(self, data: Dict[str, Any]) -> None:
        """Merge a data-driven row into local execution state."""
        if data:
            self.apply_context(data)

    def apply_context(self, context: Dict[str, Any]) -> None:
        """Apply caller-provided context variables."""
        if not context:
            return
        self.variables.update(context)
        for key, value in context.items():
            self.test_context.set(key, value)

    def set_variable(self, name: str, value: Any) -> str:
        """Set a DSL variable and return the selected scope."""
        if name.startswith("g_"):
            global_context.set_variable(name, value)
            return "global"

        self.set_local_variable(name, value)
        return "local"

    def set_local_variable(self, name: str, value: Any) -> None:
        """Set a local variable and keep TestContext in sync."""
        self.variables[name] = value
        self.test_context.set(name, value)

    def clear(self, keep_variables: bool = False) -> None:
        """Clear per-execution variables unless explicitly preserved."""
        if keep_variables:
            return

        self.variables.clear()
        self.test_context.clear()

        if hasattr(self.variable_replacer, "local_variables"):
            self.variable_replacer.local_variables.clear()
