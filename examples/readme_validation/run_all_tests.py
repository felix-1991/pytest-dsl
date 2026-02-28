#!/usr/bin/env python3
"""README 示例一键验证脚本。

目标：
1) 发现 DSL 语法回归
2) 离线执行 README 示例（通过本地 mock HTTP 替代外网）
3) 发现远程关键字执行回归（自动拉起本地 remote server）
"""

from __future__ import annotations

import argparse
import contextlib
import http.server
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import parse_with_error_handling

SCRIPT_DIR = Path(__file__).resolve().parent

# README 示例执行清单（保留你原本使用习惯）
EXECUTION_FILES = [
    "hello.dsl",
    "basic_syntax.dsl",
    "builtin_keywords.dsl",
    "custom_keywords.dsl",
    "resource_usage.dsl",
    "api_basic.dsl",
    "api_params.dsl",
    "api_capture.dsl",
    "yaml_vars.dsl",
    "variable_access.dsl",
    "assertion_retry.dsl",
    "auth_test.dsl",
    "test_dict_support.dsl",
    "test_if_elif_else.dsl",
    "test_in_operator.dsl",
    "test_logical_operators.dsl",
    "test_contains_operators.dsl",
    "test_break_continue_final.dsl",
    "boolean_demo.dsl",
    "retry_block_every_until.dsl",
    "retry_block_no_modifiers.dsl",
    "retry_block_times.dsl",
    "../test_new_for_loops.dsl",
]

# README 中仅用于 pytest 数据驱动的示例，仍做语法校验
SYNTAX_ONLY_FILES = ["data_driven.dsl"]


class _MockAPIHandler(http.server.BaseHTTPRequestHandler):
    """为 README API 示例提供离线响应。"""

    def _send_json(self, payload, status: int = 200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args):  # noqa: D401
        # 验证脚本保持安静输出
        return

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/posts/1":
            self._send_json(
                {
                    "userId": 1,
                    "id": 1,
                    "title": "sunt aut facere repellat provident occaecati",
                    "body": "offline mock payload",
                }
            )
            return

        if path == "/posts":
            user_id = int(query.get("userId", ["1"])[0])
            limit = int(query.get("_limit", ["10"])[0])
            posts = [
                {
                    "userId": user_id,
                    "id": i,
                    "title": f"post {i}",
                    "body": "offline mock payload",
                }
                for i in range(1, max(limit, 1) + 1)
            ]
            self._send_json(posts)
            return

        if path == "/users/1":
            self._send_json(
                {
                    "id": 1,
                    "name": "Leanne Graham",
                    "email": "leanne@example.com",
                }
            )
            return

        self._send_json({"error": "not found", "path": path}, status=404)


class LocalMockHTTP:
    """本地 HTTP mock 服务器。"""

    def __init__(self):
        self._server: Optional[http.server.ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self.base_url: Optional[str] = None

    def __enter__(self) -> "LocalMockHTTP":
        self._server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _MockAPIHandler)
        host, port = self._server.server_address
        self.base_url = f"http://{host}:{port}"

        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        if self._thread:
            self._thread.join(timeout=2)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_tcp(port: int, timeout: float = 12.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.25)
            try:
                s.connect(("127.0.0.1", port))
                return True
            except OSError:
                time.sleep(0.15)
    return False


