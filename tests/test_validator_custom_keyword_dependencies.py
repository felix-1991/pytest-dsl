import pytest_dsl.keywords  # noqa: F401 - registers builtin keywords

from pytest_dsl.core.custom_keyword_manager import custom_keyword_manager
from pytest_dsl.core.dsl_executor import DSLExecutor
from pytest_dsl.core.keyword_manager import keyword_manager
from pytest_dsl.core.validator import validate_dsl


DEPENDENCY_KEYWORDS = [
    "依赖关键字_基础",
    "依赖关键字_组合",
]


def _remove_dependency_keywords():
    for name in DEPENDENCY_KEYWORDS:
        keyword_manager._keywords.pop(name, None)


def test_custom_keyword_definition_allows_dependencies_registered_later():
    _remove_dependency_keywords()
    try:
        base_keyword = """
@name: "base"
function 依赖关键字_基础() do
    [打印], 内容: "base"
end
"""
        composite_keyword = """
@name: "composite"
function 依赖关键字_组合() do
    [依赖关键字_基础]
end
"""

        ok, diagnostics = validate_dsl(composite_keyword)

        assert ok is True
        assert any("未注册的关键字: 依赖关键字_基础" in str(item) for item in diagnostics)

        custom_keyword_manager.register_keyword_from_dsl_content(
            composite_keyword,
            "test:composite",
        )
        custom_keyword_manager.register_keyword_from_dsl_content(
            base_keyword,
            "test:base",
        )

        DSLExecutor(enable_hooks=False, enable_tracking=False).execute_from_content(
            """
@name: "run composite"
[依赖关键字_组合]
"""
        )
    finally:
        _remove_dependency_keywords()


def test_top_level_unknown_keyword_still_fails_validation():
    _remove_dependency_keywords()

    ok, diagnostics = validate_dsl(
        """
@name: "unknown"
[依赖关键字_基础]
"""
    )

    assert ok is False
    assert any("关键字错误: 未注册的关键字: 依赖关键字_基础" in str(item) for item in diagnostics)
