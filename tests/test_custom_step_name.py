from contextlib import contextmanager

import pytest_dsl.keywords  # noqa: F401 - import registers builtin keywords
from pytest_dsl.core.dsl_executor import DSLExecutor


def test_keyword_call_uses_custom_step_name_in_allure(monkeypatch):
    step_titles = []

    @contextmanager
    def record_step(title):
        step_titles.append(title)
        yield

    monkeypatch.setattr("allure.step", record_step)

    content = """
@name: "自定义步骤名称测试"

[打印], 内容: "hello", 步骤名称: "自定义打印步骤"
"""

    DSLExecutor(enable_hooks=False).execute_from_content(content)

    assert "自定义打印步骤" in step_titles


def test_remote_keyword_call_forwards_custom_step_name(monkeypatch):
    forwarded_calls = []

    def record_remote_call(alias, keyword_name, **kwargs):
        forwarded_calls.append((alias, keyword_name, kwargs))
        return "ok"

    monkeypatch.setattr(
        "pytest_dsl.remote.keyword_client.remote_keyword_manager."
        "execute_remote_keyword",
        record_remote_call,
    )

    content = """
@name: "远程自定义步骤名称测试"

api|[打印], 内容: "hello", 步骤名称: "远程自定义打印步骤"
"""

    DSLExecutor(enable_hooks=False).execute_from_content(content)

    assert len(forwarded_calls) == 1
    alias, keyword_name, kwargs = forwarded_calls[0]
    assert alias == "api"
    assert keyword_name == "打印"
    assert kwargs["内容"] == "hello"
    assert kwargs["步骤名称"] == "远程自定义打印步骤"


def test_remote_keyword_call_uses_custom_step_name_in_allure(monkeypatch):
    step_titles = []

    @contextmanager
    def record_step(title):
        step_titles.append(title)
        yield

    monkeypatch.setattr("allure.step", record_step)
    monkeypatch.setattr(
        "pytest_dsl.remote.keyword_client.remote_keyword_manager."
        "execute_remote_keyword",
        lambda *args, **kwargs: "ok",
    )

    content = """
@name: "远程Allure自定义步骤名称测试"

api|[打印], 内容: "hello", 步骤名称: "远程自定义打印步骤"
"""

    DSLExecutor(enable_hooks=False).execute_from_content(content)

    assert "远程自定义打印步骤" in step_titles
