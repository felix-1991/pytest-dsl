from pathlib import Path


pytest_plugins = ["pytester"]


def write_file(root: Path, relative_path: str, content: str = "") -> Path:
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def install_fake_hook_logger(pytester, log_path: Path) -> None:
    pytester.makeconftest(
        f"""
from pathlib import Path

from pytest_dsl.core import auto_directory

LOG_PATH = Path({str(log_path)!r})


def pytest_configure(config):
    def fake_execute_hook_file(file_path, is_setup, dir_path_str):
        hook_type = "setup" if is_setup else "teardown"
        directory = Path(dir_path_str).name or "tests"
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as stream:
            stream.write(f"{{hook_type}}:{{directory}}\\n")

    auto_directory.execute_hook_file = fake_execute_hook_file
"""
    )


def test_nested_dsl_hooks_follow_directory_scope_and_ignore_plain_pytest(pytester):
    log_path = pytester.path / "order.log"
    install_fake_hook_logger(pytester, log_path)

    write_file(pytester.path, "tests/setup.dsl")
    write_file(pytester.path, "tests/teardown.dsl")
    write_file(pytester.path, "tests/api/setup.dsl")
    write_file(pytester.path, "tests/api/teardown.dsl")
    write_file(pytester.path, "tests/api/auth/setup.dsl")
    write_file(pytester.path, "tests/api/auth/teardown.dsl")
    write_file(pytester.path, "tests/api/auth/login.dsl")
    write_file(pytester.path, "tests/api/auth/logout.dsl")
    write_file(
        pytester.path,
        "tests/api/auth/.pytest-dsl-generated/test_dsl_cases.py",
        f"""
from pathlib import Path

import pytest

LOG_PATH = Path({str(log_path)!r})
_CASE_DIR = Path(__file__).resolve().parents[1]
_TESTS_ROOT = Path(__file__).resolve().parents[3]


def record(name):
    with LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write(f"case:{{name}}\\n")


@pytest.mark.pytest_dsl_case(
    case_path=str(_CASE_DIR / "login.dsl"),
    suite_id="api",
    hook_root=str(_TESTS_ROOT),
)
def test_login():
    record("login")


@pytest.mark.pytest_dsl_case(
    case_path=str(_CASE_DIR / "logout.dsl"),
    suite_id="api",
    hook_root=str(_TESTS_ROOT),
)
def test_logout():
    record("logout")
""",
    )
    write_file(
        pytester.path,
        "tests/api/test_plain.py",
        f"""
from pathlib import Path

LOG_PATH = Path({str(log_path)!r})


def test_plain_pytest_item():
    with LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write("plain:pytest\\n")
""",
    )

    result = pytester.runpytest(
        "tests/api/auth/.pytest-dsl-generated/test_dsl_cases.py",
        "tests/api/test_plain.py",
        "-q",
    )

    result.assert_outcomes(passed=3)
    assert log_path.read_text(encoding="utf-8").splitlines() == [
        "setup:tests",
        "setup:api",
        "setup:auth",
        "case:login",
        "case:logout",
        "teardown:auth",
        "teardown:api",
        "teardown:tests",
        "plain:pytest",
    ]


def test_sessionfinish_closes_remaining_dsl_hook_scopes(pytester):
    log_path = pytester.path / "order.log"
    install_fake_hook_logger(pytester, log_path)

    write_file(pytester.path, "tests/setup.dsl")
    write_file(pytester.path, "tests/teardown.dsl")
    write_file(pytester.path, "tests/api/setup.dsl")
    write_file(pytester.path, "tests/api/teardown.dsl")
    write_file(pytester.path, "tests/api/auth/setup.dsl")
    write_file(pytester.path, "tests/api/auth/teardown.dsl")
    write_file(pytester.path, "tests/api/auth/login.dsl")
    write_file(
        pytester.path,
        "tests/api/auth/.pytest-dsl-generated/test_dsl_cases.py",
        f"""
from pathlib import Path

import pytest

LOG_PATH = Path({str(log_path)!r})
_CASE_DIR = Path(__file__).resolve().parents[1]
_TESTS_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.pytest_dsl_case(
    case_path=str(_CASE_DIR / "login.dsl"),
    suite_id="api",
    hook_root=str(_TESTS_ROOT),
)
def test_login():
    with LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write("case:login\\n")
    pytest.exit("stop early")
""",
    )

    result = pytester.runpytest(
        "tests/api/auth/.pytest-dsl-generated/test_dsl_cases.py",
        "-q",
    )

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
