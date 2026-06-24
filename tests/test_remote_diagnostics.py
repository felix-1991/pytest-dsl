import logging
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from pytest_dsl.core.keyword_manager import keyword_manager
from pytest_dsl.core.dsl_executor import DSLExecutor
from pytest_dsl.remote.keyword_client import remote_keyword_manager
from pytest_dsl.remote.keyword_server import (
    RemoteKeywordServer,
    ThreadedXMLRPCServer,
)


LONG_REMOTE_TEXT = "x" * 11704


@keyword_manager.register("远程诊断失败测试", [
    {"name": "标签", "mapping": "label", "description": "日志隔离标签"},
])
def remote_diagnostics_failure_keyword(**kwargs):
    label = kwargs.get("label")
    print(f"stdout-{label}-before")
    logging.warning("log-%s-before", label)
    raise RuntimeError(f"boom-{label}")


@keyword_manager.register("远程长字符串返回测试", [])
def remote_large_string_keyword(**kwargs):
    return LONG_REMOTE_TEXT


def make_server():
    server = RemoteKeywordServer.__new__(RemoteKeywordServer)
    server.api_key = None
    server.max_concurrency = 20
    server._concurrency_limiter = threading.BoundedSemaphore(20)
    server.shared_variables = {}
    return server


def get_available_local_port():
    sock = socket.socket()
    try:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
    except PermissionError as exc:
        pytest.skip(f"当前环境不允许监听本地端口: {exc}")
    finally:
        sock.close()


def start_minimal_xmlrpc_keyword_server(server, port):
    xmlrpc_server = ThreadedXMLRPCServer(
        ("127.0.0.1", port), allow_none=True)
    xmlrpc_server.register_function(server.get_keyword_names)
    xmlrpc_server.register_function(server.run_keyword)
    xmlrpc_server.register_function(server.get_keyword_arguments)
    xmlrpc_server.register_function(server.get_keyword_parameter_details)
    xmlrpc_server.register_function(server.get_keyword_documentation)
    xmlrpc_server.register_function(server.get_keyword_contract)
    xmlrpc_server.register_function(server.sync_variables_from_client)
    thread = threading.Thread(target=xmlrpc_server.serve_forever, daemon=True)
    thread.start()
    return xmlrpc_server, thread


def stop_xmlrpc_server(xmlrpc_server, thread):
    xmlrpc_server.shutdown()
    xmlrpc_server.server_close()
    thread.join(timeout=2)


def force_large_diagnostics_thread_id(monkeypatch):
    from pytest_dsl.remote.diagnostics import RemoteExecutionCapture

    original_enter = RemoteExecutionCapture.__enter__

    def enter_with_large_thread_id(self):
        result = original_enter(self)
        self.thread_id = 8351538816
        return result

    monkeypatch.setattr(
        RemoteExecutionCapture,
        "__enter__",
        enter_with_large_thread_id,
    )


def test_run_keyword_returns_remote_diagnostics_on_failure():
    server = make_server()

    result = server.run_keyword("远程诊断失败测试", {"label": "alpha"})

    assert result["status"] == "FAIL"
    diagnostics = result["diagnostics"]
    assert diagnostics["version"] == 1
    assert diagnostics["keyword"] == "远程诊断失败测试"
    assert "stdout-alpha-before" in diagnostics["stdout"]
    assert any("log-alpha-before" in item["message"] for item in diagnostics["logs"])
    assert "RuntimeError: boom-alpha" in "".join(diagnostics["traceback"])


def test_remote_execution_capture_keeps_concurrent_stdout_isolated():
    from pytest_dsl.remote.diagnostics import RemoteExecutionCapture

    def run(label):
        with RemoteExecutionCapture(f"keyword-{label}", max_chars=5000) as capture:
            print(f"{label}-start")
            time.sleep(0.02)
            print(f"{label}-end")
            return capture.to_payload("PASS")

    with ThreadPoolExecutor(max_workers=2) as pool:
        left, right = list(pool.map(run, ["left", "right"]))

    assert "left-start" in left["stdout"]
    assert "left-end" in left["stdout"]
    assert "right-start" not in left["stdout"]
    assert "right-end" not in left["stdout"]
    assert "right-start" in right["stdout"]
    assert "right-end" in right["stdout"]
    assert "left-start" not in right["stdout"]
    assert "left-end" not in right["stdout"]


def test_run_keyword_keeps_concurrent_diagnostics_isolated():
    server = make_server()

    def run(label):
        return server.run_keyword("远程诊断失败测试", {"label": label})

    with ThreadPoolExecutor(max_workers=2) as pool:
        left, right = list(pool.map(run, ["left", "right"]))

    left_diagnostics = left["diagnostics"]
    right_diagnostics = right["diagnostics"]

    assert "stdout-left-before" in left_diagnostics["stdout"]
    assert "stdout-right-before" not in left_diagnostics["stdout"]
    assert any("log-left-before" in item["message"]
               for item in left_diagnostics["logs"])
    assert not any("log-right-before" in item["message"]
                   for item in left_diagnostics["logs"])

    assert "stdout-right-before" in right_diagnostics["stdout"]
    assert "stdout-left-before" not in right_diagnostics["stdout"]
    assert any("log-right-before" in item["message"]
               for item in right_diagnostics["logs"])
    assert not any("log-left-before" in item["message"]
                   for item in right_diagnostics["logs"])


