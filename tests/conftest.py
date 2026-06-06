import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace


# These legacy CLI/manual DSL assets are exercised through their dedicated
# runners and require syntax/runtime setup that is outside the default pytest
# session. Keep them out of repository-wide native DSL collection.
collect_ignore_glob = [
    "test_auth_basic.dsl",
    "test_auth_functionality.dsl",
    "test_retry_functionality.dsl",
]


_TESTS_DIR = Path(__file__).resolve().parent
_AUTH_DSL_FILES = {
    "comprehensive_auth_test.dsl",
    "simple_auth_test.dsl",
}
_NULL_LITERAL_DSL_FILE = "test_http_null_literal_request.dsl"
_AUTH_SERVER_HEALTH_URL = "http://localhost:8889/health"

_auth_mock_server = None


def pytest_runtest_setup(item):
    filename = _dsl_filename(item)
    if filename in _AUTH_DSL_FILES:
        _snapshot_yaml_variables(item)
        _load_simple_config()
        _reset_http_client_manager()
        _ensure_auth_mock_server()
    elif filename == _NULL_LITERAL_DSL_FILE:
        _install_null_literal_http_request_fake(item)


def pytest_runtest_teardown(item):
    _restore_null_literal_http_request(item)
    _restore_yaml_variables(item)


def pytest_sessionfinish(session, exitstatus):
    _stop_auth_mock_server()


def _dsl_filename(item):
    path = getattr(item, "case_path", None) or getattr(item, "path", None)
    return Path(str(path)).name if path else None


def _snapshot_yaml_variables(item):
    from pytest_dsl.core.yaml_vars import yaml_vars

    if hasattr(item, "_pytest_dsl_yaml_snapshot"):
        return
    item._pytest_dsl_yaml_snapshot = (
        yaml_vars._variables.copy(),
        yaml_vars._loaded_files.copy(),
    )


def _restore_yaml_variables(item):
    from pytest_dsl.core.yaml_vars import yaml_vars

    snapshot = getattr(item, "_pytest_dsl_yaml_snapshot", None)
    if snapshot is None:
        return
    variables, loaded_files = snapshot
    yaml_vars._variables = variables
    yaml_vars._loaded_files = loaded_files
    _reset_http_client_manager()
    delattr(item, "_pytest_dsl_yaml_snapshot")


def _load_simple_config():
    from pytest_dsl.core.yaml_vars import yaml_vars

    yaml_vars.clear()
    yaml_vars.load_yaml_file(str(_TESTS_DIR / "simple_config.yaml"))


def _reset_http_client_manager():
    from pytest_dsl.core.http_client import http_client_manager

    http_client_manager.close_all()
    http_client_manager.set_context(None)


def _ensure_auth_mock_server():
    global _auth_mock_server

    if _auth_mock_server is not None or _auth_server_is_healthy():
        return

    from tests.test_auth_mock_server import AuthMockServer

    server = AuthMockServer()
    try:
        server.start()
    except OSError:
        if _auth_server_is_healthy():
            return
        raise

    _auth_mock_server = server
    _wait_for_auth_mock_server()


def _stop_auth_mock_server():
    global _auth_mock_server

    if _auth_mock_server is None:
        return
    _auth_mock_server.stop()
    _auth_mock_server = None


def _wait_for_auth_mock_server(timeout_seconds=5):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if _auth_server_is_healthy():
            return
        time.sleep(0.05)
    raise RuntimeError("授权测试Mock服务器启动后健康检查超时")


def _auth_server_is_healthy():
    try:
        with urllib.request.urlopen(_AUTH_SERVER_HEALTH_URL, timeout=0.5) as response:
            if response.status != 200:
                return False
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("server") == "auth-mock-server"
    except (OSError, urllib.error.URLError, ValueError, json.JSONDecodeError):
        return False


def _install_null_literal_http_request_fake(item):
    from pytest_dsl.keywords import http_keywords

    if hasattr(item, "_pytest_dsl_original_http_request"):
        return

    item._pytest_dsl_original_http_request = http_keywords.HTTPRequest

    class FakeHTTPRequest:
        def __init__(self, config, client_name="default", session_name=None):
            self.config = config
            self.client_name = client_name
            self.session_name = session_name
            self.captured_values = {
                "caller": (
                    config.get("request", {})
                    .get("json", {})
                    .get("meta", {})
                    .get("caller")
                )
            }

        def execute(self, disable_auth=False):
            self.disable_auth = disable_auth
            return SimpleNamespace(
                status_code=200,
                headers={"Content-Type": "application/json"},
                text='{"ok": true}',
                url="https://example.test/async-task",
                elapsed=0.01,
            )

        def process_asserts(self, specific_asserts=None, index_mapping=None):
            return ([{"result": True}], [])

    http_keywords.HTTPRequest = FakeHTTPRequest


def _restore_null_literal_http_request(item):
    from pytest_dsl.keywords import http_keywords

    original = getattr(item, "_pytest_dsl_original_http_request", None)
    if original is None:
        return
    http_keywords.HTTPRequest = original
    delattr(item, "_pytest_dsl_original_http_request")
