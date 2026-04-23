"""XML-RPC serialization boundary tests."""

from pytest_dsl.core.serialization_utils import XMLRPCSerializer
from pytest_dsl.remote.keyword_server import RemoteKeywordServer


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
