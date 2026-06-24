"""XML-RPC serialization boundary tests."""

from pytest_dsl.core.serialization_utils import XMLRPCSerializer
from pytest_dsl.remote.keyword_server import RemoteKeywordServer


LARGE_VERSION = 20260518160022
LONG_STRING_LENGTH = 11704


class _FakeServerProxy:
    def run_keyword(self):
        return {
            "status": "PASS",
            "return": {
                "result": {"TIME": "__bigint__:1717654567890"},
            },
        }


class _FakeHTTPBodyServerProxy:
    def run_keyword(self):
        return {
            "status": "PASS",
            "return": {
                "result": {
                    "resp_body": '{"createTime":1717654567890}',
                    "TIME": "__bigint__:1717654567890",
                },
                "side_effects": {
                    "variables": {
                        "resp_body": '{"createTime":1717654567890}',
                        "TIME": "__bigint__:1717654567890",
                    },
                },
                "metadata": {"keyword_type": "http_request"},
            },
        }


class _FakeVariableSyncServerProxy:
    def __init__(self):
        self.server = RemoteKeywordServer.__new__(RemoteKeywordServer)
        self.server.api_key = None
        self.server.shared_variables = {}

    def sync_variables_from_client(self, variables, api_key=None):
        return self.server.sync_variables_from_client(variables, api_key)

    def set_shared_variable(self, name, value, api_key=None):
        return self.server.set_shared_variable(name, value, api_key)

    def get_shared_variable(self, name, api_key=None):
        return self.server.get_shared_variable(name, api_key)

    def get_variables_for_client(self, api_key=None):
        return self.server.get_variables_for_client(api_key)


class _HookLargeIntClient:
    def __init__(self):
        self.api_key = None
        self.server = self
        self.received_variables = None

    def _apply_hook_filter(self, variables, original_variables, sync_type):
        return {"version": LARGE_VERSION}

    def sync_variables_from_client(self, variables, api_key=None):
        self.received_variables = variables
        return {"status": "success"}


class _FakeRemoteKeywordServerProxy:
    def __init__(self):
        self.received_args = None

    def run_keyword(self, name, args_dict, api_key=None):
        self.received_args = args_dict
        return {
            "status": "PASS",
            "return": {
                "result": "ok",
                "captures": {},
                "session_state": {},
                "metadata": {},
            },
        }


class _FakeContext:
    def get_all_context_variables(self):
        return {"version": 1}


def test_remote_keyword_result_with_large_capture_int_is_xmlrpc_safe():
    """HTTP captures can include millisecond timestamps larger than XML-RPC int."""
    large_create_time = 1717654567890
    server = RemoteKeywordServer.__new__(RemoteKeywordServer)
    keyword_result = {
        "result": {"TIME": large_create_time},
        "side_effects": {
            "variables": {"TIME": large_create_time},
            "context_updates": {}
        },
        "metadata": {
            "keyword_type": "http_request",
            "status_code": 200,
        },
    }

    processed = server._process_keyword_result(keyword_result, test_context=None)
    rpc_payload = {"status": "PASS", "return": processed}

    is_valid, error_msg = XMLRPCSerializer.validate_xmlrpc_data(rpc_payload)
    assert is_valid, error_msg


def test_remote_keyword_result_captures_test_context_local_variables():
    """Legacy remote keywords should return variables written via context.set."""
    from pytest_dsl.core.context import TestContext

    server = RemoteKeywordServer.__new__(RemoteKeywordServer)
    test_context = TestContext()
    test_context.set("exported_value", "second")

    processed = server._process_keyword_result(
        {"success": True}, test_context)

    assert processed["result"] == {"success": True}
    assert processed["captures"] == {"exported_value": "second"}


