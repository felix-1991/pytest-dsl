from pathlib import Path

from pytest_dsl.core.auto_decorator import resolve_case_data_source
from pytest_dsl.workbench.suite_generator import (
    ROOT_SUITE_ID,
    build_pytest_targets,
    discover_convention_suites,
    generate_pytest_files,
    make_test_function_name,
)


def write_file(root: Path, relative_path: str, content: str = "") -> Path:
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def suite_by_id(suites):
    return {suite["id"]: suite for suite in suites}


def test_discovers_first_level_suites_and_excludes_hook_files(tmp_path):
    write_file(tmp_path, "tests/setup.dsl")
    write_file(tmp_path, "tests/teardown.auto")
    write_file(tmp_path, "tests/root_case.dsl")
    write_file(tmp_path, "tests/test_smoke.py")
    write_file(tmp_path, "tests/api/setup.dsl")
    write_file(tmp_path, "tests/api/auth/login.dsl")
    write_file(tmp_path, "tests/api/auth/logout.auto")
    write_file(tmp_path, "tests/api/auth/teardown.dsl")
    write_file(tmp_path, "tests/api/test_contract.py")
    write_file(tmp_path, "tests/api/auth/test_token_rules.py")
    write_file(tmp_path, "tests/ui/pages/dashboard.dsl")
    write_file(tmp_path, "tests/_support/test_helper.py")
    write_file(tmp_path, "tests/api/auth/.pytest-dsl-generated/test_dsl_cases.py")

    suites = suite_by_id(discover_convention_suites(tmp_path))

    assert list(suites) == [ROOT_SUITE_ID, "api", "api/auth", "ui/pages"]
    assert suites[ROOT_SUITE_ID]["rootPath"] == "tests"
    assert suites[ROOT_SUITE_ID]["dslCaseCount"] == 1
    assert suites[ROOT_SUITE_ID]["pythonTestCount"] == 1
    assert suites[ROOT_SUITE_ID]["pythonTestFiles"] == ["tests/test_smoke.py"]
    assert suites["api"]["rootPath"] == "tests/api"
    assert suites["api"]["dslCaseCount"] == 0
    assert suites["api"]["pythonTestCount"] == 1
    assert suites["api"]["pythonTestFiles"] == ["tests/api/test_contract.py"]
    assert suites["api/auth"]["dslCaseCount"] == 2
    assert suites["api/auth"]["pythonTestCount"] == 1
    assert suites["api/auth"]["generatedFiles"] == []
    assert suites["ui/pages"]["dslCaseCount"] == 1


def test_builds_directory_pytest_targets_without_generating_files(tmp_path):
    write_file(tmp_path, "tests/root_case.dsl", "[打印], 内容: \"root\"\n")
    write_file(tmp_path, "tests/api/auth/login.dsl", "[打印], 内容: \"login\"\n")
    write_file(tmp_path, "tests/api/auth/logout.dsl", "[打印], 内容: \"logout\"\n")
    write_file(tmp_path, "tests/api/order/create.dsl", "[打印], 内容: \"order\"\n")
    write_file(tmp_path, "tests/api/test_contract.py", "def test_contract():\n    pass\n")
    write_file(tmp_path, "tests/ui/pages/dashboard.dsl", "[打印], 内容: \"dashboard\"\n")

    suites = discover_convention_suites(tmp_path)
    generated = generate_pytest_files(tmp_path, selected_suite_ids=["api"])
    refreshed = suite_by_id(discover_convention_suites(tmp_path))

    assert generated == []
    assert refreshed["api"]["generatedFiles"] == []
    assert not (tmp_path / "tests/api/auth/.pytest-dsl-generated/test_dsl_cases.py").exists()

    targets = build_pytest_targets(tmp_path, selected_suite_ids=["api"])
    assert targets == ["tests/api"]
    assert suites[1]["id"] == "api"


def test_selected_all_expands_to_tests_directory_and_test_names_are_stable(tmp_path):
    write_file(tmp_path, "tests/root_case.dsl")
    write_file(tmp_path, "tests/api/auth/create-user.dsl")
    write_file(tmp_path, "tests/ui/pages/create_user.dsl")

    generated = generate_pytest_files(tmp_path, selected_suite_ids=["all"])
    targets = build_pytest_targets(tmp_path, selected_suite_ids=["all"])

    assert generated == []
    assert targets == ["tests"]
    assert make_test_function_name(Path("create-user.dsl"), used_names=set()) == "test_create_user"
    assert make_test_function_name(Path("create_user.dsl"), used_names={"test_create_user"}).startswith(
        "test_create_user_"
    )


def test_data_source_file_resolves_relative_to_dsl_case_directory(tmp_path, monkeypatch):
    case_file = write_file(tmp_path, "tests/api/auth/login.dsl")
    data_file = write_file(tmp_path, "tests/api/auth/login_data.csv", "user\nalice\n")
    monkeypatch.chdir(tmp_path)

    original = {"file": "login_data.csv", "format": "csv"}
    resolved = resolve_case_data_source(case_file, original)

    assert resolved == {"file": str(data_file.resolve()), "format": "csv"}
    assert original == {"file": "login_data.csv", "format": "csv"}
