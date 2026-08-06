"""自定义目录收集器模块

该模块提供自定义的pytest目录收集器，用于处理.auto文件并将其转换为pytest测试用例。
"""

import hashlib
import json
import logging
import tempfile
from pathlib import Path
from typing import Iterable, Union, Optional, List

from filelock import FileLock

from pytest_dsl.core.dsl_executor_utils import execute_dsl_file
from pytest_dsl.core.hook_files import discover_hook_files

# 配置日志
logger = logging.getLogger(__name__)

# 用于跟踪已执行的setup和teardown的目录
_setup_executed = set()
_teardown_executed = set()
_hook_state_dir = Path(tempfile.mkdtemp(prefix="pytest-dsl-hooks-"))

# 常量定义
SETUP_FILE_NAME = "setup.auto"
TEARDOWN_FILE_NAME = "teardown.auto"
# 支持.dsl扩展名的setup和teardown文件
SETUP_DSL_FILE_NAME = "setup.dsl"
TEARDOWN_DSL_FILE_NAME = "teardown.dsl"
LOCK_FILE_SUFFIX = ".lock"
EXECUTED_FILE_SUFFIX = ".lock.executed"


def reset_hook_execution_state() -> None:
    """重置本进程内已执行的目录hook记录。"""
    _setup_executed.clear()
    _teardown_executed.clear()


def configure_hook_execution_state(state_dir: Union[str, Path]) -> None:
    """Use a per-test-run state directory shared by all xdist workers."""
    global _hook_state_dir

    _hook_state_dir = Path(state_dir).resolve()
    _hook_state_dir.mkdir(parents=True, exist_ok=True)
    reset_hook_execution_state()


def get_hook_execution_state_dir() -> Path:
    """Return the currently configured hook coordination directory."""
    return _hook_state_dir


def discover_hook_chain(hook_root: Union[str, Path], case_path: Union[str, Path]) -> List[Path]:
    """获取从hook根目录到用例所在目录的目录链。"""
    root = Path(hook_root).resolve()
    case_dir = Path(case_path).resolve().parent
    case_dir.relative_to(root)

    chain = [root]
    relative_parts = case_dir.relative_to(root).parts
    current = root
    for part in relative_parts:
        current = current / part
        chain.append(current)
    return chain


def find_setup_file(directory: Union[str, Path]) -> Optional[Path]:
    """查找第一个目录级setup文件（兼容旧调用方）。"""
    setup_files = find_setup_files(directory)
    return setup_files[0] if setup_files else None


def find_setup_files(directory: Union[str, Path]) -> List[Path]:
    """按执行顺序查找目录级setup文件。"""
    return discover_hook_files(directory, "setup")


def find_teardown_file(directory: Union[str, Path]) -> Optional[Path]:
    """查找第一个目录级teardown文件（兼容旧调用方）。"""
    teardown_files = find_teardown_files(directory)
    return teardown_files[0] if teardown_files else None


def find_teardown_files(directory: Union[str, Path]) -> List[Path]:
    """按执行顺序查找目录级teardown文件。"""
    return discover_hook_files(directory, "teardown")


def execute_directory_setup(directory: Union[str, Path]) -> None:
    """按顺序执行目录级setup文件（如果存在）。"""
    path = Path(directory).resolve()
    execute_hook_files(find_setup_files(path), True, str(path))


def execute_directory_teardown(directory: Union[str, Path]) -> None:
    """按反向顺序执行目录级teardown文件（如果存在）。"""
    path = Path(directory).resolve()
    execute_hook_files(find_teardown_files(path), False, str(path))


def get_lock_file_path(dir_path: str, is_setup: bool) -> str:
    """获取锁文件路径

    Args:
        dir_path: 目录路径
        is_setup: 是否为setup锁文件

    Returns:
        str: 锁文件路径
    """
    prefix = "pytest_dsl_setup_" if is_setup else "pytest_dsl_teardown_"
    key = directory_state_key(dir_path)
    return str(_hook_state_dir / f"{prefix}{key}{LOCK_FILE_SUFFIX}")


def directory_state_key(dir_path: Union[str, Path]) -> str:
    """Return a stable, process-independent key for a directory path."""
    normalized = str(Path(dir_path).resolve())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]


def get_execution_result_path(dir_path: str, is_setup: bool) -> Path:
    """Return the shared result marker for one directory hook group."""
    return Path(f"{get_lock_file_path(dir_path, is_setup)}{EXECUTED_FILE_SUFFIX}")


def hook_execution_was_attempted(dir_path: Union[str, Path], is_setup: bool) -> bool:
    """Whether a hook group has already written a cross-process result."""
    resolved = str(Path(dir_path).resolve())
    return get_execution_result_path(resolved, is_setup).exists()


def _read_hook_result(result_file: Path, hook_type: str, dir_path_str: str) -> None:
    try:
        result = json.loads(result_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Unable to read shared {hook_type.lower()} result for {dir_path_str}: {exc}"
        ) from exc

    if not result.get("success", False):
        error = result.get("error") or "unknown error"
        raise RuntimeError(f"{hook_type} for directory failed: {dir_path_str}: {error}")


def _write_hook_result(result_file: Path, success: bool, error: Optional[str] = None) -> None:
    result_file.write_text(
        json.dumps({"success": success, "error": error}, ensure_ascii=False),
        encoding="utf-8",
    )


def execute_hook_file(file_path: Path, is_setup: bool, dir_path_str: str) -> None:
    """执行单个setup或teardown钩子文件（兼容旧调用方）。"""
    execute_hook_files([file_path], is_setup, dir_path_str)


def execute_hook_files(
    file_paths: Iterable[Path],
    is_setup: bool,
    dir_path_str: str,
) -> None:
    """将一个目录的有序hook文件作为一个执行单元运行。

    Args:
        file_paths: 已按执行顺序排列的钩子文件路径
        is_setup: 是否为setup钩子
        dir_path_str: 目录路径字符串
    """
    paths = [Path(file_path) for file_path in file_paths]
    if not paths:
        return

    hook_type = "Setup" if is_setup else "Teardown"
    executed_set = _setup_executed if is_setup else _teardown_executed
    lock_file = get_lock_file_path(dir_path_str, is_setup)

    result_file = get_execution_result_path(dir_path_str, is_setup)

    # 检查是否已执行过
    if dir_path_str in executed_set:
        logger.info(f"{hook_type} for directory already executed: {dir_path_str}")
        return

    # 使用filelock获取锁并执行
    with FileLock(lock_file):
        if result_file.exists():
            _read_hook_result(result_file, hook_type, dir_path_str)
            executed_set.add(dir_path_str)
            return

        if dir_path_str in executed_set:
            return

        logger.info(
            "Running %s files for directory %s: %s",
            hook_type.lower(),
            dir_path_str,
            ", ".join(path.name for path in paths),
        )
        try:
            for file_path in paths:
                if file_path.exists():
                    execute_dsl_file(str(file_path))
        except BaseException as exc:
            _write_hook_result(result_file, False, str(exc))
            raise

        _write_hook_result(result_file, True)
        executed_set.add(dir_path_str)