def test_remote_keyword_side_effects_result_merges_context_variables():
    """New-format remote keyword results should include context variables."""
    from pytest_dsl.core.context import TestContext

    server = RemoteKeywordServer.__new__(RemoteKeywordServer)
    test_context = TestContext()
    test_context.set("saved_response", {"status_code": 201})

    processed = server._process_keyword_result({
        "result": {"created_id": 42},
        "side_effects": {
            "variables": {"created_id": 42},
            "context_updates": {}
        },
        "metadata": {"keyword_type": "http_request"}
    }, test_context)

    assert processed["result"] == {"created_id": 42}
    assert processed["side_effects"]["variables"] == {
        "saved_response": {"status_code": 201},
        "created_id": 42
    }
    assert processed["metadata"]["keyword_type"] == "http_request"


def test_safe_xmlrpc_call_restores_large_int_markers_from_response():
    result = XMLRPCSerializer.safe_xmlrpc_call(
        _FakeServerProxy(), "run_keyword")

    assert result["return"]["result"]["TIME"] == 1717654567890


def test_safe_xmlrpc_call_preserves_complete_response_body_string():
    result = XMLRPCSerializer.safe_xmlrpc_call(
        _FakeHTTPBodyServerProxy(), "run_keyword")

    return_data = result["return"]
    assert return_data["result"]["TIME"] == 1717654567890
    assert return_data["side_effects"]["variables"]["TIME"] == 1717654567890
    assert return_data["result"]["resp_body"] == '{"createTime":1717654567890}'
    assert (
        return_data["side_effects"]["variables"]["resp_body"] ==
        '{"createTime":1717654567890}'
    )


def test_convert_to_serializable_preserves_large_strings_within_payload_limit():
    long_text = "x" * LONG_STRING_LENGTH

    converted = XMLRPCSerializer.convert_to_serializable({
        "json_cmt": long_text,
    })

    assert converted["json_cmt"] == long_text
    assert len(converted["json_cmt"]) == LONG_STRING_LENGTH
    valid, error = XMLRPCSerializer.validate_xmlrpc_data(converted)
    assert valid, error


def test_server_variable_sync_restores_large_int_markers():
    from pytest_dsl.core.yaml_vars import yaml_vars

    server_proxy = _FakeVariableSyncServerProxy()
    var_name = "large_version_sync_test"

    try:
        result = XMLRPCSerializer.safe_xmlrpc_call(
            server_proxy, "sync_variables_from_client",
            {var_name: LARGE_VERSION})

        assert result["status"] == "success"
        assert server_proxy.server.shared_variables[var_name] == LARGE_VERSION
        assert isinstance(server_proxy.server.shared_variables[var_name], int)
    finally:
        yaml_vars._variables.pop(var_name, None)


def test_set_shared_variable_restores_large_int_markers():
    server_proxy = _FakeVariableSyncServerProxy()

    result = XMLRPCSerializer.safe_xmlrpc_call(
        server_proxy, "set_shared_variable", "version", LARGE_VERSION)

    assert result["status"] == "success"
    assert server_proxy.server.shared_variables["version"] == LARGE_VERSION
    assert isinstance(server_proxy.server.shared_variables["version"], int)


def test_shared_variable_getters_return_large_ints_as_xmlrpc_safe_data():
    server_proxy = _FakeVariableSyncServerProxy()
    server_proxy.server.shared_variables["version"] = LARGE_VERSION

    shared_response = server_proxy.get_shared_variable("version")
    all_response = server_proxy.get_variables_for_client()

    shared_valid, shared_error = XMLRPCSerializer.validate_xmlrpc_data(
        shared_response)
    all_valid, all_error = XMLRPCSerializer.validate_xmlrpc_data(all_response)

    assert shared_valid, shared_error
    assert all_valid, all_error
    assert shared_response["value"] == "__bigint__:20260518160022"
    assert all_response["variables"]["version"] == "__bigint__:20260518160022"

    restored_shared = XMLRPCSerializer.safe_xmlrpc_call(
        server_proxy, "get_shared_variable", "version")
    restored_all = XMLRPCSerializer.safe_xmlrpc_call(
        server_proxy, "get_variables_for_client")

    assert restored_shared["value"] == LARGE_VERSION
    assert restored_all["variables"]["version"] == LARGE_VERSION


