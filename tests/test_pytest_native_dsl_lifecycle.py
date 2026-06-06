from pathlib import Path


pytest_plugins = ["pytester"]


def write_file(root: Path, relative_path: str, content: str = "") -> Path:
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def install_fake_runtime_logger(pytester, log_path: Path, exit_case: str | None = None) -> None:
    pytester.makeconftest(
        f"""
from pathlib import Path

import pytest

from pytest_dsl.core import auto_directory
from pytest_dsl.core import dsl_collector

LOG_PATH = Path({str(log_path)!r})
EXIT_CASE = {exit_case!r}


def record(line):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write(f"{{line}}\\n")


def pytest_configure(config):
    def fake_execute_hook_file(file_path, is_setup, dir_path_str):
        hook_type = "setup" if is_setup else "teardown"
        directory = Path(dir_path_str).name or "tests"
        record(f"{{hook_type}}:{{directory}}")

    def fake_execute_dsl_file(file_path, executor=None):
        case_name = Path(file_path).stem
        record(f"case:{{case_name}}")
        if EXIT_CASE == case_name:
            pytest.exit("stop early")

    auto_directory.execute_hook_file = fake_execute_hook_file
    dsl_collector.execute_dsl_file = fake_execute_dsl_file
"""
    )


def test_native_dsl_hooks_follow_nested_directory_scope_once(pytester):
    log_path = pytester.path / "order.log"
    install_fake_runtime_logger(pytester, log_path)

    write_file(pytester.path, "tests/setup.dsl")
    write_file(pytester.path, "tests/teardown.dsl")
    write_file(pytester.path, "tests/api/setup.dsl")
    write_file(pytester.path, "tests/api/teardown.dsl")
    write_file(pytester.path, "tests/api/auth/setup.dsl")
    write_file(pytester.path, "tests/api/auth/teardown.dsl")
    write_file(pytester.path, "tests/api/auth/login.dsl", '[打印], 内容: "login"\n')
    write_file(pytester.path, "tests/api/auth/logout.dsl", '[打印], 内容: "logout"\n')

    result = pytester.runpytest("tests/api/auth", "-q")

    result.assert_outcomes(passed=2)
    assert log_path.read_text(encoding="utf-8").splitlines() == [
        "setup:tests",
        "setup:api",
        "setup:auth",
        "case:login",
        "case:logout",
        "teardown:auth",
        "teardown:api",
        "teardown:tests",
    ]


def test_plain_pytest_items_do_not_trigger_dsl_hooks(pytester):
    log_path = pytester.path / "order.log"
    install_fake_runtime_logger(pytester, log_path)

    write_file(pytester.path, "tests/setup.dsl")
    write_file(pytester.path, "tests/teardown.dsl")
    write_file(
        pytester.path,
        "tests/test_plain.py",
        f"""
from pathlib import Path

LOG_PATH = Path({str(log_path)!r})


def test_plain_pytest_item():
    with LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write("plain:pytest\\n")
""",
    )

    result = pytester.runpytest("tests", "-q")

    result.assert_outcomes(passed=1)
    assert log_path.read_text(encoding="utf-8").splitlines() == ["plain:pytest"]


def test_sessionfinish_closes_native_dsl_hook_scopes_after_early_exit(pytester):
    log_path = pytester.path / "order.log"
    install_fake_runtime_logger(pytester, log_path, exit_case="login")

    write_file(pytester.path, "tests/setup.dsl")
    write_file(pytester.path, "tests/teardown.dsl")
    write_file(pytester.path, "tests/api/setup.dsl")
    write_file(pytester.path, "tests/api/teardown.dsl")
    write_file(pytester.path, "tests/api/auth/setup.dsl")
    write_file(pytester.path, "tests/api/auth/teardown.dsl")
    write_file(pytester.path, "tests/api/auth/login.dsl", '[打印], 内容: "login"\n')

    result = pytester.runpytest("tests/api/auth", "-q")

    result.stdout.fnmatch_lines(["*stop early*"])
    assert log_path.read_text(encoding="utf-8").splitlines() == [
        "setup:tests",
        "setup:api",
        "setup:auth",
        "case:login",
        "teardown:auth",
        "teardown:api",
        "teardown:tests",
    ]
