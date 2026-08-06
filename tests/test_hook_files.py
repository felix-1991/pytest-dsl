from pathlib import Path

import pytest

from pytest_dsl.core import auto_directory
from pytest_dsl.core.hook_files import (
    discover_hook_files,
    is_hook_file,
    parse_hook_file,
)


REAL_EXECUTE_HOOK_FILES = auto_directory.execute_hook_files


def touch(root: Path, name: str) -> Path:
    path = root / name
    path.touch()
    return path


def test_recognizes_legacy_numbered_and_named_hook_names():
    assert is_hook_file("setup.dsl")
    assert is_hook_file("setup_01.dsl")
    assert is_hook_file("setup_20_database.auto")
    assert is_hook_file("setup_fast.dsl")
    assert is_hook_file("setup_前置打开debug开关.dsl")
    assert is_hook_file("teardown_关闭debug开关.auto")
    assert is_hook_file("teardown_20_清理数据库.dsl")

    assert not is_hook_file("setup_.dsl")
    assert not is_hook_file("setup_01_.dsl")
    assert not is_hook_file("my_setup_01.dsl")

    hook = parse_hook_file("setup_020_database.dsl")
    assert hook is not None
    assert hook.kind == "setup"
    assert hook.order == 20
    assert hook.label == "database"

    named_hook = parse_hook_file("setup_前置打开debug开关.dsl")
    assert named_hook is not None
    assert named_hook.kind == "setup"
    assert named_hook.order is None
    assert named_hook.label == "前置打开debug开关"
    assert not named_hook.legacy


def test_discovers_setup_in_numeric_order_and_teardown_in_reverse(tmp_path):
    for name in [
        "setup_100_last.dsl",
        "setup_2_second.dsl",
        "setup_前置打开debug开关.dsl",
        "setup.dsl",
        "setup_02_after_second.dsl",
        "teardown.dsl",
        "teardown_2_second.dsl",
        "teardown_100_last.dsl",
        "teardown_关闭debug开关.dsl",
        "case.dsl",
    ]:
        touch(tmp_path, name)

    assert [path.name for path in discover_hook_files(tmp_path, "setup")] == [
        "setup.dsl",
        "setup_前置打开debug开关.dsl",
        "setup_02_after_second.dsl",
        "setup_2_second.dsl",
        "setup_100_last.dsl",
    ]
    assert [path.name for path in discover_hook_files(tmp_path, "teardown")] == [
        "teardown_100_last.dsl",
        "teardown_2_second.dsl",
        "teardown_关闭debug开关.dsl",
        "teardown.dsl",
    ]


def test_dsl_extension_wins_when_same_hook_stem_has_auto_variant(tmp_path):
    touch(tmp_path, "setup.dsl")
    touch(tmp_path, "setup.auto")
    touch(tmp_path, "setup_10_database.dsl")
    touch(tmp_path, "setup_10_database.auto")

    assert [path.name for path in discover_hook_files(tmp_path, "setup")] == [
        "setup.dsl",
        "setup_10_database.dsl",
    ]


def test_directory_hook_group_executes_once_in_discovered_order(tmp_path, monkeypatch):
    for name in [
        "setup_10_database.dsl",
        "setup.dsl",
        "setup_前置打开debug开关.dsl",
        "setup_2_environment.dsl",
    ]:
        touch(tmp_path, name)

    executed = []
    monkeypatch.setattr(auto_directory, "execute_dsl_file", executed.append)
    monkeypatch.setattr(auto_directory, "execute_hook_files", REAL_EXECUTE_HOOK_FILES)
    auto_directory.reset_hook_execution_state()

    auto_directory.execute_directory_setup(tmp_path)
    auto_directory.execute_directory_setup(tmp_path)

    assert [Path(path).name for path in executed] == [
        "setup.dsl",
        "setup_前置打开debug开关.dsl",
        "setup_2_environment.dsl",
        "setup_10_database.dsl",
    ]


def test_hook_result_marker_is_shared_after_in_memory_state_is_reset(tmp_path, monkeypatch):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    monkeypatch.setattr(auto_directory, "_hook_state_dir", state_dir)
    setup_file = touch(tmp_path, "setup.dsl")
    executed = []
    monkeypatch.setattr(auto_directory, "execute_dsl_file", executed.append)
    monkeypatch.setattr(auto_directory, "execute_hook_files", REAL_EXECUTE_HOOK_FILES)

    auto_directory.reset_hook_execution_state()
    auto_directory.execute_directory_setup(tmp_path)
    auto_directory.reset_hook_execution_state()
    auto_directory.execute_directory_setup(tmp_path)

    assert executed == [str(setup_file)]


def test_hook_lock_path_is_stable_and_does_not_use_process_hash(tmp_path, monkeypatch):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    monkeypatch.setattr(auto_directory, "_hook_state_dir", state_dir)

    first = auto_directory.get_lock_file_path(str(tmp_path), True)
    second = auto_directory.get_lock_file_path(str(tmp_path), True)

    assert first == second
    assert auto_directory.directory_state_key(tmp_path) in first


def test_setup_failure_is_propagated_to_other_process_state(tmp_path, monkeypatch):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    monkeypatch.setattr(auto_directory, "_hook_state_dir", state_dir)
    touch(tmp_path, "setup.dsl")
    attempts = []

    def fail_setup(file_path):
        attempts.append(file_path)
        raise ValueError("database unavailable")

    monkeypatch.setattr(auto_directory, "execute_dsl_file", fail_setup)
    monkeypatch.setattr(auto_directory, "execute_hook_files", REAL_EXECUTE_HOOK_FILES)
    auto_directory.reset_hook_execution_state()

    with pytest.raises(ValueError, match="database unavailable"):
        auto_directory.execute_directory_setup(tmp_path)

    auto_directory.reset_hook_execution_state()
    with pytest.raises(RuntimeError, match="database unavailable"):
        auto_directory.execute_directory_setup(tmp_path)

    assert len(attempts) == 1
