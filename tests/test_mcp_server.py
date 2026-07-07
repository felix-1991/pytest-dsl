import hashlib
import http.client
import io
import json
from pathlib import Path
import threading

import pytest

from pytest_dsl.core.keyword_manager import keyword_manager


@pytest.fixture(autouse=True)
def isolate_keyword_registry(monkeypatch):
    import pytest_dsl.core.plugin_discovery as plugin_discovery

    original_keywords = dict(keyword_manager._keywords)
    keyword_manager._keywords.clear()
    monkeypatch.setattr(plugin_discovery, "load_all_plugins", lambda: None)
    monkeypatch.setattr(plugin_discovery, "scan_local_keywords", lambda: None)
    yield
    keyword_manager._keywords.clear()
    keyword_manager._keywords.update(original_keywords)


def _register_sample_keyword():
    @keyword_manager.register(
        "sample_add",
        parameters=[
            {"name": "left", "mapping": "left", "description": "左操作数"},
            {"name": "right", "mapping": "right", "description": "右操作数"},
        ],
        category="测试",
        returns={"type": "int", "description": "两数之和"},
    )
    def sample_add(left, right, context=None):
        return int(left) + int(right)

    return sample_add


def test_pyproject_exposes_mcp_console_script():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert 'pytest-dsl-mcp = "pytest_dsl.mcp.server:main"' in pyproject


def test_mcp_initialize_reports_tools_capability():
    from pytest_dsl.mcp.server import MCPKeywordServer

    server = MCPKeywordServer()

    response = server.handle_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "1"},
        },
    })

    assert response["id"] == 1
    assert response["result"]["protocolVersion"] == "2025-06-18"
    assert response["result"]["capabilities"]["tools"] == {
        "listChanged": False
    }
    assert response["result"]["serverInfo"]["name"] == "pytest-dsl"


def test_mcp_tools_list_includes_meta_tools_and_dynamic_keyword_tool():
    from pytest_dsl.mcp.server import MCPKeywordServer

    _register_sample_keyword()
    server = MCPKeywordServer()

    response = server.handle_request({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
    })

    tools = response["result"]["tools"]
    tool_names = {tool["name"] for tool in tools}
    assert "pytest_dsl_list_keywords" in tool_names
    assert "pytest_dsl_run_keyword" in tool_names
    assert "pytest_dsl_keyword__sample_add" in tool_names

    sample_tool = next(
        tool for tool in tools if tool["name"] == "pytest_dsl_keyword__sample_add"
    )
    assert sample_tool["title"] == "sample_add"
    assert sample_tool["inputSchema"]["required"] == ["left", "right"]
    assert sample_tool["inputSchema"]["properties"]["left"]["description"] == "左操作数"


def test_mcp_read_only_meta_tools_are_annotated_as_read_only():
    from pytest_dsl.mcp.server import MCPKeywordServer

    server = MCPKeywordServer()

    response = server.handle_request({
        "jsonrpc": "2.0",
        "id": 21,
        "method": "tools/list",
    })

    tools = {
        tool["name"]: tool for tool in response["result"]["tools"]
    }
    assert tools["pytest_dsl_list_keywords"]["annotations"] == {
        "readOnlyHint": True,
        "destructiveHint": False,
    }
    assert tools["pytest_dsl_get_keyword_contract"]["annotations"] == {
        "readOnlyHint": True,
        "destructiveHint": False,
    }
    assert tools["pytest_dsl_get_shared_variable"]["annotations"] == {
        "readOnlyHint": True,
        "destructiveHint": False,
    }


