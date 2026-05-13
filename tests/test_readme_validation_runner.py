from __future__ import annotations

import re

from examples.readme_validation import run_all_tests as runner


def test_executed_readme_examples_have_effective_assertions():
    missing_assertions = []

    for rel_path in runner.EXECUTION_FILES:
        target = (runner.SCRIPT_DIR / rel_path).resolve()
        content = target.read_text(encoding="utf-8")
        if "[断言]" not in content and "asserts:" not in content:
            missing_assertions.append(rel_path)

    assert missing_assertions == []


def test_syntax_only_files_are_not_counted_in_default_discovery():
    discovered = {path.name for path in runner.discover_dsl_files()}

    assert discovered.isdisjoint(runner.SYNTAX_ONLY_FILES)


def test_data_driven_pytest_examples_run_from_validation_directory(monkeypatch):
    calls = []

    class Result:
        returncode = 0
        stdout = "4 passed"
        stderr = ""

    def fake_run(cmd, cwd, capture_output, text, timeout):
        calls.append(
            {
                "cmd": cmd,
                "cwd": cwd,
                "capture_output": capture_output,
                "text": text,
                "timeout": timeout,
            }
        )
        return Result()

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    passed, failed, messages = runner.pytest_data_driven_examples()

    assert (passed, failed, messages) == (1, 0, [])
    assert calls == [
        {
            "cmd": [
                runner.sys.executable,
                "-m",
                "pytest",
                "test_runner.py",
                "-k",
                "data_driven",
                "-q",
            ],
            "cwd": str(runner.SCRIPT_DIR),
            "capture_output": True,
            "text": True,
            "timeout": 90,
        }
    ]


def test_materialize_temp_dsl_rewrites_imported_resources():
    mock_base_url = "http://mock.local"
    temp_file = runner._materialize_temp_dsl(runner.SCRIPT_DIR / "auth_test.dsl", mock_base_url)

    generated_files = [temp_file]
    try:
        content = temp_file.read_text(encoding="utf-8")
        imports = re.findall(r'@import:\s*"([^"]+)"', content)
        assert imports

        imported_contents = []
        for import_path in imports:
            imported_file = (temp_file.parent / import_path).resolve()
            generated_files.append(imported_file)
            imported_contents.append(imported_file.read_text(encoding="utf-8"))

        joined_imports = "\n".join(imported_contents)
        assert "https://jsonplaceholder.typicode.com" not in joined_imports
        assert mock_base_url in joined_imports
    finally:
        for generated in generated_files:
            if generated.exists() and generated.name.startswith(".tmp_"):
                generated.unlink()
