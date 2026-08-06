from pathlib import Path


pytest_plugins = ["pytester"]


def write_file(root: Path, relative_path: str, content: str = "") -> Path:
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def run_pytest_dsl(pytester, *args):
    return pytester.runpytest(*args)


def test_single_dsl_file_runs_as_pytest_item(pytester):
    write_file(pytester.path, "tests/case.dsl", '[打印], 内容: "native"\n')

    result = run_pytest_dsl(pytester, "tests/case.dsl", "-q")

    result.assert_outcomes(passed=1)


def test_collect_only_uses_stable_dsl_nodeid(pytester):
    write_file(pytester.path, "tests/case.dsl", '[打印], 内容: "native"\n')

    result = run_pytest_dsl(pytester, "tests/case.dsl", "--collect-only", "-q")

    result.stdout.fnmatch_lines(["tests/case.dsl::case"])
    assert "tests/case.dsl::setup" not in result.stdout.str()


def test_hook_files_are_not_collected_as_cases(pytester):
    write_file(pytester.path, "tests/setup.dsl", '[打印], 内容: "setup"\n')
    write_file(pytester.path, "tests/setup_01_environment.dsl", '[打印], 内容: "setup"\n')
    write_file(pytester.path, "tests/setup_前置打开debug开关.dsl", '[打印], 内容: "setup"\n')
    write_file(pytester.path, "tests/teardown.dsl", '[打印], 内容: "teardown"\n')
    write_file(pytester.path, "tests/teardown_01_environment.auto", '[打印], 内容: "teardown"\n')
    write_file(pytester.path, "tests/teardown_关闭debug开关.dsl", '[打印], 内容: "teardown"\n')
    write_file(pytester.path, "tests/case.auto", '[打印], 内容: "case"\n')

    result = run_pytest_dsl(pytester, "tests", "--collect-only", "-q")

    output = result.stdout.str()
    assert "tests/case.auto::case" in output
    assert "tests/setup.dsl::setup" not in output
    assert "setup_01_environment" not in output
    assert "setup_前置打开debug开关" not in output
    assert "tests/teardown.dsl::teardown" not in output
    assert "teardown_01_environment" not in output
    assert "teardown_关闭debug开关" not in output


def test_directory_collects_dsl_and_plain_pytest_items(pytester):
    write_file(pytester.path, "tests/mixed/case.dsl", '[打印], 内容: "dsl"\n')
    write_file(
        pytester.path,
        "tests/mixed/test_plain.py",
        "def test_plain_pytest_item():\n    assert True\n",
    )

    result = run_pytest_dsl(pytester, "tests/mixed", "-q")

    result.assert_outcomes(passed=2)


def test_data_driven_dsl_collects_one_item_per_data_row(pytester):
    write_file(
        pytester.path,
        "tests/api/login.dsl",
        "\n".join(
            [
                '@name: "Login"',
                '@data: "login_data.csv" using csv',
                "",
                '[打印], 内容: "用户: ${username}"',
                '[断言], 条件: "${expected} == ok", 消息: "数据行未注入"',
                "",
            ]
        ),
    )
    write_file(pytester.path, "tests/api/login_data.csv", "username,expected\nalice,ok\nbob,ok\n")

    collect = run_pytest_dsl(pytester, "tests/api/login.dsl", "--collect-only", "-q")
    collect.stdout.fnmatch_lines(
        [
            "tests/api/login.dsl::login[data-0]",
            "tests/api/login.dsl::login[data-1]",
        ]
    )

    result = run_pytest_dsl(pytester, "tests/api/login.dsl", "-q")
    result.assert_outcomes(passed=2)


def test_native_dsl_item_exposes_function_for_pytest_plugin_compatibility(pytester):
    pytester.makeconftest(
        """
import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    outcome.get_result()
    getattr(item.function, "case_id", None)
"""
    )
    write_file(pytester.path, "tests/case.dsl", '[打印], 内容: "native"\n')

    result = run_pytest_dsl(pytester, "tests/case.dsl", "-q")

    result.assert_outcomes(passed=1)
    assert "INTERNALERROR" not in result.stdout.str()


def test_directory_scan_ignores_dsl_files_outside_tests_directory(pytester):
    write_file(pytester.path, "framework/dsl/templates/example.dsl", '[打印], 内容: "template"\n')
    write_file(
        pytester.path,
        "framework/test_plain.py",
        "def test_plain_pytest_item():\n    assert True\n",
    )

    result = run_pytest_dsl(pytester, "framework", "--collect-only", "-q")

    output = result.stdout.str()
    assert "framework/test_plain.py::test_plain_pytest_item" in output
    assert "framework/dsl/templates/example.dsl::example" not in output


def test_explicit_dsl_file_outside_tests_directory_still_runs(pytester):
    write_file(pytester.path, "examples/example.dsl", '[打印], 内容: "explicit"\n')

    result = run_pytest_dsl(pytester, "examples/example.dsl", "-q")

    result.assert_outcomes(passed=1)


def test_dsl_tags_are_native_pytest_markers(pytester):
    write_file(
        pytester.path,
        "tests/smoke.dsl",
        '@tags: [BVT, "串行"]\n\n[打印], 内容: "smoke"\n',
    )
    write_file(
        pytester.path,
        "tests/regression.dsl",
        '@tags: [regression]\n\n[打印], 内容: "regression"\n',
    )

    result = run_pytest_dsl(pytester, "tests", "-m", "BVT", "--strict-markers", "-q")

    result.assert_outcomes(passed=1, deselected=1)
    assert "PytestUnknownMarkWarning" not in result.stdout.str()


def test_unicode_dsl_tag_can_be_selected_with_marker_expression(pytester):
    write_file(
        pytester.path,
        "tests/serial.dsl",
        '@tags: ["串行"]\n\n[打印], 内容: "serial"\n',
    )
    write_file(pytester.path, "tests/parallel.dsl", '[打印], 内容: "parallel"\n')

    result = run_pytest_dsl(pytester, "tests", "-m", "串行", "-q")

    result.assert_outcomes(passed=1, deselected=1)