def test_mcp_dynamic_keyword_tool_call_uses_existing_keyword_execution():
    from pytest_dsl.mcp.server import MCPKeywordServer

    _register_sample_keyword()
    server = MCPKeywordServer()

    response = server.handle_request({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "pytest_dsl_keyword__sample_add",
            "arguments": {"left": 2, "right": 3},
        },
    })

    result = response["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["status"] == "PASS"
    assert result["structuredContent"]["return"]["result"] == 5
    assert json.loads(result["content"][0]["text"])["status"] == "PASS"


@pytest.mark.parametrize("resource_dir_name", ["resources", "resource"])
def test_mcp_loads_project_resource_keywords_as_tools_by_default(
    tmp_path,
    monkeypatch,
    resource_dir_name,
):
    from pytest_dsl.mcp.server import (
        MCPKeywordServer,
        build_parser,
        run_server_from_args,
    )

    resources_dir = tmp_path / resource_dir_name
    resources_dir.mkdir()
    (resources_dir / "gui.resource").write_text(
        "\n".join([
            '@name: "GUI资源"',
            "",
            "function GUI测试关键字 (输入) do",
            "    return ${输入}",
            "end",
            "",
        ]),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    resource_tool_name = MCPKeywordServer.keyword_tool_name("GUI测试关键字")
    input_stream = io.StringIO("\n".join([
        json.dumps({
            "jsonrpc": "2.0",
            "id": 31,
            "method": "tools/list",
        }, ensure_ascii=False),
        json.dumps({
            "jsonrpc": "2.0",
            "id": 32,
            "method": "tools/call",
            "params": {
                "name": resource_tool_name,
                "arguments": {"输入": "ok"},
            },
        }, ensure_ascii=False),
        "",
    ]))
    output_stream = io.StringIO()
    monkeypatch.setattr("sys.stdin", input_stream)
    monkeypatch.setattr("sys.stdout", output_stream)

    assert run_server_from_args(build_parser().parse_args([])) == 0

    response, call_response = [
        json.loads(line) for line in output_stream.getvalue().splitlines()
    ]
    tools = response["result"]["tools"]
    resource_tool = next(
        tool for tool in tools
        if tool["title"] == "GUI测试关键字"
    )
    assert resource_tool["name"] == resource_tool_name
    assert resource_tool["inputSchema"]["required"] == ["输入"]
    assert call_response["result"]["isError"] is False
    assert call_response["result"]["structuredContent"]["status"] == "PASS"
    assert call_response["result"]["structuredContent"]["return"]["result"] == "ok"


def test_mcp_keyword_tool_name_falls_back_to_stable_hash_for_non_ascii_names():
    from pytest_dsl.mcp.server import MCPKeywordServer

    keyword_name = "打印"
    digest = hashlib.sha1(keyword_name.encode("utf-8")).hexdigest()[:12]

    assert (
        MCPKeywordServer.keyword_tool_name(keyword_name)
        == f"pytest_dsl_keyword__keyword_{digest}"
    )


def test_mcp_http_service_handles_jsonrpc_post_and_notifications():
    from pytest_dsl.mcp.server import MCPKeywordServer, create_http_server

    _register_sample_keyword()
    mcp_server = MCPKeywordServer()
    http_server = create_http_server("127.0.0.1", 0, "/mcp", mcp_server)
    thread = threading.Thread(target=http_server.serve_forever, daemon=True)
    thread.start()
    host, port = http_server.server_address

    try:
        initialize_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "http-test", "version": "1"},
            },
        }
        init_response = _post_mcp(host, port, "/mcp", initialize_payload)
        assert init_response.status == 200
        assert init_response.headers["content-type"].startswith("application/json")
        init_body = json.loads(init_response.read().decode("utf-8"))
        assert init_body["result"]["serverInfo"]["name"] == "pytest-dsl"

        notification_response = _post_mcp(
            host,
            port,
            "/mcp",
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        assert notification_response.status == 202
        assert notification_response.read() == b""

        tools_response = _post_mcp(
            host,
            port,
            "/mcp",
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        )
        assert tools_response.status == 200
        tools_body = json.loads(tools_response.read().decode("utf-8"))
        tool_names = {
            tool["name"] for tool in tools_body["result"]["tools"]
        }
        assert "pytest_dsl_list_keywords" in tool_names
        assert "pytest_dsl_keyword__sample_add" in tool_names

        not_found = _post_mcp(host, port, "/wrong", initialize_payload)
        assert not_found.status == 404
    finally:
        http_server.shutdown()
        http_server.server_close()
        thread.join(timeout=3)


def test_mcp_parser_accepts_http_service_options():
    from pytest_dsl.mcp.server import build_parser

    args = build_parser().parse_args([
        "--transport", "http",
        "--host", "127.0.0.1",
        "--port", "8765",
        "--path", "/mcp",
    ])

    assert args.transport == "http"
    assert args.host == "127.0.0.1"
    assert args.port == 8765
    assert args.path == "/mcp"


def test_pytest_dsl_cli_mcp_command_accepts_http_service_options(monkeypatch):
    from pytest_dsl import cli

    monkeypatch.setattr("sys.argv", [
        "pytest-dsl",
        "mcp",
        "--transport", "http",
        "--host", "127.0.0.1",
        "--port", "8765",
        "--path", "/mcp",
        "--no-keyword-tools",
    ])

    args = cli.parse_args()

    assert args.command == "mcp"
    assert args.transport == "http"
    assert args.host == "127.0.0.1"
    assert args.port == 8765
    assert args.path == "/mcp"
    assert args.no_keyword_tools is True


def _post_mcp(host, port, path, payload):
    connection = http.client.HTTPConnection(host, port, timeout=5)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    connection.request(
        "POST",
        path,
        body=body,
        headers={
            "content-type": "application/json",
            "accept": "application/json, text/event-stream",
        },
    )
    return connection.getresponse()
