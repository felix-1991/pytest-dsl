"""MCP stdio server exposing pytest-dsl keyword capabilities."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
import re
import sys
import urllib.parse
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Dict, Iterable, List, Optional

from pytest_dsl.core.keyword_manager import keyword_manager
from pytest_dsl.remote.keyword_server import (
    RemoteKeywordServer,
    _auto_load_extensions,
    _load_extensions,
)


PROTOCOL_VERSION = "2025-06-18"
JSONRPC_VERSION = "2.0"
KEYWORD_TOOL_PREFIX = "pytest_dsl_keyword__"
PROJECT_RESOURCE_DIR_NAMES = ("resources", "resource")
ANY_JSON_SCHEMA_TYPE = [
    "string",
    "number",
    "integer",
    "boolean",
    "object",
    "array",
    "null",
]


class MCPError(Exception):
    """JSON-RPC error raised while handling an MCP request."""

    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class MCPKeywordServer:
    """Small MCP JSON-RPC server backed by pytest-dsl keyword execution."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_concurrency: int = 20,
        protocol_version: str = PROTOCOL_VERSION,
        expose_keyword_tools: bool = True,
    ):
        self.api_key = api_key
        self.protocol_version = protocol_version
        self.expose_keyword_tools = expose_keyword_tools
        self.keyword_service = RemoteKeywordServer(
            host="localhost",
            port=0,
            api_key=api_key,
            max_concurrency=max_concurrency,
            register_shutdown_handlers=False,
        )

    @classmethod
    def keyword_tool_name(cls, keyword_name: str) -> str:
        """Return the stable MCP tool name for a pytest-dsl keyword."""
        raw_name = str(keyword_name)
        ascii_name = re.sub(r"[^A-Za-z0-9_-]+", "_", raw_name)
        ascii_name = re.sub(r"_+", "_", ascii_name).strip("_-").lower()
        if not ascii_name:
            digest = hashlib.sha1(raw_name.encode("utf-8")).hexdigest()[:12]
            ascii_name = f"keyword_{digest}"
        return f"{KEYWORD_TOOL_PREFIX}{ascii_name}"

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle one JSON-RPC request or notification."""
        request_id = request.get("id")
        method = request.get("method")

        if not isinstance(method, str):
            return self._error_response(request_id, -32600, "Invalid Request")

        if method.startswith("notifications/"):
            return None

        try:
            if method == "initialize":
                result = self._initialize_result()
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": self.list_tools()}
            elif method == "tools/call":
                result = self.call_tool(request.get("params") or {})
            elif method == "shutdown":
                result = {}
            else:
                raise MCPError(-32601, f"Method not found: {method}")
            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": request_id,
                "result": result,
            }
        except MCPError as exc:
            return self._error_response(
                request_id, exc.code, exc.message, exc.data)
        except Exception as exc:
            return self._error_response(request_id, -32603, str(exc))

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return MCP tools exposed by pytest-dsl."""
        tools = self._meta_tools()
        if self.expose_keyword_tools:
            for tool_name, keyword_name in self._keyword_tool_map().items():
                tools.append(self._keyword_to_tool(tool_name, keyword_name))
        return tools

    def call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an MCP tool call."""
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(tool_name, str):
            raise MCPError(-32602, "tools/call requires a string name")
        if not isinstance(arguments, dict):
            raise MCPError(-32602, "tools/call arguments must be an object")

        if tool_name == "pytest_dsl_list_keywords":
            return self._call_list_keywords(arguments)
        if tool_name == "pytest_dsl_get_keyword_contract":
            return self._call_get_keyword_contract(arguments)
        if tool_name == "pytest_dsl_run_keyword":
            return self._call_run_keyword(arguments)
        if tool_name == "pytest_dsl_set_shared_variable":
            return self._tool_result(self.keyword_service.set_shared_variable(
                arguments.get("name"), arguments.get("value"), self.api_key))
        if tool_name == "pytest_dsl_get_shared_variable":
            return self._tool_result(self.keyword_service.get_shared_variable(
                arguments.get("name"), self.api_key))
        if tool_name == "pytest_dsl_list_shared_variables":
            return self._tool_result(
                self.keyword_service.list_shared_variables(self.api_key))

        keyword_name = self._keyword_tool_map().get(tool_name)
        if keyword_name:
            return self._execute_keyword_tool(keyword_name, arguments)

        raise MCPError(-32602, f"Unknown tool: {tool_name}")

    def run_stdio(
        self,
        input_stream=None,
        output_stream=None,
    ) -> int:
        """Run newline-delimited JSON-RPC over stdio streams."""
        input_stream = input_stream or sys.stdin
        output_stream = output_stream or sys.stdout

        for raw_line in input_stream:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            response = self.handle_raw_message(raw_line)
            if response is None:
                continue
            output_stream.write(
                json.dumps(response, ensure_ascii=False) + "\n")
            output_stream.flush()
        return 0

    def handle_raw_message(self, raw_message: str) -> Optional[Any]:
        """Handle one raw JSON-RPC message and return the JSON response."""
        try:
            payload = json.loads(raw_message)
        except json.JSONDecodeError as exc:
            return self._error_response(None, -32700, "Parse error", str(exc))

        if isinstance(payload, list):
            responses = [
                response
                for response in (self.handle_request(item) for item in payload)
                if response is not None
            ]
            return responses or None
        if not isinstance(payload, dict):
            return self._error_response(None, -32600, "Invalid Request")
        return self.handle_request(payload)

    def _initialize_result(self) -> Dict[str, Any]:
        return {
            "protocolVersion": self.protocol_version,
            "capabilities": {
                "tools": {
                    "listChanged": False,
                },
            },
            "serverInfo": {
                "name": "pytest-dsl",
                "version": _package_version(),
            },
        }

    def _meta_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "pytest_dsl_list_keywords",
                "title": "List pytest-dsl keywords",
                "description": (
                    "List loaded pytest-dsl keyword names and optionally "
                    "include their contracts."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "Optional substring filter.",
                        },
                        "include_contracts": {
                            "type": "boolean",
                            "default": False,
                        },
                    },
                    "additionalProperties": False,
                },
                "annotations": self._read_only_annotations(),
            },
            {
                "name": "pytest_dsl_get_keyword_contract",
                "title": "Get pytest-dsl keyword contract",
                "description": "Return parameters, return metadata, and docs.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Original pytest-dsl keyword name.",
                        },
                    },
                    "required": ["name"],
                    "additionalProperties": False,
                },
                "annotations": self._read_only_annotations(),
            },
            {
                "name": "pytest_dsl_run_keyword",
                "title": "Run pytest-dsl keyword",
                "description": "Run any loaded pytest-dsl keyword by name.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Original pytest-dsl keyword name.",
                        },
                        "arguments": {
                            "type": "object",
                            "description": "Keyword arguments keyed by DSL parameter name.",
                        },
                    },
                    "required": ["name", "arguments"],
                    "additionalProperties": False,
                },
                "annotations": self._mutating_annotations(),
            },
            {
                "name": "pytest_dsl_set_shared_variable",
                "title": "Set pytest-dsl shared variable",
                "description": "Set a shared variable for later keyword calls.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "value": {"type": ANY_JSON_SCHEMA_TYPE},
                    },
                    "required": ["name", "value"],
                    "additionalProperties": False,
                },
                "annotations": self._mutating_annotations(),
            },
            {
                "name": "pytest_dsl_get_shared_variable",
                "title": "Get pytest-dsl shared variable",
                "description": "Read a shared variable.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                    "additionalProperties": False,
                },
                "annotations": self._read_only_annotations(),
            },
            {
                "name": "pytest_dsl_list_shared_variables",
                "title": "List pytest-dsl shared variables",
                "description": "List current shared variable names.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                "annotations": self._read_only_annotations(),
            },
        ]

    def _read_only_annotations(self) -> Dict[str, bool]:
        return {
            "readOnlyHint": True,
            "destructiveHint": False,
        }

    def _mutating_annotations(self) -> Dict[str, bool]:
        return {
            "readOnlyHint": False,
            "destructiveHint": False,
        }

    def _keyword_tool_map(self) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        for keyword_name in sorted(keyword_manager._keywords.keys()):
            tool_name = self.keyword_tool_name(keyword_name)
            if tool_name in mapping and mapping[tool_name] != keyword_name:
                digest = hashlib.sha1(
                    keyword_name.encode("utf-8")).hexdigest()[:12]
                tool_name = f"{tool_name}_{digest}"
            mapping[tool_name] = keyword_name
        return mapping

    def _keyword_to_tool(
        self,
        tool_name: str,
        keyword_name: str,
    ) -> Dict[str, Any]:
        contract = self.keyword_service.get_keyword_contract(keyword_name)
        documentation = contract.get("documentation") or ""
        description = documentation.splitlines()[0] if documentation else (
            f"Run pytest-dsl keyword: {keyword_name}"
        )
        return {
            "name": tool_name,
            "title": keyword_name,
            "description": description,
            "inputSchema": self._keyword_input_schema(contract),
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": False,
            },
        }

    def _keyword_input_schema(self, contract: Dict[str, Any]) -> Dict[str, Any]:
        properties: Dict[str, Any] = {}
        required: List[str] = []
        for parameter in contract.get("parameters") or []:
            name = parameter.get("name")
            if not name or name == "步骤名称":
                continue
            schema = {
                "type": ANY_JSON_SCHEMA_TYPE,
                "description": parameter.get("description") or "",
            }
            if parameter.get("default") is not None:
                schema["default"] = parameter.get("default")
            else:
                required.append(name)
            properties[name] = schema

        schema = {
            "type": "object",
            "properties": properties,
            "additionalProperties": True,
        }
        if required:
            schema["required"] = required
        return schema

    def _call_list_keywords(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        name_filter = str(arguments.get("filter") or "")
        include_contracts = bool(arguments.get("include_contracts"))
        names = sorted(keyword_manager._keywords.keys())
        if name_filter:
            names = [name for name in names if name_filter in name]

        payload: Dict[str, Any] = {
            "keywords": names,
            "count": len(names),
        }
        if include_contracts:
            payload["contracts"] = [
                self.keyword_service.get_keyword_contract(name)
                for name in names
            ]
        if self.expose_keyword_tools:
            tool_map = self._keyword_tool_map()
            payload["mcp_tools"] = {
                keyword_name: tool_name
                for tool_name, keyword_name in tool_map.items()
                if keyword_name in names
            }
        return self._tool_result(payload)

    def _call_get_keyword_contract(
        self,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        keyword_name = arguments.get("name")
        if not isinstance(keyword_name, str) or not keyword_name:
            raise MCPError(-32602, "Keyword name is required")
        contract = self.keyword_service.get_keyword_contract(keyword_name)
        if not contract:
            return self._tool_result({
                "status": "FAIL",
                "error": f"Unknown keyword: {keyword_name}",
            }, is_error=True)
        return self._tool_result(contract)

    def _call_run_keyword(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        keyword_name = arguments.get("name")
        keyword_args = arguments.get("arguments")
        if not isinstance(keyword_name, str) or not keyword_name:
            raise MCPError(-32602, "Keyword name is required")
        if not isinstance(keyword_args, dict):
            raise MCPError(-32602, "Keyword arguments must be an object")
        return self._execute_keyword_tool(keyword_name, keyword_args)

    def _execute_keyword_tool(
        self,
        keyword_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        with contextlib.redirect_stdout(io.StringIO()):
            result = self.keyword_service.run_keyword(
                keyword_name, dict(arguments), self.api_key)
        return self._tool_result(
            result,
            is_error=(result.get("status") != "PASS"),
        )

    def _tool_result(
        self,
        payload: Dict[str, Any],
        is_error: bool = False,
    ) -> Dict[str, Any]:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        payload, ensure_ascii=False, sort_keys=True),
                },
            ],
            "structuredContent": payload,
            "isError": is_error,
        }

    def _error_response(
        self,
        request_id: Any,
        code: int,
        message: str,
        data: Any = None,
    ) -> Dict[str, Any]:
        error = {
            "code": code,
            "message": message,
        }
        if data is not None:
            error["data"] = data
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "error": error,
        }


def _package_version() -> str:
    try:
        return version("pytest-dsl")
    except PackageNotFoundError:
        return "0.0.0"


def load_project_resources(project_root: Optional[str] = None) -> None:
    """Load project .resource files so their keywords become MCP tools."""
    root = os.path.abspath(project_root or os.getcwd())
    from pytest_dsl.core.custom_keyword_manager import custom_keyword_manager

    for resource_dir in _iter_project_resource_dirs(root):
        custom_keyword_manager.add_resource_path(resource_dir)
        for resource_file in _iter_resource_files(resource_dir):
            custom_keyword_manager.load_resource_file(resource_file)


def _iter_project_resource_dirs(project_root: str) -> Iterable[str]:
    for dirname in PROJECT_RESOURCE_DIR_NAMES:
        resource_dir = os.path.join(project_root, dirname)
        if os.path.isdir(resource_dir):
            yield resource_dir


def _iter_resource_files(resource_dir: str) -> Iterable[str]:
    for current_dir, dirnames, filenames in os.walk(resource_dir):
        dirnames.sort()
        for filename in sorted(filenames):
            if filename.endswith(".resource"):
                yield os.path.join(current_dir, filename)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Start pytest-dsl as an MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="MCP transport to use: stdio (default) or http service.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP service host when --transport http is used.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="HTTP service port when --transport http is used.",
    )
    parser.add_argument(
        "--path",
        default="/mcp",
        help="HTTP MCP endpoint path when --transport http is used.",
    )
    parser.add_argument(
        "--extensions",
        help="Extra extension module paths or module names, separated by commas.",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=20,
        help="Maximum concurrent keyword executions.",
    )
    parser.add_argument(
        "--no-keyword-tools",
        action="store_true",
        help="Expose only meta tools instead of one MCP tool per keyword.",
    )
    return parser


def create_http_server(
    host: str,
    port: int,
    path: str,
    mcp_server: MCPKeywordServer,
) -> ThreadingHTTPServer:
    endpoint_path = _normalize_http_path(path)

    class MCPHTTPHandler(BaseHTTPRequestHandler):
        server_version = "pytest-dsl-mcp/1.0"

        def do_POST(self):
            if self._request_path() != endpoint_path:
                self._send_json_status(404, {"error": "Not found"})
                return

            content_length = self.headers.get("content-length")
            try:
                length = int(content_length or "0")
            except ValueError:
                self._send_json_status(400, {"error": "Invalid content-length"})
                return

            raw_body = self.rfile.read(length).decode("utf-8")
            response = mcp_server.handle_raw_message(raw_body)
            if response is None:
                self.send_response(202)
                self.send_header("content-length", "0")
                self.end_headers()
                return

            self._send_json_status(200, response)

        def do_GET(self):
            if self._request_path() == "/healthz":
                self._send_json_status(200, {
                    "status": "ok",
                    "transport": "http",
                    "endpoint": endpoint_path,
                })
                return

            if self._request_path() == endpoint_path:
                self._send_json_status(405, {
                    "error": "Use POST for JSON-RPC requests",
                })
                return

            self._send_json_status(404, {"error": "Not found"})

        def do_OPTIONS(self):
            self.send_response(204)
            self._send_common_headers(content_length=0)
            self.end_headers()

        def _request_path(self):
            return urllib.parse.urlparse(self.path).path

        def _send_json_status(self, status_code: int, payload: Dict[str, Any]):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status_code)
            self._send_common_headers(content_length=len(body))
            self.send_header("content-type", "application/json; charset=utf-8")
            self.end_headers()
            if body:
                self.wfile.write(body)

        def _send_common_headers(self, content_length: int):
            self.send_header("content-length", str(content_length))
            self.send_header("access-control-allow-origin", "*")
            self.send_header("access-control-allow-methods", "POST, GET, OPTIONS")
            self.send_header(
                "access-control-allow-headers",
                "content-type, accept, mcp-protocol-version",
            )

        def log_message(self, format, *args):
            print(
                f"{self.address_string()} - {format % args}",
                file=sys.stderr,
            )

    return ThreadingHTTPServer((host, port), MCPHTTPHandler)


def _normalize_http_path(path: str) -> str:
    if not path:
        return "/mcp"
    return path if path.startswith("/") else f"/{path}"


def run_server_from_args(args) -> int:
    protocol_stdout = sys.stdout
    with contextlib.redirect_stdout(sys.stderr):
        if getattr(args, "extensions", None):
            _load_extensions(args.extensions)
        _auto_load_extensions()
        server = MCPKeywordServer(
            max_concurrency=getattr(args, "max_concurrency", 20),
            expose_keyword_tools=not getattr(args, "no_keyword_tools", False),
        )
        load_project_resources()

    if getattr(args, "transport", "stdio") == "http":
        return run_http_service_from_args(args, server)

    return server.run_stdio(sys.stdin, protocol_stdout)


def run_http_service_from_args(args, server: MCPKeywordServer) -> int:
    http_server = create_http_server(
        getattr(args, "host", "127.0.0.1"),
        getattr(args, "port", 8765),
        getattr(args, "path", "/mcp"),
        server,
    )
    host, port = http_server.server_address
    endpoint = _normalize_http_path(getattr(args, "path", "/mcp"))
    print(
        f"pytest-dsl MCP HTTP service listening on http://{host}:{port}{endpoint}",
        file=sys.stderr,
    )
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("pytest-dsl MCP HTTP service interrupted", file=sys.stderr)
    finally:
        http_server.server_close()
    return 0


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return run_server_from_args(args)


if __name__ == "__main__":
    sys.exit(main())
