import io
import json

from pytest_dsl import gui_runner


def _structured_events(output):
    prefix = gui_runner.GUI_EVENT_PREFIX
    events = []
    for line in output.splitlines():
        if line.startswith(prefix):
            events.append(json.loads(line[len(prefix):]))
    return events


def test_debug_run_emits_step_events_and_accepts_continue(tmp_path, monkeypatch, capsys):
    dsl_file = tmp_path / "case.dsl"
    dsl_file.write_text('[打印], 内容: "debug ok"\n', encoding="utf-8")
    monkeypatch.setattr("sys.stdin", io.StringIO("continue\n"))

    exit_code = gui_runner.debug_run(str(dsl_file), yaml_vars=[])

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

    exit_code = gui_runner.debug_run(str(dsl_file), yaml_vars=[], pause_from_line=2)

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