def test_remote_diagnostics_redacts_sensitive_output():
    from pytest_dsl.remote.diagnostics import RemoteExecutionCapture

    with RemoteExecutionCapture("secret-keyword", max_chars=5000) as capture:
        print("token=abc123 password: open-sesame normal=value")
        payload = capture.to_payload("FAIL")

    assert "abc123" not in payload["stdout"]
    assert "open-sesame" not in payload["stdout"]
    assert "normal=value" in payload["stdout"]
    assert "***REDACTED***" in payload["stdout"]


def test_remote_diagnostics_payload_is_xmlrpc_safe_with_large_thread_id():
    from pytest_dsl.core.serialization_utils import XMLRPCSerializer
    from pytest_dsl.remote.diagnostics import RemoteExecutionCapture

    capture = RemoteExecutionCapture("xmlrpc-safe-keyword", max_chars=5000)
    capture.thread_id = 8351538816

    payload = capture.to_payload("PASS")

    valid, error = XMLRPCSerializer.validate_xmlrpc_data(payload)
    assert valid, error


def test_run_keyword_response_with_diagnostics_is_xmlrpc_safe(monkeypatch):
    from pytest_dsl.core.serialization_utils import XMLRPCSerializer

    force_large_diagnostics_thread_id(monkeypatch)
    server = make_server()

    response = server.run_keyword("远程诊断失败测试", {"label": "xmlrpc"})

    valid, error = XMLRPCSerializer.validate_xmlrpc_data(response)
    assert valid, error


def test_dsl_remote_keyword_roundtrip_through_xmlrpc_service(monkeypatch):
    force_large_diagnostics_thread_id(monkeypatch)
    remote_keyword_manager.clients.clear()
    server = make_server()
    port = get_available_local_port()
    xmlrpc_server, thread = start_minimal_xmlrpc_keyword_server(server, port)

    try:
        content = f"""
@name: "真实远程服务诊断冒烟"
@remote: "http://127.0.0.1:{port}/" as xmlrpc_diag

xmlrpc_diag|[打印], 内容: "hello remote service"
"""

        DSLExecutor(
            enable_hooks=False,
            enable_tracking=False,
        ).execute_from_content(content)
    finally:
        remote_keyword_manager.clients.clear()
        stop_xmlrpc_server(xmlrpc_server, thread)


def test_dsl_remote_assignment_preserves_large_string_through_xmlrpc(monkeypatch):
    monkeypatch.setenv("PYTEST_DSL_KEEP_VARIABLES", "1")
    remote_keyword_manager.clients.clear()
    server = make_server()
    port = get_available_local_port()
    xmlrpc_server, thread = start_minimal_xmlrpc_keyword_server(server, port)

    try:
        content = f"""
@name: "真实远程长字符串赋值"
@remote: "http://127.0.0.1:{port}/" as xmlrpc_long

json_cmt = xmlrpc_long|[远程长字符串返回测试]
"""

        executor = DSLExecutor(
            enable_hooks=False,
            enable_tracking=False,
        )
        executor.execute_from_content(content)

        assert executor.variables["json_cmt"] == LONG_REMOTE_TEXT
        assert "字符串过长" not in executor.variables["json_cmt"]
    finally:
        remote_keyword_manager.clients.clear()
        stop_xmlrpc_server(xmlrpc_server, thread)


class _FailingRemoteProxy:
    def run_keyword(self, name, args_dict, api_key=None):
        return {
            "status": "FAIL",
            "error": "remote boom",
            "traceback": ["Traceback remote\n", "RuntimeError: remote boom\n"],
            "diagnostics": {
                "version": 1,
                "request_id": "req-client",
                "keyword": name,
                "status": "FAIL",
                "error": "remote boom",
                "elapsed_ms": 12.5,
                "thread_id": 101,
                "stdout": "stdout from remote",
                "stderr": "stderr from remote",
                "logs": [
                    {
                        "level": "ERROR",
                        "logger": "remote.test",
                        "message": "log from remote",
                    }
                ],
                "traceback": [
                    "Traceback remote\n",
                    "RuntimeError: remote boom\n",
                ],
                "truncated": {
                    "stdout": False,
                    "stderr": False,
                    "logs": False,
                },
            },
        }


