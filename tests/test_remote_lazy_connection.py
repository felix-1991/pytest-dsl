import pytest
import pytest_dsl.keywords  # noqa: F401 - import registers builtin keywords

from pytest_dsl.core.dsl_executor import DSLExecutor
from pytest_dsl.core.execution.exceptions import DSLExecutionError
from pytest_dsl.remote.keyword_client import remote_keyword_manager


def test_remote_import_connection_failure_does_not_block_local_steps(
    monkeypatch,
    capsys,
):
    remote_keyword_manager.clients.clear()
    attempts = []

    def fail_register(url, alias, **kwargs):
        attempts.append((url, alias, kwargs))
        return False

    monkeypatch.setattr(
        remote_keyword_manager,
        "register_remote_server",
        fail_register,
    )

    content = """
@name: "远程导入延迟连接测试"
@remote: "http://localhost:65530/" as api

[打印], 内容: "local still runs"
"""

    DSLExecutor(enable_hooks=False, enable_tracking=False).execute_from_content(
        content,
    )

    assert attempts == [("http://localhost:65530/", "api", {})]
    assert "远程服务器 api 暂不可用" in capsys.readouterr().out


def test_remote_import_connection_failure_fails_when_keyword_is_called(
    monkeypatch,
):
    remote_keyword_manager.clients.clear()

    monkeypatch.setattr(
        remote_keyword_manager,
        "register_remote_server",
        lambda *args, **kwargs: False,
    )

    content = """
@name: "远程导入调用失败测试"
@remote: "http://localhost:65530/" as api

api|[打印], 内容: "remote should fail here"
"""

    with pytest.raises(DSLExecutionError, match="未找到别名为 api 的远程服务器"):
        DSLExecutor(
            enable_hooks=False,
            enable_tracking=False,
        ).execute_from_content(content)
