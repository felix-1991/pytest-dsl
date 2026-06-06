"""自定义目录收集器模块

该模块提供自定义的pytest目录收集器，用于处理.auto文件并将其转换为pytest测试用例。
"""

import sys
import os
import types
import logging
from pathlib import Path
from _pytest import nodes
from typing import Iterable, Union, Optional, List, Dict, Any
import pytest
from filelock import FileLock

from pytest_dsl.core.dsl_executor import DSLExecutor
from pytest_dsl.core.dsl_executor_utils import read_file, execute_dsl_file, extract_metadata_from_ast
from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import get_parser

# 配置日志
logger = logging.getLogger(__name__)

# 获取词法分析器和解析器实例
lexer = get_lexer()
parser = get_parser()

# 用于跟踪已执行的setup和teardown的目录
_setup_executed = set()
_teardown_executed = set()

# 常量定义
SETUP_FILE_NAME = "setup.auto"
TEARDOWN_FILE_NAME = "teardown.auto"
# 支持.dsl扩展名的setup和teardown文件
SETUP_DSL_FILE_NAME = "setup.dsl"
TEARDOWN_DSL_FILE_NAME = "teardown.dsl"
TMP_DIR = "/tmp"
LOCK_FILE_SUFFIX = ".lock"
EXECUTED_FILE_SUFFIX = ".lock.executed"


def reset_hook_execution_state() -> None:
    """重置本进程内已执行的目录hook记录。"""
    _setup_executed.clear()
    _teardown_executed.clear()


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
    """查找目录级setup文件。"""
    path = Path(directory)
    for name in [SETUP_DSL_FILE_NAME, SETUP_FILE_NAME]:
        candidate = path / name
        if candidate.exists():
            return candidate
    return None


def find_teardown_file(directory: Union[str, Path]) -> Optional[Path]:
    """查找目录级teardown文件。"""
    path = Path(directory)
    for name in [TEARDOWN_DSL_FILE_NAME, TEARDOWN_FILE_NAME]:
        candidate = path / name
        if candidate.exists():
            return candidate
    return None


def execute_directory_setup(directory: Union[str, Path]) -> None:
    """执行目录级setup文件（如果存在）。"""
    path = Path(directory).resolve()
    setup_file = find_setup_file(path)
    if setup_file:
        execute_hook_file(setup_file, True, str(path))


def execute_directory_teardown(directory: Union[str, Path]) -> None:
    """执行目录级teardown文件（如果存在）。"""
    path = Path(directory).resolve()
    teardown_file = find_teardown_file(path)
    if teardown_file:
        execute_hook_file(teardown_file, False, str(path))


def get_lock_file_path(dir_path: str, is_setup: bool) -> str:
    """获取锁文件路径

    Args:
        dir_path: 目录路径
        is_setup: 是否为setup锁文件

    Returns:
        str: 锁文件路径
    """
    prefix = "pytest_dsl_setup_" if is_setup else "pytest_dsl_teardown_"
    return f"{TMP_DIR}/{prefix}{hash(dir_path)}{LOCK_FILE_SUFFIX}"


def execute_hook_file(file_path: Path, is_setup: bool, dir_path_str: str) -> None:
    """执行setup或teardown钩子文件

    Args:
        file_path: 钩子文件路径
        is_setup: 是否为setup钩子
        dir_path_str: 目录路径字符串
    """
    hook_type = "Setup" if is_setup else "Teardown"
    executed_set = _setup_executed if is_setup else _teardown_executed
    lock_file = get_lock_file_path(dir_path_str, is_setup)

    # 检查是否已执行过
    if dir_path_str in executed_set:
        logger.info(f"{hook_type} for directory already executed: {dir_path_str}")
        return

    # 使用filelock获取锁并执行
    with FileLock(lock_file):
        if dir_path_str not in executed_set:  # 再次检查，防止在获取锁期间被其他进程执行
            logger.info(f"Running {hook_type.lower()} for directory: {dir_path_str}")
            if file_path.exists():
                execute_dsl_file(str(file_path))
            # 标记为已执行
            executed_set.add(dir_path_str)
            # 创建标记文件，用于跨进程共享执行状态
            with open(f"{lock_file}{EXECUTED_FILE_SUFFIX}", "w") as f:
                f.write("1")
