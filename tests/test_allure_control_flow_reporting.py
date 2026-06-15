import json
import subprocess
import sys


def _walk_steps(node):
    for step in node.get("steps", []):
        yield step
        yield from _walk_steps(step)


def test_return_control_flow_does_not_create_broken_allure_step(tmp_path):
    dsl_file = tmp_path / "return_reporting.dsl"
    dsl_file.write_text(
        '''
@name: "return reporting"

function make_value() do
    return "ready"
end

value = [make_value]
[断言], 条件: "'${value}' == 'ready'", 消息: "return value should flow out"
''',
        encoding="utf-8",
    )
    allure_dir = tmp_path / "allure-results"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(dsl_file),
            "--alluredir",
            str(allure_dir),
            "-q",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr

    result_files = list(allure_dir.glob("*-result.json"))
    assert result_files
    results = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in result_files
    ]
    return_steps = [
        step
        for result in results
        for step in _walk_steps(result)
        if step.get("name") == "执行返回语句"
    ]

    assert results[0]["status"] == "passed"
    assert not [
        step for step in return_steps
        if step.get("status") == "broken"
    ]
