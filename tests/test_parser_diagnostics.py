from pytest_dsl.cli import execute_dsl_file
from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import format_parse_errors, parse_with_error_handling


def test_parse_error_reports_line_column_source_and_fix_suggestion():
    dsl = '@name: "bad keyword call"\n[打印] 内容: "missing comma"'

    _ast, errors = parse_with_error_handling(dsl, lexer=get_lexer())

    assert errors
    first = errors[0]
    assert first["line"] == 2
    assert first["column"] == 8
    assert first["source_line"] == '[打印] 内容: "missing comma"'
    assert first["marker"] == "       ^"
    assert "第 2 行第 8 列" in first["message"]
    assert "参数前缺少逗号" in first["suggestion"]

    formatted = format_parse_errors(errors)
    assert '[打印] 内容: "missing comma"' in formatted
    assert "       ^" in formatted
    assert "修改建议：" in formatted
    assert "Token COLON" not in formatted


def test_eof_error_points_to_unclosed_block_start():
    dsl = """@name: "missing end"
value = 1
if ${value} == 1 do
    [打印], 内容: "missing end"
"""

    _ast, errors = parse_with_error_handling(dsl, lexer=get_lexer())

    assert errors
    first = errors[0]
    assert first["line"] == 4
    assert "文件结尾" in first["message"]
    assert "第 3 行开始的 if 块可能缺少 end" in first["suggestion"]


def test_lexer_error_for_unclosed_string_is_collected():
    dsl = '[打印], 内容: "abc'

    _ast, errors = parse_with_error_handling(dsl, lexer=get_lexer())

    assert errors
    first = errors[0]
    assert first["kind"] == "lexer"
    assert first["line"] == 1
    assert first["column"] == 11
    assert "字符串未闭合" in first["message"]
    assert "补上结束引号" in first["suggestion"]


def test_crlf_line_endings_do_not_create_carriage_return_errors():
    dsl = (
        '@name: "crlf"\r\n'
        '[打印], 内容: "ssh，到${install_location}上执行连接器卸载脚本，'
        '执行命令：${uninstall_command}"\r\n'
        'value = 1\r\n'
    )

    ast, errors = parse_with_error_handling(dsl, lexer=get_lexer())

    assert errors == []
    assert ast is not None


def test_crlf_inside_multiline_string_is_supported():
    dsl = (
        '@name: "multiline crlf"\r\n'
        '[打印], 内容: """\r\n'
        'line1\r\n'
        'line2\r\n'
        '"""\r\n'
    )

    ast, errors = parse_with_error_handling(dsl, lexer=get_lexer())

    assert errors == []
    assert ast is not None


def test_common_copied_whitespace_does_not_create_lexer_errors():
    dsl = (
        '\ufeff@name: "copied whitespace"\n'
        '\xa0[打印], 内容: "nbsp indent"\n'
        '\u3000[打印], 内容: "fullwidth indent"\n'
    )

    ast, errors = parse_with_error_handling(dsl, lexer=get_lexer())

    assert errors == []
    assert ast is not None


def test_cli_prints_readable_parse_errors_without_raw_dict(tmp_path, capsys):
    dsl_file = tmp_path / "bad.dsl"
    dsl_file.write_text('[打印] 内容: "missing comma"', encoding="utf-8")

    ok = execute_dsl_file(str(dsl_file), get_lexer(), None, object())

    assert ok is False
    output = capsys.readouterr().out
    assert "解析失败" in output
    assert "第 1 行第 8 列" in output
    assert '[打印] 内容: "missing comma"' in output
    assert "修改建议：" in output
    assert "{'message'" not in output
