"""Step-debug support for pytest-dsl workbench runtimes."""

import sys

from pytest_dsl.workbench.protocol import emit_event


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
