"""Small command helpers used by the local Electron GUI."""

import argparse
import json
import os
import sys
from pathlib import Path

from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import parse_with_error_handling


GUI_EVENT_PREFIX = "__PYTEST_DSL_GUI_EVENT__"
DEBUG_STEP_NODE_TYPES = {
    "Assignment",
    "AssignmentKeywordCall",
    "AssignmentRemoteKeywordCall",
    "KeywordCall",
    "RemoteKeywordCall",
    "ForLoop",
    "ForRangeLoop",
    "ForItemLoop",
    "ForKeyValueLoop",
    "IfStatement",
    "Retry",
    "Return",
    "Break",
    "Continue",
}


def syntax_check(file_path: str) -> int:
    """Parse a DSL file and print syntax diagnostics."""
    target = Path(file_path)
    try:
        content = target.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"读取失败: {target}: {exc}", flush=True)
        return 1

    try:
        _ast, errors = parse_with_error_handling(content, lexer=get_lexer())
    except Exception as exc:
        print(f"语法检查异常: {exc}", flush=True)
        return 1

    if errors:
        print(f"语法检查失败: {target}", flush=True)
        for error in errors:
            line = error.get("line")
            column = error.get("column")
            message = error.get("message", "未知语法错误")
            location = f"line {line}"
            if column is not None:
                location += f", column {column}"
            print(f"{location}: {message}", flush=True)
        return 1

    print(f"语法检查通过: {target}", flush=True)
    return 0


def debug_run(file_path: str, yaml_vars=None, pause_from_line=None) -> int:
    """Execute a DSL file in step-debug mode."""
    yaml_vars = yaml_vars or []
    target = Path(file_path)
    try:
        content = target.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"读取失败: {target}: {exc}", flush=True)
        return 1

    try:
        _load_runtime(yaml_vars)

        from pytest_dsl.core.dsl_executor import DSLExecutor
        from pytest_dsl.core.execution_tracker import (
            get_or_create_tracker,
            remove_tracker,
        )

        dsl_id = str(target.resolve())
        tracker = get_or_create_tracker(dsl_id)
        debugger = StepDebugger(pause_from_line=pause_from_line)
        debugger.attach(tracker)

        try:
            DSLExecutor(enable_hooks=True, enable_tracking=True).execute_from_content(
                content,
                dsl_id=dsl_id,
            )
        finally:
            remove_tracker(dsl_id)
        return 0
    except KeyboardInterrupt:
        emit_event({
            "type": "debug_step",
            "phase": "stopped",
            "line": None,
            "nodeType": None,
            "description": "调试已停止",
            "status": "stopped",
        })
        return 130
    except Exception as exc:
        print(f"调试执行失败: {exc}", flush=True)
        return 1


class StepDebugger:
    """Blocks DSL execution between tracked executable steps."""

    def __init__(self, pause_from_line=None):
        self.auto_continue = False
        self.tracked_steps = set()
        self.pause_from_line = normalize_pause_from_line(pause_from_line)

    def attach(self, tracker):
        tracker.register_callback("step_start", self.on_step_start)
        tracker.register_callback("step_finish", self.on_step_finish)

    def on_step_start(self, step, **_kwargs):
        if step.node_type not in DEBUG_STEP_NODE_TYPES:
            return
        if self.pause_from_line and step.line_number < self.pause_from_line:
            return

        self.tracked_steps.add(id(step))
        emit_event({
            "type": "debug_step",
            "phase": "start",
            "line": step.line_number,
            "nodeType": step.node_type,
            "description": step.description,
            "status": step.status.value,
        })

        if not self.auto_continue:
            command = read_debug_command()
            if command == "continue":
                self.auto_continue = True
            elif command == "stop":
                raise KeyboardInterrupt()

    def on_step_finish(self, step, **_kwargs):
        if id(step) not in self.tracked_steps:
            return

        emit_event({
            "type": "debug_step",
            "phase": "finish",
            "line": step.line_number,
            "nodeType": step.node_type,
            "description": step.description,
            "status": "failed" if step.error else "success",
            "error": step.error,
            "duration": step.duration,
        })


def read_debug_command() -> str:
    command = sys.stdin.readline()
    if not command:
        return "continue"
    normalized = command.strip().lower()
    if normalized in {"next", "continue", "stop"}:
        return normalized
    return "next"


def normalize_pause_from_line(value):
    if value is None:
        return None
    try:
        line = int(value)
    except (TypeError, ValueError):
        return None
    return line if line > 1 else None


def emit_event(payload) -> None:
    print(
        GUI_EVENT_PREFIX + json.dumps(payload, ensure_ascii=False),
        flush=True,
    )


def _load_runtime(yaml_vars):
    from pytest_dsl.core.keyword_loader import load_all_keywords
    from pytest_dsl.core.yaml_loader import load_yaml_variables_from_args

    class Args:
        yaml_vars_dir = None

        def __init__(self, yaml_files):
            self.yaml_vars = yaml_files

    load_all_keywords(include_remote=True)
    environment = (
        os.environ.get("PYTEST_DSL_ENVIRONMENT") or
        os.environ.get("ENVIRONMENT")
    )
    load_yaml_variables_from_args(
        yaml_files=yaml_vars,
        yaml_vars_dir=None,
        project_root=os.getcwd(),
        environment=environment,
        auto_load_default=not bool(yaml_vars),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="pytest-dsl GUI helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    syntax_parser = subparsers.add_parser("syntax", help="检查 DSL 语法")
    syntax_parser.add_argument("path", help="要检查的 DSL 文件路径")

    debug_parser = subparsers.add_parser("debug", help="按步骤调试 DSL")
    debug_parser.add_argument("path", help="要调试的 DSL 文件路径")
    debug_parser.add_argument(
        "--yaml-vars",
        action="append",
        default=[],
        help="YAML变量文件路径，可以指定多个文件",
    )
    debug_parser.add_argument(
        "--pause-from-line",
        type=int,
        default=None,
        help="执行前置步骤后，从指定源码行开始暂停调试",
    )

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "syntax":
        return syntax_check(args.path)
    if args.command == "debug":
        return debug_run(
            args.path,
            yaml_vars=args.yaml_vars,
            pause_from_line=args.pause_from_line,
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
