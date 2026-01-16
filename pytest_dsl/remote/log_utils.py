import os


def is_verbose() -> bool:
    """是否输出详细调试信息（默认关闭）。"""
    value = os.getenv("PYTEST_DSL_VERBOSE", "").strip().lower()
    return value in {"1", "true", "yes", "y", "on"}


def preview_value(value, max_len: int = 160) -> str:
    """生成适合日志输出的值预览，避免大对象刷屏。"""
    try:
        text = repr(value)
    except Exception:
        text = f"<unreprable {type(value).__name__}>"
    if len(text) > max_len:
        return text[:max_len] + "...(truncated)"
    return text


def preview_keys(mapping: dict, max_keys: int = 20) -> str:
    """生成 dict key 的预览，避免变量过多刷屏。"""
    try:
        keys_iter = iter(mapping.keys())
    except Exception:
        return "<keys unavailable>"

    shown = []
    for _ in range(max_keys):
        try:
            k = next(keys_iter)
        except StopIteration:
            break
        except Exception:
            shown.append("<key error>")
            break
        shown.append(str(k))

    try:
        total = len(mapping)
    except Exception:
        total = None

    if total is not None and total > len(shown):
        shown.append(f"...(+{total - len(shown)})")
    return ", ".join(shown)

