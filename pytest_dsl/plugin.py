"""pytest-dsl插件的主要入口文件

该文件负责将DSL功能集成到pytest框架中，包括命令行参数处理、YAML变量加载、
自定义目录收集器等功能。
"""
import pytest
import os
from collections import Counter
from pathlib import Path

# 导入模块化组件
from pytest_dsl.core.yaml_loader import add_yaml_options, load_yaml_variables
from pytest_dsl.core.plugin_discovery import (
    load_all_plugins, scan_local_keywords
)
from pytest_dsl.core.global_context import global_context
from pytest_dsl.core import auto_directory


class DslLifecycleState:
    """pytest会话内DSL目录hook运行状态。"""

    def __init__(self):
        self.item_chains = {}
        self.remaining_counts = Counter()
        self.setup_executed = set()
        self.teardown_executed = set()


def pytest_addoption(parser):
    """添加命令行参数选项

    Args:
        parser: pytest命令行参数解析器
    """
    # 使用yaml_loader模块添加YAML相关选项
    add_yaml_options(parser)


@pytest.hookimpl
def pytest_collect_file(file_path, parent):
    """Collect pytest-dsl case files without generating Python wrappers."""
    from pytest_dsl.core.dsl_collector import DslFile, is_dsl_case_file

    path = Path(file_path)
    if is_dsl_case_file(path):
        return DslFile.from_parent(parent, path=path)
    return None


@pytest.hookimpl
def pytest_configure(config):
    """配置测试会话，加载已执行的setup/teardown信息和YAML变量

    Args:
        config: pytest配置对象
    """

    # 加载YAML变量文件
    load_yaml_variables(config)
    config.addinivalue_line(
        "markers",
        "pytest_dsl_case(case_path, suite_id, hook_root): generated DSL case metadata",
    )
    config._pytest_dsl_lifecycle_state = DslLifecycleState()
    auto_directory.reset_hook_execution_state()

    # 确保全局变量存储目录存在
    os.makedirs(global_context._storage_dir, exist_ok=True)

    # 首先导入内置关键字模块，确保内置关键字被注册
    try:
        import pytest_dsl.keywords  # noqa: F401
        print("pytest环境：内置关键字模块加载完成")
    except ImportError as e:
        print(f"pytest环境：加载内置关键字模块失败: {e}")

    # 加载所有已安装的关键字插件
    load_all_plugins()

    # 加载本地关键字（向后兼容）
    scan_local_keywords()

    # 在插件加载完成后，重新初始化hook系统以确保新插件的hook能被注册
    try:
        from pytest_dsl.core.hook_manager import hook_manager
        from pytest_dsl.core.hookable_keyword_manager import hookable_keyword_manager

        # 重新初始化hook管理器和hookable关键字管理器
        hook_manager.reinitialize_after_plugin_load()
        hookable_keyword_manager.reinitialize_after_plugin_load()

    except Exception as e:
        print(f"pytest环境：重新初始化Hook系统时出现警告: {str(e)}")

    # 自动导入项目中的resources目录
    try:
        from pytest_dsl.core.custom_keyword_manager import (
            custom_keyword_manager
        )

        # 获取pytest的根目录
        project_root = str(config.rootdir) if config.rootdir else os.getcwd()

        # 检查是否存在resources目录
        resources_dir = os.path.join(project_root, "resources")
        if os.path.exists(resources_dir) and os.path.isdir(resources_dir):
            custom_keyword_manager.auto_import_resources_directory(
                project_root)
            print(f"pytest环境：已自动导入resources目录 {resources_dir}")

    except Exception as e:
        print(f"pytest环境：自动导入resources目录时出现警告: {str(e)}")


@pytest.hookimpl
def pytest_collection_modifyitems(config, items):
    """收集生成DSL pytest item的目录hook链。"""
    state = _get_lifecycle_state(config)
    state.item_chains.clear()
    state.remaining_counts.clear()
    state.setup_executed.clear()
    state.teardown_executed.clear()

    for item in items:
        metadata = _get_dsl_case_metadata(item)
        if not metadata:
            continue
        case_path = metadata.get("case_path")
        hook_root = metadata.get("hook_root")
        if not case_path or not hook_root:
            continue

        chain = auto_directory.discover_hook_chain(hook_root, case_path)
        state.item_chains[item.nodeid] = chain
        for directory in chain:
            state.remaining_counts[directory] += 1


@pytest.hookimpl
def pytest_runtest_setup(item):
    """在DSL用例运行前执行缺失的目录setup。"""
    state = _get_lifecycle_state(item.config)
    chain = state.item_chains.get(item.nodeid)
    if not chain:
        return

    for directory in chain:
        if directory in state.setup_executed:
            continue
        auto_directory.execute_directory_setup(directory)
        state.setup_executed.add(directory)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item):
    """在DSL用例运行后关闭已完成的目录scope。"""
    outcome = yield
    state = _get_lifecycle_state(item.config)
    chain = state.item_chains.get(item.nodeid)
    if not chain:
        return

    _close_finished_directories(state, reversed(chain))
    outcome.get_result()


@pytest.hookimpl
def pytest_sessionfinish(session, exitstatus):
    """会话结束时关闭仍未关闭的DSL目录hook。"""
    state = _get_lifecycle_state(session.config)
    open_directories = [
        directory
        for directory in state.remaining_counts
        if directory not in state.teardown_executed
    ]
    for directory in sorted(open_directories, key=lambda path: len(path.parts), reverse=True):
        _execute_teardown_once(state, directory)


def _close_finished_directories(state: DslLifecycleState, directories) -> None:
    for directory in directories:
        if state.remaining_counts[directory] > 0:
            state.remaining_counts[directory] -= 1
        if state.remaining_counts[directory] == 0:
            _execute_teardown_once(state, directory)


def _execute_teardown_once(state: DslLifecycleState, directory: Path) -> None:
    if directory in state.teardown_executed:
        return
    auto_directory.execute_directory_teardown(directory)
    state.teardown_executed.add(directory)


def _get_lifecycle_state(config) -> DslLifecycleState:
    state = getattr(config, "_pytest_dsl_lifecycle_state", None)
    if state is None:
        state = DslLifecycleState()
        config._pytest_dsl_lifecycle_state = state
    return state


def _get_dsl_case_metadata(item):
    metadata = getattr(item, "_pytest_dsl_case", None)
    if metadata:
        return metadata

    marker = item.get_closest_marker("pytest_dsl_case")
    if marker:
        return marker.kwargs

    return None
