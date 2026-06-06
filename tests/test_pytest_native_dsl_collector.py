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
    write_file(pytester.path, "tests/teardown.dsl", '[打印], 内容: "teardown"\n')
    write_file(pytester.path, "tests/case.auto", '[打印], 内容: "case"\n')

    result = run_pytest_dsl(pytester, "tests", "--collect-only", "-q")

    output = result.stdout.str()
    assert "tests/case.auto::case" in output
    assert "tests/setup.dsl::setup" not in output
    assert "tests/teardown.dsl::teardown" not in output


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
