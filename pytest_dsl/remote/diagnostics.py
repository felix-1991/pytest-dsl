"""Thread-local diagnostics capture for remote keyword execution."""

import logging
import os
import re
import sys
import threading
import time
import traceback as traceback_module
import uuid
from typing import Any, Dict, List, Optional


DEFAULT_MAX_CHARS = 20000
DEFAULT_MAX_LOG_RECORDS = 200
DEFAULT_LOG_LEVEL = "INFO"

_capture_state = threading.local()
_stream_install_lock = threading.RLock()
_root_level_lock = threading.RLock()
_active_root_level_requests = 0
_root_original_level = None


_SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?i)\b("
    r"authorization|token|secret|password|api[-_]?key|apikey|x-api-key|"
    r"cookie|set-cookie|认证|授权|令牌|密钥|密码|口令"
    r")\b\s*([:=])\s*([^\s,;]+)"
)


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if not raw_value:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return value if value > 0 else default


def _env_log_level() -> int:
    raw_value = os.getenv("PYTEST_DSL_REMOTE_DIAG_LOG_LEVEL",
                          DEFAULT_LOG_LEVEL)
    return getattr(logging, str(raw_value).strip().upper(), logging.INFO)


def redact_diagnostic_text(text: Any) -> str:
    """Redact common secret assignments from diagnostic free text."""
    if text is None:
        return ""
    text = str(text)

    def replace(match):
        return f"{match.group(1)}{match.group(2)} ***REDACTED***"

    return _SENSITIVE_ASSIGNMENT_RE.sub(replace, text)


class _LimitedTextBuffer:
    def __init__(self, max_chars: int):
        self.max_chars = max_chars
        self.parts: List[str] = []
        self.length = 0
        self.truncated = False

    def write(self, text: Any) -> None:
        if text is None:
            return
        text = str(text)
        if not text:
            return

        remaining = self.max_chars - self.length
        if remaining <= 0:
            self.truncated = True
            return

        if len(text) > remaining:
            self.parts.append(text[:remaining])
            self.length += remaining
            self.truncated = True
            return

        self.parts.append(text)
        self.length += len(text)

    def value(self) -> str:
        return redact_diagnostic_text("".join(self.parts))


def _capture_stack() -> List["RemoteExecutionCapture"]:
    stack = getattr(_capture_state, "stack", None)
    if stack is None:
        stack = []
        _capture_state.stack = stack
    return stack


def _active_capture() -> Optional["RemoteExecutionCapture"]:
    stack = getattr(_capture_state, "stack", None)
    if not stack:
        return None
    return stack[-1]


class _ThreadLocalTeeStream:
    """A process-wide stream proxy that captures only the current thread."""

    _pytest_dsl_thread_capture_proxy = True

    def __init__(self, wrapped, stream_name: str):
        self._wrapped = wrapped
        self._stream_name = stream_name

    def write(self, text):
        active = _active_capture()
        if active is not None:
            active.write_stream(self._stream_name, text)

        result = self._wrapped.write(text)
        return len(text) if result is None else result

    def flush(self):
        return self._wrapped.flush()

    def isatty(self):
        return self._wrapped.isatty()

    @property
    def encoding(self):
        return getattr(self._wrapped, "encoding", None)

    @property
    def errors(self):
        return getattr(self._wrapped, "errors", None)

    def fileno(self):
        return self._wrapped.fileno()

    def __getattr__(self, item):
        return getattr(self._wrapped, item)


def install_thread_capture_streams() -> None:
    """Install stdout/stderr proxies once for thread-local capture."""
    with _stream_install_lock:
        if not getattr(sys.stdout, "_pytest_dsl_thread_capture_proxy", False):
            sys.stdout = _ThreadLocalTeeStream(sys.stdout, "stdout")
        if not getattr(sys.stderr, "_pytest_dsl_thread_capture_proxy", False):
            sys.stderr = _ThreadLocalTeeStream(sys.stderr, "stderr")


class _CaptureLogHandler(logging.Handler):
    def __init__(self, capture: "RemoteExecutionCapture"):
        super().__init__(logging.NOTSET)
        self.capture = capture

    def emit(self, record):
        if record.thread != self.capture.thread_id:
            return
        try:
            message = record.getMessage()
        except Exception:
            message = "<log message unavailable>"

        entry: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": redact_diagnostic_text(message),
        }
        if record.exc_info:
            entry["traceback"] = redact_diagnostic_text(
                "".join(traceback_module.format_exception(*record.exc_info))
            )
        self.capture.write_log(entry)


