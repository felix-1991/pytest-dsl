import io
import json
from pathlib import Path

from pytest_dsl.workbench import runner
from pytest_dsl.workbench.protocol import GUI_EVENT_PREFIX


def _structured_events(output):
    events = []
    for line in output.splitlines():
        if line.startswith(GUI_EVENT_PREFIX):
            events.append(json.loads(line[len(GUI_EVENT_PREFIX):]))
    return events


def test_debug_run_emits_step_events_and_accepts_continue(tmp_path, monkeypatch, capsys):
    dsl_file = tmp_path / "case.dsl"
    dsl_file.write_text('[打印], 内容: "debug ok"\n', encoding="utf-8")
    monkeypatch.setattr("sys.stdin", io.StringIO("continue\n"))

    exit_code = runner.debug_run(str(dsl_file), yaml_vars=[])

    assert exit_code == 0
    events = _structured_events(capsys.readouterr().out)
    assert any(
        event["type"] == "debug_step"
        and event["phase"] == "start"
        and event["line"] == 1
        and event["nodeType"] == "KeywordCall"
        for event in events
    )
    assert any(
        event["type"] == "debug_step"
        and event["phase"] == "finish"
        and event["status"] == "success"
        for event in events
    )


def test_debug_run_can_prepare_context_before_pausing_from_line(tmp_path, monkeypatch, capsys):
    dsl_file = tmp_path / "case.dsl"
    dsl_file.write_text(
        "\n".join([
            '[打印], 内容: "prep"',
            '[打印], 内容: "pause here"',
            "",
        ]),
        encoding="utf-8",
    )
    monkeypatch.setattr("sys.stdin", io.StringIO("continue\n"))

    exit_code = runner.debug_run(str(dsl_file), yaml_vars=[], pause_from_line=2)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "prep" in output
    events = _structured_events(output)
    start_events = [
        event
        for event in events
        if event["type"] == "debug_step" and event["phase"] == "start"
    ]
    assert [event["line"] for event in start_events] == [2]


def test_workbench_capabilities_command_reports_public_debug_features(capsys):
    exit_code = runner.main(["capabilities"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["protocol"] == 1
    assert payload["commands"] == ["syntax", "debug", "capabilities"]
    assert payload["features"]["pauseFromLine"] is True
    assert "selectionDebug" not in payload["features"]
    assert payload["features"]["selectionMaterialization"] is True
    assert payload["features"]["structuredDebugEvents"] is True


def test_pyproject_exposes_workbench_console_script():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert (
        'pytest-dsl-workbench = "pytest_dsl.workbench.runner:main"' in
        pyproject
    )