def test_keyword_metadata_with_large_int_defaults_is_xmlrpc_safe():
    from pytest_dsl.core.keyword_manager import keyword_manager

    keyword_name = "大整数默认值测试"

    @keyword_manager.register(keyword_name, [{
        "name": "版本",
        "mapping": "version",
        "description": "版本号",
        "default": LARGE_VERSION,
    }])
    def fake_keyword(version=None):
        return version

    server = RemoteKeywordServer.__new__(RemoteKeywordServer)

    try:
        contract = server.get_keyword_contract(keyword_name)
        details = server.get_keyword_parameter_details(keyword_name)

        contract_valid, contract_error = XMLRPCSerializer.validate_xmlrpc_data(
            contract)
        details_valid, details_error = XMLRPCSerializer.validate_xmlrpc_data(
            details)

        assert contract_valid, contract_error
        assert details_valid, details_error
        assert contract["parameters"][0]["default"] == (
            "__bigint__:20260518160022")
        assert details[0]["default"] == "__bigint__:20260518160022"

        restored_contract = XMLRPCSerializer.safe_xmlrpc_call(
            server, "get_keyword_contract", keyword_name)
        restored_details = XMLRPCSerializer.safe_xmlrpc_call(
            server, "get_keyword_parameter_details", keyword_name)

        assert restored_contract["parameters"][0]["default"] == LARGE_VERSION
        assert restored_details[0]["default"] == LARGE_VERSION
    finally:
        keyword_manager._keywords.pop(keyword_name, None)


def test_changed_variable_hook_result_is_xmlrpc_safe(monkeypatch):
    from pytest_dsl.core.execution.remote_invoker import RemoteKeywordInvoker
    from pytest_dsl.remote.keyword_client import remote_keyword_manager

    fake_client = _HookLargeIntClient()
    original_clients = remote_keyword_manager.clients
    monkeypatch.setattr(
        remote_keyword_manager, "clients", {"remote": fake_client})

    RemoteKeywordInvoker(executor=None).notify_variable_changed(
        "version", 1)

    assert original_clients is not remote_keyword_manager.clients
    assert fake_client.received_variables == {
        "version": "__bigint__:20260518160022"
    }
    valid, error = XMLRPCSerializer.validate_xmlrpc_data(
        fake_client.received_variables)
    assert valid, error


def test_realtime_sync_hook_result_is_xmlrpc_safe():
    from pytest_dsl.remote.keyword_client import RemoteKeywordClient

    fake_server = _HookLargeIntClient()
    client = RemoteKeywordClient.__new__(RemoteKeywordClient)
    client.server = fake_server
    client.api_key = None
    client.alias = "remote"
    client.sync_config = {"yaml_exclude_patterns": []}

    def hook_filter(variables, original_variables, sync_type,
                    variable_source="context"):
        assert sync_type == "realtime"
        return {"version": LARGE_VERSION}

    client._apply_hook_filter = hook_filter

    client._sync_context_variables_before_execution(_FakeContext())

    assert fake_server.received_variables == {
        "version": "__bigint__:20260518160022"
    }


def test_remote_keyword_call_args_are_xmlrpc_safe():
    from pytest_dsl.remote.keyword_client import RemoteKeywordClient

    fake_server = _FakeRemoteKeywordServerProxy()
    client = RemoteKeywordClient.__new__(RemoteKeywordClient)
    client.server = fake_server
    client.api_key = None
    client.alias = "remote"
    client.url = "http://remote"
    client.timeout = 600.0
    client.param_mappings = {}
    client.keyword_cache = {}

    result = client._execute_remote_keyword(
        name="远程大整数参数测试", version=LARGE_VERSION)

    assert result == "ok"
    assert fake_server.received_args == {
        "version": "__bigint__:20260518160022"
    }
