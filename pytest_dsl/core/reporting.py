"""Small helpers for concise default reports and verbose diagnostics."""

import json
import os
from typing import Any, Dict, Iterable

import allure


SENSITIVE_KEY_PARTS = (
    "authorization",
    "认证",
    "授权",
    "token",
    "令牌",
    "secret",
    "密钥",
    "password",
    "密码",
    "口令",
    "api-key",
    "apikey",
    "x-api-key",
    "cookie",
    "set-cookie",
)


def is_verbose() -> bool:
    """Return whether detailed DSL diagnostics should be emitted."""
    value = os.getenv("PYTEST_DSL_VERBOSE", "").strip().lower()
    return value in {"1", "true", "yes", "y", "on"}


def is_sensitive_key(key: Any) -> bool:
    key_text = str(key).lower()
    return any(part in key_text for part in SENSITIVE_KEY_PARTS)


def redact_value(value: Any, key: Any = None) -> Any:
    """Return a copy of value with common credential fields redacted."""
    if key is not None and is_sensitive_key(key):
        return "***REDACTED***"

    if isinstance(value, dict):
        return {
            item_key: redact_value(item_value, item_key)
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    return value


def preview_value(value: Any, max_len: int = 160, redact: bool = True,
                  key: Any = None) -> str:
    """Generate a compact, report-friendly value preview."""
    safe_value = redact_value(value, key) if redact else value
    try:
        text = repr(safe_value)
    except Exception:
        text = f"<unreprable {type(value).__name__}>"
    if len(text) > max_len:
        return text[:max_len] + "...(truncated)"
    return text


def payload_summary(value: Any) -> str:
    """Summarize payload shape without exposing full body contents."""
    if value is None:
        return "<empty>"
    if isinstance(value, dict):
        return f"<dict, {len(value)} keys>"
    if isinstance(value, (list, tuple)):
        return f"<{type(value).__name__}, {len(value)} items>"
    if isinstance(value, (bytes, bytearray)):
        return f"<{len(value)} bytes>"
    if isinstance(value, str):
        return preview_value(value)
    return f"<{type(value).__name__}>"


def preview_keys(mapping: dict, max_keys: int = 20) -> str:
    """Preview dict keys without flooding logs."""
    try:
        keys_iter: Iterable = iter(mapping.keys())
    except Exception:
        return "<keys unavailable>"

    shown = []
    for _ in range(max_keys):
        try:
            key = next(keys_iter)
        except StopIteration:
            break
        except Exception:
            shown.append("<key error>")
            break
        shown.append(str(key))

    try:
        total = len(mapping)
    except Exception:
        total = None

    if total is not None and total > len(shown):
        shown.append(f"...(+{total - len(shown)})")
    return ", ".join(shown)


def attach_text(name: str, details: str) -> None:
    allure.attach(details, name=name, attachment_type=allure.attachment_type.TEXT)


def attach_verbose(name: str, details: str) -> None:
    if is_verbose():
        attach_text(name, details)


def format_mapping(mapping: Dict[str, Any]) -> str:
    return "\n".join(f"{key}: {value}" for key, value in mapping.items())


def compact_json(value: Any, max_len: int = 160) -> str:
    try:
        text = json.dumps(redact_value(value), ensure_ascii=False, default=str)
    except Exception:
        return preview_value(value, max_len=max_len)
    if len(text) > max_len:
        return text[:max_len] + "...(truncated)"
    return text


def format_keyword_arguments(arguments: Dict[str, Any], keyword_info: Dict = None,
                             excluded_keys: Iterable[str] = None,
                             max_value_len: int = 500) -> str:
    """Format keyword call arguments for concise Allure attachments."""
    excluded = set(excluded_keys or ("context", "skip_logging"))
    visible_arguments = {
        key: value for key, value in arguments.items()
        if key not in excluded
    }

    if not visible_arguments:
        return "传入参数: <无>"

    mapping = {}
    if keyword_info:
        mapping = keyword_info.get("mapping", {}) or {}

    reverse_mapping = {}
    for display_name, runtime_name in mapping.items():
        reverse_mapping.setdefault(runtime_name, display_name)

    ordered_keys = []
    parameters = (keyword_info.get("parameters") or []) if keyword_info else []
    for parameter in parameters:
        runtime_name = getattr(parameter, "mapping", None)
        if (runtime_name in visible_arguments and
                runtime_name not in ordered_keys):
            ordered_keys.append(runtime_name)

    for key in visible_arguments.keys():
        if key not in ordered_keys:
            ordered_keys.append(key)

    lines = ["传入参数:"]
    for key in ordered_keys:
        display_name = reverse_mapping.get(key)
        if display_name and display_name != key:
            label = f"{display_name}({key})"
        else:
            label = str(key)
        value_preview = preview_value(
            visible_arguments[key],
            max_len=max_value_len,
            key=key,
        )
        lines.append(f"{label}: {value_preview}")
    return "\n".join(lines)
