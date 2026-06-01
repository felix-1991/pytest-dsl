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

# Node types that represent entering a keyword/function body.
# Stepping over these nodes skips all statements inside the body
# so the debugger does not descend into user-defined keywords.
_KEYWORD_CALL_TYPES = frozenset({
    "KeywordCall",
    "RemoteKeywordCall",
    "AssignmentKeywordCall",
    "AssignmentRemoteKeywordCall",
})


class StepDebugger:
    """Blocks DSL execution between tracked executable steps."""

    def __init__(self, pause_from_line=None):
        self.auto_continue = False
        self.tracked_steps = set()
        self.pause_from_line = normalize_pause_from_line(pause_from_line)
        # Nesting depth for "step over" keyword calls.
        # When > 0 the debugger is inside a keyword body and all
        # inner step events are suppressed.
        self._keyword_call_depth = 0

    def attach(self, tracker):
        tracker.register_callback("step_start", self.on_step_start)
        tracker.register_callback("step_finish", self.on_step_finish)

    def on_step_start(self, step, **_kwargs):
        if step.node_type not in DEBUG_STEP_NODE_TYPES:
            return
        if self.pause_from_line and step.line_number < self.pause_from_line:
            return

        # Step-over keyword calls: pause on the call site itself
        # (at depth 0), then suppress all inner steps until the
        # keyword body finishes.
        if step.node_type in _KEYWORD_CALL_TYPES:
            if self._keyword_call_depth == 0:
                # Outermost keyword call — pause here, step over.
                self._keyword_call_depth += 1
            else:
                # Nested keyword call inside another keyword body
                # — skip and track the nesting level.
                self._keyword_call_depth += 1
                return
        elif self._keyword_call_depth > 0:
            # Non-keyword step inside a keyword body — skip.
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
        # Decrement keyword-call nesting depth when a boundary
        # node finishes, regardless of whether it was tracked.
        if step.node_type in _KEYWORD_CALL_TYPES:
            self._keyword_call_depth = max(0, self._keyword_call_depth - 1)

        if id(step) not in self.tracked_steps:
            return
        self.tracked_steps.discard(id(step))

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