def make_client(proxy):
    from pytest_dsl.remote.keyword_client import RemoteKeywordClient

    client = RemoteKeywordClient.__new__(RemoteKeywordClient)
    client.server = proxy
    client.api_key = None
    client.alias = "api"
    client.url = "http://remote"
    client.timeout = 600.0
    client.param_mappings = {}
    client.keyword_cache = {}
    return client


def test_remote_keyword_client_preserves_diagnostics_on_failure():
    from pytest_dsl.remote.keyword_client import (
        RemoteKeywordClient,
        RemoteKeywordExecutionError,
    )

    client = make_client(_FailingRemoteProxy())

    with pytest.raises(RemoteKeywordExecutionError) as exc_info:
        client._execute_remote_keyword(name="远程失败诊断测试")

    error = exc_info.value
    assert "remote boom" in str(error)
    assert error.alias == "api"
    assert error.keyword == "远程失败诊断测试"
    assert error.diagnostics["stdout"] == "stdout from remote"
    assert "RuntimeError: remote boom" in "".join(error.traceback)
    assert RemoteKeywordClient is not None


def test_remote_keyword_invoker_attaches_failure_diagnostics_to_allure(monkeypatch):
    from pytest_dsl.remote.keyword_client import RemoteKeywordExecutionError

    attachments = []

    def record_attachment(body, name=None, attachment_type=None):
        attachments.append((name, body))

    def raise_remote_error(alias, keyword_name, **kwargs):
        raise RemoteKeywordExecutionError(
            "remote boom",
            alias=alias,
            keyword=keyword_name,
            url="http://remote",
            timeout=600.0,
            traceback_lines=["Traceback remote\n", "RuntimeError: remote boom\n"],
            diagnostics={
                "version": 1,
                "request_id": "req-allure-fail",
                "keyword": keyword_name,
                "status": "FAIL",
                "error": "remote boom",
                "elapsed_ms": 15.0,
                "stdout": "stdout from allure remote",
                "stderr": "stderr from allure remote",
                "logs": [
                    {
                        "level": "ERROR",
                        "logger": "remote.test",
                        "message": "log from allure remote",
                    }
                ],
                "traceback": [
                    "Traceback remote\n",
                    "RuntimeError: remote boom\n",
                ],
                "truncated": {
                    "stdout": False,
                    "stderr": False,
                    "logs": False,
                },
            },
        )

    monkeypatch.setattr("allure.attach", record_attachment)
    monkeypatch.setattr(
        "pytest_dsl.remote.keyword_client.remote_keyword_manager."
        "execute_remote_keyword_with_outcome",
        raise_remote_error,
        raising=False,
    )

    content = """
@name: "远程失败诊断Allure测试"

api|[打印], 内容: "hello failure diagnostics"
"""

    with pytest.raises(Exception, match="remote boom"):
        DSLExecutor(enable_hooks=False, enable_tracking=False).execute_from_content(content)

    diagnostic_details = "\n".join(
        str(body) for name, body in attachments if name == "远程关键字失败诊断"
    )

    assert "request_id: req-allure-fail" in diagnostic_details
    assert "stdout from allure remote" in diagnostic_details
    assert "stderr from allure remote" in diagnostic_details
    assert "log from allure remote" in diagnostic_details
    assert "RuntimeError: remote boom" in diagnostic_details


def test_remote_keyword_invoker_attaches_success_diagnostics_to_allure(monkeypatch):
    from pytest_dsl.remote.keyword_client import RemoteKeywordCallOutcome

    attachments = []

    def record_attachment(body, name=None, attachment_type=None):
        attachments.append((name, body))

    def execute_remote(alias, keyword_name, **kwargs):
        return RemoteKeywordCallOutcome(
            value="ok",
            diagnostics={
                "version": 1,
                "request_id": "req-allure-pass",
                "keyword": keyword_name,
                "status": "PASS",
                "elapsed_ms": 10.0,
                "stdout": "stdout from successful remote",
                "stderr": "",
                "logs": [
                    {
                        "level": "INFO",
                        "logger": "remote.test",
                        "message": "log from successful remote",
                    }
                ],
                "traceback": [],
                "truncated": {
                    "stdout": False,
                    "stderr": False,
                    "logs": False,
                },
            },
        )

    monkeypatch.setattr("allure.attach", record_attachment)
    monkeypatch.setattr(
        "pytest_dsl.remote.keyword_client.remote_keyword_manager."
        "execute_remote_keyword_with_outcome",
        execute_remote,
        raising=False,
    )

    content = """
@name: "远程成功诊断Allure测试"

api|[打印], 内容: "hello success diagnostics"
"""

    DSLExecutor(enable_hooks=False, enable_tracking=False).execute_from_content(content)

    diagnostic_details = "\n".join(
        str(body) for name, body in attachments if name == "远程关键字远端日志"
    )

    assert "request_id: req-allure-pass" in diagnostic_details
    assert "stdout from successful remote" in diagnostic_details
    assert "log from successful remote" in diagnostic_details
