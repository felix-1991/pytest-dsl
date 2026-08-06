"""pytest-dsl插件的主要入口文件

该文件负责将DSL功能集成到pytest框架中，包括命令行参数处理、YAML变量加载、
自定义目录收集器等功能。
"""
import json
import pytest
import os
import shutil
import tempfile
from collections import Counter
from pathlib import Path

from filelock import FileLock

# 导入模块化组件
from pytest_dsl.core.yaml_loader import add_yaml_options, load_yaml_variables
from pytest_dsl.core.plugin_discovery import (
    load_all_plugins, scan_local_keywords
)
from pytest_dsl.core.global_context import global_context
from pytest_dsl.core import auto_directory
from pytest_dsl.core.reporting import print_verbose


class DslLifecycleState:
    """pytest会话内DSL目录hook运行状态。"""

    def __init__(self):
        self.item_chains = {}
        self.remaining_counts = Counter()
        self.setup_started = set()
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
    if is_dsl_case_file(path) and _should_collect_dsl_file(path, parent.config):
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
    state_dir = _configure_shared_lifecycle_dir(config)
    auto_directory.configure_hook_execution_state(state_dir)

    # 确保全局变量存储目录存在
    os.makedirs(global_context._storage_dir, exist_ok=True)

    # 首先导入内置关键字模块，确保内置关键字被注册
    try:
        import pytest_dsl.keywords  # noqa: F401
        print_verbose("pytest环境：内置关键字模块加载完成")
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
            print_verbose(f"pytest环境：已自动导入resources目录 {resources_dir}")

    except Exception as e:
        print(f"pytest环境：自动导入resources目录时出现警告: {str(e)}")


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    """收集生成DSL pytest item的目录hook链。"""
    state = _get_lifecycle_state(config)
    state.item_chains.clear()
    state.remaining_counts.clear()
    state.setup_started.clear()
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

    if _is_xdist_worker(config):
        _initialize_distributed_counts(config, state)


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
        state.setup_started.add(directory)
        if _is_xdist_worker(item.config):
            _mark_directory_started(item.config, directory)
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

    if _is_xdist_worker(item.config):
        _close_distributed_directories(item.config, state, reversed(chain))
    else:
        _close_finished_directories(state, reversed(chain))
    outcome.get_result()


@pytest.hookimpl
def pytest_sessionfinish(session, exitstatus):
    """会话结束时关闭仍未关闭的DSL目录hook。"""
    if _is_xdist_worker(session.config):
        return

    if _is_xdist_controller(session.config):
        _finish_distributed_lifecycle(session.config)
        return

    state = _get_lifecycle_state(session.config)
    open_directories = [
        directory
        for directory in state.remaining_counts
        if directory in state.setup_started and directory not in state.teardown_executed
    ]
    for directory in sorted(open_directories, key=lambda path: len(path.parts), reverse=True):
        _execute_teardown_once(state, directory)


@pytest.hookimpl(optionalhook=True)
def pytest_configure_node(node):
    """Pass the controller's lifecycle directory to every xdist worker."""
    state_dir = getattr(node.config, "_pytest_dsl_lifecycle_dir", None)
    if state_dir is not None:
        node.workerinput["pytest_dsl_lifecycle_dir"] = str(state_dir)


def pytest_unconfigure(config):
    """Remove the per-run coordination directory after all session hooks finish."""
    if not getattr(config, "_pytest_dsl_owns_lifecycle_dir", False):
        return
    state_dir = getattr(config, "_pytest_dsl_lifecycle_dir", None)
    if state_dir is not None:
        previous_dir = getattr(config, "_pytest_dsl_previous_lifecycle_dir", None)
        if previous_dir is not None:
            auto_directory.configure_hook_execution_state(previous_dir)
        shutil.rmtree(state_dir, ignore_errors=True)


def _close_finished_directories(state: DslLifecycleState, directories) -> None:
    for directory in directories:
        if state.remaining_counts[directory] > 0:
            state.remaining_counts[directory] -= 1
        if state.remaining_counts[directory] == 0:
            _execute_teardown_once(state, directory)