def _acquire_root_log_level(level: int) -> None:
    global _active_root_level_requests, _root_original_level
    root_logger = logging.getLogger()
    with _root_level_lock:
        if _active_root_level_requests == 0:
            _root_original_level = root_logger.level
        _active_root_level_requests += 1
        if root_logger.level > level:
            root_logger.setLevel(level)


def _release_root_log_level() -> None:
    global _active_root_level_requests, _root_original_level
    root_logger = logging.getLogger()
    with _root_level_lock:
        if _active_root_level_requests > 0:
            _active_root_level_requests -= 1
        if _active_root_level_requests == 0 and _root_original_level is not None:
            root_logger.setLevel(_root_original_level)
            _root_original_level = None


class RemoteExecutionCapture:
    """Capture remote keyword output for the current request thread."""

    def __init__(self, keyword: str, request_id: str = None,
                 max_chars: int = None, max_log_records: int = None,
                 log_level: int = None):
        self.keyword = keyword
        self.request_id = request_id or uuid.uuid4().hex
        self.max_chars = max_chars or _env_int(
            "PYTEST_DSL_REMOTE_DIAG_MAX_CHARS", DEFAULT_MAX_CHARS)
        self.max_log_records = max_log_records or _env_int(
            "PYTEST_DSL_REMOTE_DIAG_MAX_LOG_RECORDS",
            DEFAULT_MAX_LOG_RECORDS)
        self.log_level = log_level if log_level is not None else _env_log_level()
        self.stdout = _LimitedTextBuffer(self.max_chars)
        self.stderr = _LimitedTextBuffer(self.max_chars)
        self.logs: List[Dict[str, Any]] = []
        self.logs_truncated = False
        self.thread_id = None
        self.started_at = None
        self._handler = None

    def __enter__(self):
        install_thread_capture_streams()
        self.thread_id = threading.get_ident()
        self.started_at = time.monotonic()
        _capture_stack().append(self)
        self._handler = _CaptureLogHandler(self)
        logging.getLogger().addHandler(self._handler)
        _acquire_root_log_level(self.log_level)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._handler is not None:
            logging.getLogger().removeHandler(self._handler)
            self._handler = None
        _release_root_log_level()

        stack = _capture_stack()
        if stack and stack[-1] is self:
            stack.pop()
        elif self in stack:
            stack.remove(self)
        return False

    def write_stream(self, stream_name: str, text: Any) -> None:
        if stream_name == "stderr":
            self.stderr.write(text)
        else:
            self.stdout.write(text)

    def write_log(self, entry: Dict[str, Any]) -> None:
        if len(self.logs) >= self.max_log_records:
            self.logs_truncated = True
            return
        self.logs.append(entry)

    def to_payload(self, status: str, error: str = None,
                   traceback_lines: List[str] = None) -> Dict[str, Any]:
        elapsed_ms = 0.0
        if self.started_at is not None:
            elapsed_ms = (time.monotonic() - self.started_at) * 1000

        safe_traceback = [
            redact_diagnostic_text(line) for line in (traceback_lines or [])
        ]
        return {
            "version": 1,
            "request_id": self.request_id,
            "keyword": self.keyword,
            "status": status,
            "error": redact_diagnostic_text(error) if error else "",
            "elapsed_ms": round(elapsed_ms, 3),
            "thread_id": str(self.thread_id) if self.thread_id is not None else "",
            "stdout": self.stdout.value(),
            "stderr": self.stderr.value(),
            "logs": list(self.logs),
            "traceback": safe_traceback,
            "truncated": {
                "stdout": self.stdout.truncated,
                "stderr": self.stderr.truncated,
                "logs": self.logs_truncated,
            },
        }


def diagnostics_has_output(diagnostics: Dict[str, Any]) -> bool:
    if not isinstance(diagnostics, dict):
        return False
    if diagnostics.get("stdout") or diagnostics.get("stderr"):
        return True
    if diagnostics.get("logs") or diagnostics.get("traceback"):
        return True
    return False
