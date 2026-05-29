"""Public workbench command helpers for local GUI/editor integrations."""

import argparse
import json
import os
import sys
from pathlib import Path

from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import format_parse_errors, parse_with_error_handling
from pytest_dsl.workbench.debug import (
    DEBUG_STEP_NODE_TYPES,
    StepDebugger,
    normalize_pause_from_line,
    read_debug_command,
)
from pytest_dsl.workbench.protocol import (
    GUI_EVENT_PREFIX,
    capabilities_payload,
    emit_event,
)


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
        print(format_parse_errors(errors, file_path=str(target)), flush=True)
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


def capabilities() -> int:
    print(json.dumps(capabilities_payload(), ensure_ascii=False), flush=True)
    return 0


def _load_runtime(yaml_vars):
    from pytest_dsl.core.keyword_loader import load_all_keywords
    from pytest_dsl.core.yaml_loader import load_yaml_variables_from_args

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
    parser = argparse.ArgumentParser(description="pytest-dsl workbench runtime")
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

    subparsers.add_parser("capabilities", help="输出 workbench runtime 能力")
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
    if args.command == "capabilities":
        return capabilities()
    return 1


if __name__ == "__main__":
    sys.exit(main())