def _configure_shared_lifecycle_dir(config) -> Path:
    config._pytest_dsl_previous_lifecycle_dir = auto_directory.get_hook_execution_state_dir()
    worker_input = getattr(config, "workerinput", None)
    shared_dir = worker_input.get("pytest_dsl_lifecycle_dir") if worker_input else None
    if shared_dir:
        state_dir = Path(shared_dir).resolve()
        owns_dir = False
    else:
        state_dir = Path(tempfile.mkdtemp(prefix="pytest-dsl-lifecycle-")).resolve()
        owns_dir = True
    state_dir.mkdir(parents=True, exist_ok=True)
    config._pytest_dsl_lifecycle_dir = state_dir
    config._pytest_dsl_owns_lifecycle_dir = owns_dir
    return state_dir


def _is_xdist_worker(config) -> bool:
    return getattr(config, "workerinput", None) is not None


def _is_xdist_controller(config) -> bool:
    if _is_xdist_worker(config):
        return False
    numprocesses = getattr(getattr(config, "option", None), "numprocesses", None)
    return numprocesses not in (None, 0)


def _shared_path(config, name: str) -> Path:
    return Path(config._pytest_dsl_lifecycle_dir) / name


def _counter_path(config, directory: Path) -> Path:
    key = auto_directory.directory_state_key(directory)
    return _shared_path(config, f"counter_{key}.txt")


def _initialize_distributed_counts(config, state: DslLifecycleState) -> None:
    ready_file = _shared_path(config, "collection.ready")
    lock_file = _shared_path(config, "collection.lock")
    with FileLock(str(lock_file)):
        if ready_file.exists():
            return

        directories = sorted(state.remaining_counts, key=lambda path: (len(path.parts), str(path)))
        manifest = []
        for directory in directories:
            count = state.remaining_counts[directory]
            _counter_path(config, directory).write_text(str(count), encoding="utf-8")
            manifest.append({"path": str(directory), "count": count})

        _shared_path(config, "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False),
            encoding="utf-8",
        )
        ready_file.touch()


def _mark_directory_started(config, directory: Path) -> None:
    key = auto_directory.directory_state_key(directory)
    _shared_path(config, f"started_{key}").touch(exist_ok=True)


def _directory_was_started(config, directory: Path) -> bool:
    key = auto_directory.directory_state_key(directory)
    return _shared_path(config, f"started_{key}").exists()


def _decrement_distributed_count(config, directory: Path) -> bool:
    counter_file = _counter_path(config, directory)
    lock_file = Path(f"{counter_file}.lock")
    with FileLock(str(lock_file)):
        if not counter_file.exists():
            return False
        try:
            remaining = int(counter_file.read_text(encoding="utf-8").strip())
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"Invalid pytest-dsl lifecycle counter {counter_file}: {exc}") from exc
        if remaining <= 0:
            return False
        remaining -= 1
        counter_file.write_text(str(remaining), encoding="utf-8")
        return remaining == 0


def _close_distributed_directories(config, state: DslLifecycleState, directories) -> None:
    for directory in directories:
        if _decrement_distributed_count(config, directory):
            _execute_teardown_once(state, directory)


def _finish_distributed_lifecycle(config) -> None:
    manifest_file = _shared_path(config, "manifest.json")
    if not manifest_file.exists():
        return
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Unable to read pytest-dsl lifecycle manifest: {exc}") from exc

    directories = [Path(entry["path"]).resolve() for entry in manifest]
    for directory in sorted(directories, key=lambda path: len(path.parts), reverse=True):
        if not _directory_was_started(config, directory):
            continue
        if auto_directory.hook_execution_was_attempted(directory, is_setup=False):
            continue
        auto_directory.execute_directory_teardown(directory)


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


def _should_collect_dsl_file(path: Path, config) -> bool:
    """Return True when a DSL file should become a pytest item."""
    resolved = path.resolve()
    if _is_under_tests_directory(resolved, config):
        return True
    return _is_explicit_dsl_file_argument(resolved, config)


def _is_under_tests_directory(path: Path, config) -> bool:
    root = Path(getattr(config, "rootpath", config.rootdir)).resolve()
    try:
        relative_parts = path.relative_to(root).parts
    except ValueError:
        relative_parts = path.parts
    return "tests" in relative_parts[:-1]


def _is_explicit_dsl_file_argument(path: Path, config) -> bool:
    invocation_dir = Path(getattr(config.invocation_params, "dir", Path.cwd())).resolve()
    for arg in config.args:
        arg_path_text = str(arg).split("::", 1)[0]
        if not arg_path_text:
            continue
        arg_path = Path(arg_path_text)
        if not arg_path.is_absolute():
            arg_path = invocation_dir / arg_path
        try:
            if arg_path.resolve() == path:
                return True
        except OSError:
            continue
    return False
