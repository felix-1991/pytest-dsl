import pytest
import pytest_dsl.keywords  # noqa: F401 - registers builtin keywords

from pytest_dsl.core.custom_keyword_manager import custom_keyword_manager
from pytest_dsl.core.dsl_executor import DSLExecutor
from pytest_dsl.core.hookable_keyword_manager import hookable_keyword_manager
from pytest_dsl.core.keyword_manager import keyword_manager
from pytest_dsl.core.validator import validate_dsl


DEPENDENCY_KEYWORDS = [
    "依赖关键字_基础",
    "依赖关键字_组合",
    "Hook注册语法关键字",
    "静默注册关键字",
    "静默Hook注册关键字",
    "缺失Hook注册关键字",
]


def _remove_dependency_keywords():
    for name in DEPENDENCY_KEYWORDS:
        hookable_keyword_manager.hook_keywords.pop(name, None)
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


def test_hook_registered_keyword_parses_and_executes_current_dsl_syntax(monkeypatch):
    _remove_dependency_keywords()
    hook_keyword = """
@name: "hook keyword syntax"
function Hook注册语法关键字(base=2) do
    value = base + 1
    if value == base + 1 do
        return "hook:" + value
    else
        return "bad"
    end
end
"""

    try:
        hookable_keyword_manager.register_hook_keyword(
            "Hook注册语法关键字",
            hook_keyword,
            {"source_type": "hook", "source_name": "syntax-test"},
        )

        assert hookable_keyword_manager.is_hook_keyword("Hook注册语法关键字")
        assert keyword_manager.get_keyword_info("Hook注册语法关键字")[
            "source_type"
        ] == "hook"

        monkeypatch.setenv("PYTEST_DSL_KEEP_VARIABLES", "1")
        executor = DSLExecutor(enable_hooks=False, enable_tracking=False)
        executor.execute_from_content(
            """
@name: "run hook keyword"
result = [Hook注册语法关键字], base: 4
"""
        )

        assert executor.variable_replacer.local_variables["result"] == "hook:5"
    finally:
        _remove_dependency_keywords()


def test_custom_keyword_registration_is_quiet_on_success(capsys):
    _remove_dependency_keywords()
    quiet_keyword = """
@name: "quiet registration"
function 静默注册关键字() do
    return "ok"
end
"""

    try:
        registered_keywords = custom_keyword_manager.register_keyword_from_dsl_content(
            quiet_keyword,
            "test:quiet",
        )

        assert registered_keywords == ["静默注册关键字"]
        assert capsys.readouterr().out == ""
    finally:
        _remove_dependency_keywords()


def test_custom_keyword_registration_logs_success_when_verbose(monkeypatch, capsys):
    _remove_dependency_keywords()
    monkeypatch.setenv("PYTEST_DSL_VERBOSE", "1")
    quiet_keyword = """
@name: "quiet registration"
function 静默注册关键字() do
    return "ok"
end
"""

    try:
        custom_keyword_manager.register_keyword_from_dsl_content(
            quiet_keyword,
            "test:quiet",
        )

        output = capsys.readouterr().out
        assert "已注册自定义关键字: 静默注册关键字 来自文件: test:quiet" in output
    finally:
        _remove_dependency_keywords()


def test_custom_keyword_registration_prints_failures(capsys):
    _remove_dependency_keywords()

    with pytest.raises(Exception):
        custom_keyword_manager.register_keyword_from_dsl_content(
            '@name: "broken"\n',
            "test:broken",
        )

    output = capsys.readouterr().out
    assert "从DSL内容注册关键字失败（来源：test:broken）" in output


def test_hook_keyword_registration_is_quiet_on_success(capsys):
    _remove_dependency_keywords()
    hook_keyword = """
@name: "quiet hook registration"
function 静默Hook注册关键字() do
    return "ok"
end
"""

    try:
        hookable_keyword_manager.register_hook_keyword(
            "静默Hook注册关键字",
            hook_keyword,
            {"source_type": "hook", "source_name": "quiet-test"},
        )

        assert hookable_keyword_manager.is_hook_keyword("静默Hook注册关键字")
        assert capsys.readouterr().out == ""
    finally:
        _remove_dependency_keywords()


def test_hook_keyword_registration_logs_success_when_verbose(monkeypatch, capsys):
    _remove_dependency_keywords()
    monkeypatch.setenv("PYTEST_DSL_VERBOSE", "1")
    hook_keyword = """
@name: "quiet hook registration"
function 静默Hook注册关键字() do
    return "ok"
end
"""

    try:
        hookable_keyword_manager.register_hook_keyword(
            "静默Hook注册关键字",
            hook_keyword,
            {"source_type": "hook", "source_name": "quiet-test"},
        )

        output = capsys.readouterr().out
        assert "已注册自定义关键字: 静默Hook注册关键字 来自文件: quiet-test" in output
        assert "注册Hook关键字: 静默Hook注册关键字" in output
    finally:
        _remove_dependency_keywords()


def test_hook_keyword_registration_prints_failures(capsys):
    _remove_dependency_keywords()

    with pytest.raises(Exception):
        hookable_keyword_manager.register_hook_keyword(
            "缺失Hook注册关键字",
            '@name: "missing"\n',
            {"source_type": "hook", "source_name": "broken-test"},
        )

    output = capsys.readouterr().out
    assert "注册Hook关键字失败 缺失Hook注册关键字" in output
