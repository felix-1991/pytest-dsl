from contextlib import contextmanager

import pytest
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


def test_keyword_call_reports_arguments_in_default_allure(monkeypatch):
    attachments = []

    def record_attachment(body, name=None, attachment_type=None):
        attachments.append((name, body))

    monkeypatch.setattr("allure.attach", record_attachment)
    monkeypatch.delenv("PYTEST_DSL_VERBOSE", raising=False)

    content = """
@name: "默认参数报告测试"

[打印], 内容: "hello report"
"""

    DSLExecutor(enable_hooks=False, enable_tracking=False).execute_from_content(content)

    keyword_call_details = "\n".join(
        str(body) for name, body in attachments if name == "关键字调用"
    )

    assert "传入参数:" in keyword_call_details
    assert "内容(content): 'hello report'" in keyword_call_details
    assert "context" not in keyword_call_details
    assert "skip_logging" not in keyword_call_details


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


def test_remote_keyword_call_reports_arguments_in_default_allure(monkeypatch):
    attachments = []

    def record_attachment(body, name=None, attachment_type=None):
        attachments.append((name, body))

    monkeypatch.setattr("allure.attach", record_attachment)
    monkeypatch.setattr(
        "pytest_dsl.remote.keyword_client.remote_keyword_manager."
        "execute_remote_keyword",
        lambda *args, **kwargs: "ok",
    )
    monkeypatch.delenv("PYTEST_DSL_VERBOSE", raising=False)

    content = """
@name: "远程默认参数报告测试"

api|[打印], 内容: "hello remote"
"""

    DSLExecutor(enable_hooks=False, enable_tracking=False).execute_from_content(content)

    remote_details = "\n".join(
        str(body) for name, body in attachments if name == "远程关键字执行结果"
    )

    assert "传入参数:" in remote_details
    assert "内容: 'hello remote'" in remote_details
    assert "context" not in remote_details


def test_remote_keyword_call_reports_arguments_on_failure(monkeypatch):
    attachments = []

    def record_attachment(body, name=None, attachment_type=None):
        attachments.append((name, body))

    def raise_remote_error(*args, **kwargs):
        raise RuntimeError("remote boom")

    monkeypatch.setattr("allure.attach", record_attachment)
    monkeypatch.setattr(
        "pytest_dsl.remote.keyword_client.remote_keyword_manager."
        "execute_remote_keyword",
        raise_remote_error,
    )
    monkeypatch.delenv("PYTEST_DSL_VERBOSE", raising=False)

    content = """
@name: "远程失败参数报告测试"

api|[打印], 内容: "hello failure"
"""

    with pytest.raises(Exception, match="remote boom"):
        DSLExecutor(enable_hooks=False, enable_tracking=False).execute_from_content(content)

    error_details = "\n".join(
        str(body) for name, body in attachments if name == "DSL执行异常"
    )

    assert "传入参数:" in error_details
    assert "内容: 'hello failure'" in error_details
    assert "context" not in error_details


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