@contextlib.contextmanager
def start_remote_server():
    """拉起 pytest-dsl 远程关键字服务并在退出时清理。"""
    port = _find_free_port()
    cmd = [
        sys.executable,
        "-m",
        "pytest_dsl.remote.keyword_server",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=str(SCRIPT_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if not _wait_for_tcp(port):
        stdout, stderr = proc.communicate(timeout=3)
        raise RuntimeError(
            "远程服务启动失败。\n"
            f"命令: {' '.join(cmd)}\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        )

    try:
        yield f"http://127.0.0.1:{port}/"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def _rewrite_content(content: str, replacement_base_url: str) -> str:
    rewritten = content.replace("https://jsonplaceholder.typicode.com", replacement_base_url)
    rewritten = rewritten.replace("${api.base_url}", replacement_base_url)
    return rewritten


def _materialize_temp_dsl(original_file: Path, replacement_base_url: str) -> Path:
    content = original_file.read_text(encoding="utf-8")
    rewritten = _rewrite_content(content, replacement_base_url)

    if rewritten == content:
        return original_file

    fd, temp_path = tempfile.mkstemp(
        prefix=f".tmp_{original_file.stem}_",
        suffix=original_file.suffix,
        dir=str(original_file.parent),
    )
    os.close(fd)
    temp_file = Path(temp_path)
    temp_file.write_text(rewritten, encoding="utf-8")
    return temp_file


def _run_cli(file_path: Path, timeout: int = 90, extra_args: Optional[List[str]] = None) -> Tuple[bool, str]:
    cmd = [sys.executable, "-m", "pytest_dsl.cli", "run", str(file_path)]
    if extra_args:
        cmd.extend(extra_args)

    result = subprocess.run(
        cmd,
        cwd=str(SCRIPT_DIR),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    ok = result.returncode == 0
    output = f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}".strip()
    return ok, output


def syntax_check(files: Iterable[Path]) -> Tuple[int, int, List[str]]:
    passed = 0
    failed = 0
    messages: List[str] = []

    lexer = get_lexer()

    for file_path in sorted(files):
        content = file_path.read_text(encoding="utf-8")
        _, parse_errors = parse_with_error_handling(content, lexer=lexer)
        if not parse_errors:
            passed += 1
            continue

        failed += 1
        err_lines = []
        try:
            display_name = str(file_path.relative_to(SCRIPT_DIR))
        except ValueError:
            display_name = str(file_path)
        for err in parse_errors:
            line = err.get("line", "?")
            message = err.get("message", str(err))
            err_lines.append(f"第{line}行: {message}")
        messages.append(
            f"[语法失败] {display_name}\n" + "\n".join(err_lines)
        )

    return passed, failed, messages


def syntax_check_expected_fail(files: Iterable[Path]) -> Tuple[int, int, List[str]]:
    """语法负例校验：这些文件应当解析失败。"""
    passed = 0
    failed = 0
    messages: List[str] = []

    lexer = get_lexer()

    for file_path in sorted(files):
        content = file_path.read_text(encoding="utf-8")
        _, parse_errors = parse_with_error_handling(content, lexer=lexer)
        if parse_errors:
            passed += 1
            continue

        failed += 1
        messages.append(f"[语法负例失败] {file_path} 预期应解析失败，但实际解析通过")

    return passed, failed, messages


def execute_readme_examples(mock_base_url: str) -> Tuple[int, int, List[str]]:
    passed = 0
    failed = 0
    messages: List[str] = []

    for rel_path in EXECUTION_FILES:
        target = (SCRIPT_DIR / rel_path).resolve()
        if not target.exists():
            failed += 1
            messages.append(f"[执行失败] 文件不存在: {rel_path}")
            continue

        temp_file = _materialize_temp_dsl(target, replacement_base_url=mock_base_url)
        try:
            ok, output = _run_cli(temp_file)
            if ok:
                passed += 1
            else:
                failed += 1
                messages.append(f"[执行失败] {rel_path}\n{output}")
        finally:
            if temp_file != target and temp_file.exists():
                temp_file.unlink()

    return passed, failed, messages


def remote_smoke_test() -> Tuple[int, int, List[str]]:
    passed = 0
    failed = 0
    messages: List[str] = []

    with start_remote_server() as remote_url:
        temp_dir = Path(tempfile.mkdtemp(prefix="remote_smoke_", dir=str(SCRIPT_DIR)))
        try:
            # 1) 注解方式 @remote
            annotation_file = temp_dir / "remote_annotation_smoke.dsl"
            annotation_file.write_text(
                "\n".join(
                    [
                        '@name: "远程注解冒烟"',
                        f'@remote: "{remote_url}" as server',
                        '[打印], 内容: "开始远程注解冒烟"',
                        'server|[打印], 内容: "远程打印正常"',
                        'rand = server|[生成随机数], 最小值: 1, 最大值: 10',
                        '[断言], 条件: "${rand} != \'\'", 消息: "远程随机数为空"',
                    ]
                ),
                encoding="utf-8",
            )
            ok, output = _run_cli(annotation_file)
            if ok:
                passed += 1
            else:
                failed += 1
                messages.append(f"[远程失败] 注解方式\n{output}")

            # 2) YAML remote_servers 方式
            yaml_file = temp_dir / "remote_servers.yaml"
            yaml_file.write_text(
                "\n".join(
                    [
                        "remote_servers:",
                        "  timeout_server:",
                        f"    url: \"{remote_url.rstrip('/')}\"",
                        "    alias: \"timeout_server\"",
                        "    timeout: 10",
                    ]
                ),
                encoding="utf-8",
            )
            yaml_dsl = temp_dir / "remote_yaml_smoke.dsl"
            yaml_dsl.write_text(
                "\n".join(
                    [
                        '@name: "远程YAML配置冒烟"',
                        '[打印], 内容: "开始YAML远程冒烟"',
                        'timeout_server|[等待], 秒数: 1',
                        'timeout_server|[打印], 内容: "YAML远程调用正常"',
                    ]
                ),
                encoding="utf-8",
            )
            ok, output = _run_cli(yaml_dsl, extra_args=["--yaml-vars", str(yaml_file)])
            if ok:
                passed += 1
            else:
                failed += 1
                messages.append(f"[远程失败] YAML方式\n{output}")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return passed, failed, messages


def discover_dsl_files() -> List[Path]:
    files = []
    for entry in SCRIPT_DIR.glob("*.dsl"):
        if entry.name.startswith(".tmp_"):
            continue
        files.append(entry)

    # 保留你原来纳入的 for-loop 示例
    extra = (SCRIPT_DIR / "../test_new_for_loops.dsl").resolve()
    if extra.exists():
        files.append(extra)
    return files


def discover_syntax_case_files(case_type: str) -> List[Path]:
    case_dir = SCRIPT_DIR / "syntax_cases" / case_type
    if not case_dir.exists():
        return []
    return sorted(case_dir.glob("*.dsl"))


def print_section(title: str):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def main() -> int:
    parser = argparse.ArgumentParser(description="README 示例一键验证")
    parser.add_argument("--skip-exec", action="store_true", help="跳过示例执行，仅做语法+远程")
    parser.add_argument("--skip-remote", action="store_true", help="跳过远程冒烟")
    parser.add_argument("--syntax-only", action="store_true", help="仅做语法校验")
    args = parser.parse_args()

    os.chdir(SCRIPT_DIR)

    total_passed = 0
    total_failed = 0
    details: List[str] = []

    print("开始一键验证 README 示例（语法 + 执行 + 远程）")
    print(f"工作目录: {SCRIPT_DIR}")

    # 1) 语法校验
    print_section("1) DSL 语法校验")
    syntax_files = discover_dsl_files()
    syntax_ok, syntax_fail, syntax_msgs = syntax_check(syntax_files)
    total_passed += syntax_ok
    total_failed += syntax_fail
    details.extend(syntax_msgs)
    print(f"语法通过: {syntax_ok}")
    print(f"语法失败: {syntax_fail}")

    # 特殊文件（仅语法）
    special_files = [SCRIPT_DIR / name for name in SYNTAX_ONLY_FILES]
    special_ok, special_fail, special_msgs = syntax_check([p for p in special_files if p.exists()])
    total_passed += special_ok
    total_failed += special_fail
    details.extend(special_msgs)
    if special_files:
        print(f"语法特殊通过: {special_ok}")
        print(f"语法特殊失败: {special_fail}")

    # 语法基线用例（正例/负例）
    syntax_pass_cases = discover_syntax_case_files("pass")
    syntax_fail_cases = discover_syntax_case_files("fail")

    if syntax_pass_cases:
        pass_ok, pass_fail, pass_msgs = syntax_check(syntax_pass_cases)
        total_passed += pass_ok
        total_failed += pass_fail
        details.extend(pass_msgs)
        print(f"语法正例通过: {pass_ok}")
        print(f"语法正例失败: {pass_fail}")

    if syntax_fail_cases:
        fail_ok, fail_fail, fail_msgs = syntax_check_expected_fail(syntax_fail_cases)
        total_passed += fail_ok
        total_failed += fail_fail
        details.extend(fail_msgs)
        print(f"语法负例通过: {fail_ok}")
        print(f"语法负例失败: {fail_fail}")

    if args.syntax_only:
        print_section("最终结果")
        print(f"总通过: {total_passed}")
        print(f"总失败: {total_failed}")
        if details:
            print("\n失败详情:")
            for msg in details:
                print(msg)
        return 1 if total_failed else 0

    # 2) 本地执行校验（离线）
    if not args.skip_exec:
        print_section("2) README 示例执行校验（离线 mock HTTP）")
        with LocalMockHTTP() as mock_http:
            print(f"离线 API mock 地址: {mock_http.base_url}")
            exec_ok, exec_fail, exec_msgs = execute_readme_examples(mock_http.base_url or "")

        total_passed += exec_ok
        total_failed += exec_fail
        details.extend(exec_msgs)
        print(f"执行通过: {exec_ok}")
        print(f"执行失败: {exec_fail}")

    # 3) 远程冒烟
    if not args.skip_remote:
        print_section("3) 远程关键字冒烟校验")
        try:
            remote_ok, remote_fail, remote_msgs = remote_smoke_test()
        except Exception as exc:
            remote_ok, remote_fail, remote_msgs = 0, 1, [f"[远程失败] 无法启动远程服务: {exc}"]

        total_passed += remote_ok
        total_failed += remote_fail
        details.extend(remote_msgs)
        print(f"远程通过: {remote_ok}")
        print(f"远程失败: {remote_fail}")

    print_section("最终结果")
    print(f"总通过: {total_passed}")
    print(f"总失败: {total_failed}")

    if details:
        print("\n失败详情:")
        for msg in details:
            print("-" * 72)
            print(msg)

    if total_failed == 0:
        print("\n全部校验通过。")
        return 0

    print("\n存在失败项，请根据详情修复。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
