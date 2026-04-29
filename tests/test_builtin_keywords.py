import json
import re
import string
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import pytest_dsl.keywords  # noqa: F401 - import registers builtin keywords
from pytest_dsl.core.context import TestContext as DSLContext
from pytest_dsl.core.keyword_manager import keyword_manager
from pytest_dsl.keywords import assertion_keywords, global_keywords, http_keywords
from pytest_dsl.keywords import system_keywords


def test_builtin_keywords_are_registered_with_expected_metadata():
    expected_keywords = {
        "打印",
        "返回结果",
        "等待",
        "获取当前时间",
        "生成随机字符串",
        "生成随机数",
        "字符串操作",
        "日志",
        "执行命令",
        "求和",
        "获取长度",
        "获取最大值",
        "获取最小值",
        "绝对值",
        "四舍五入",
        "转换为字符串",
        "转换为整数",
        "转换为浮点数",
        "转换为布尔值",
        "设置全局变量",
        "获取全局变量",
        "删除全局变量",
        "清除所有全局变量",
        "断言",
        "JSON断言",
        "JSON提取",
        "类型断言",
        "数据比较",
        "HTTP请求",
    }

    for name in expected_keywords:
        info = keyword_manager.get_keyword_info(name)
        assert info is not None, f"{name} should be registered"
        assert info["source_type"] == "builtin"
        assert info["returns"] is not None


def test_keyword_manager_execute_applies_builtin_defaults(monkeypatch):
    slept = []
    monkeypatch.setattr(system_keywords.time, "sleep", slept.append)

    assert keyword_manager.execute("返回结果", result=123) == 123
    assert keyword_manager.execute("等待") is None
    assert slept == [1.0]

    random_value = keyword_manager.execute("生成随机字符串")
    assert len(random_value) == 8
    assert set(random_value) <= set(string.ascii_letters + string.digits)

    number = keyword_manager.execute("生成随机数", min=5, max=5)
    assert number == 5


def test_basic_debug_wait_time_random_and_log_keywords(monkeypatch, capsys):
    system_keywords.print_content(content="hello")
    assert "内容: hello" in capsys.readouterr().out

    assert system_keywords.return_result(result={"ok": True}) == {"ok": True}

    slept = []
    monkeypatch.setattr(system_keywords.time, "sleep", slept.append)
    assert system_keywords.wait_seconds(seconds="0.25") is None
    assert slept == [0.25]

    timestamp = system_keywords.get_current_time()
    assert isinstance(timestamp, int)
    formatted = system_keywords.get_current_time(format="%Y-%m-%d", timezone="UTC")
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", formatted)

    letters = system_keywords.generate_random_string(length=32, type="letters")
    assert len(letters) == 32
    assert set(letters) <= set(string.ascii_letters)

    digits = system_keywords.generate_random_string(length="16", type="digits")
    assert len(digits) == 16
    assert digits.isdigit()

    unknown_type = system_keywords.generate_random_string(length=12, type="unknown")
    assert len(unknown_type) == 12
    assert set(unknown_type) <= set(string.ascii_letters + string.digits)

    all_chars = system_keywords.generate_random_string(length=64, type="all")
    assert len(all_chars) == 64
    assert set(all_chars) <= set(string.ascii_letters + string.digits + string.punctuation)

    integer = system_keywords.generate_random_number(min=3, max=3, decimals=0)
    assert integer == 3
    assert isinstance(integer, int)

    decimal = system_keywords.generate_random_number(min=1, max=1, decimals=2)
    assert decimal == 1.0
    assert isinstance(decimal, float)

    assert system_keywords.log_message(level="NOT_A_LEVEL", message="fallback") is True


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"operation": "concat", "string": "foo", "param1": "bar"}, "foobar"),
        ({"operation": "replace", "string": "foo bar", "param1": "bar", "param2": "baz"}, "foo baz"),
        ({"operation": "split", "string": "a,b,c", "param1": ","}, ["a", "b", "c"]),
        ({"operation": "split", "string": "a,b,c", "param1": ",", "param2": "1"}, "b"),
        ({"operation": "split", "string": "a,b,c", "param1": ",", "param2": "9"}, ["a", "b", "c"]),
        ({"operation": "split", "string": "a,b,c", "param1": ",", "param2": "-1"}, ["a", "b", "c"]),
        ({"operation": "split", "string": "a b  c"}, ["a", "b", "c"]),
        ({"operation": "upper", "string": "Abc"}, "ABC"),
        ({"operation": "lower", "string": "Abc"}, "abc"),
        ({"operation": "strip", "string": "  value  "}, "value"),
        ({"operation": "unknown", "string": "  value  "}, "value"),
    ],
)
def test_string_operation_variants(kwargs, expected):
    assert system_keywords.string_operation(**kwargs) == expected


def test_command_keyword_returns_process_result():
    result = system_keywords.execute_command(command="printf builtin", timeout=2)

    assert result == {"returncode": 0, "stdout": "builtin", "stderr": ""}


def test_command_keyword_handles_timeout():
    result = system_keywords.execute_command(
        command="python -c 'import time; time.sleep(1)'",
        timeout=0.01,
    )

    assert result["returncode"] == -1
    assert "timed out" in result["stderr"]


def test_command_keyword_handles_uncaptured_output_and_subprocess_errors(monkeypatch):
    result = system_keywords.execute_command(
        command="printf hidden",
        timeout=2,
        capture_output=False,
    )
    assert result == {"returncode": 0, "stdout": "", "stderr": ""}

    def raise_os_error(*args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr(system_keywords.subprocess, "run", raise_os_error)

    error_result = system_keywords.execute_command(command="anything")
    assert error_result == {"returncode": -1, "stdout": "", "stderr": "boom"}


def test_math_and_conversion_keywords_cover_success_and_error_paths():
    assert system_keywords.sum_values(data=[1, 2, 3], start=4) == 10
    with pytest.raises(ValueError, match="数据必须是可迭代"):
        system_keywords.sum_values(data="123")

    assert system_keywords.get_length(obj=None) == 0
    assert system_keywords.get_length(obj={"a": 1, "b": 2}) == 2
    with pytest.raises(TypeError):
        system_keywords.get_length(obj=1)

    assert system_keywords.get_max_value(data=[1, 3, 2]) == 3
    assert system_keywords.get_max_value(data=9) == 9
    assert system_keywords.get_max_value(data=[], default="empty") == "empty"
    with pytest.raises(ValueError, match="数据不能为空"):
        system_keywords.get_max_value(data=None)
    with pytest.raises(ValueError, match="数据列表为空"):
        system_keywords.get_max_value(data=[])

    assert system_keywords.get_min_value(data=[1, 3, 2]) == 1
    assert system_keywords.get_min_value(data=9) == 9
    assert system_keywords.get_min_value(data=[], default="empty") == "empty"
    with pytest.raises(ValueError, match="数据不能为空"):
        system_keywords.get_min_value(data=None)
    with pytest.raises(ValueError, match="数据列表为空"):
        system_keywords.get_min_value(data=[])

    assert system_keywords.get_absolute_value(number=-7) == 7
    with pytest.raises(ValueError, match="数值不能为空"):
        system_keywords.get_absolute_value(number=None)

    assert system_keywords.round_number(number=3.14159, ndigits=2) == 3.14
    assert system_keywords.round_number(number=3.6, ndigits=0) == 4
    with pytest.raises(ValueError, match="数值不能为空"):
        system_keywords.round_number(number=None)

    assert system_keywords.convert_to_string(value={"a": 1}) == "{'a': 1}"
    assert system_keywords.convert_to_string(value=None) == "None"
    assert system_keywords.convert_to_integer(value="ff", base=16) == 255
    assert system_keywords.convert_to_integer(value=3.9) == 3
    assert system_keywords.convert_to_float(value="3.5") == 3.5
    assert system_keywords.convert_to_boolean(value="") is False
    assert system_keywords.convert_to_boolean(value="false") is True

    with pytest.raises(ValueError, match="值不能为空"):
        system_keywords.convert_to_integer(value=None)
    with pytest.raises(ValueError, match="值不能为空"):
        system_keywords.convert_to_float(value=None)


def test_global_variable_keywords_return_uniform_remote_shape():
    context = DSLContext()
    global_keywords.clear_all_global_variables(context=context)

    set_result = global_keywords.set_global_variable(
        name="builtin_name",
        value={"v": 1},
        context=context,
    )
    assert set_result["result"] == {"v": 1}
    assert set_result["captures"] == {}
    assert set_result["metadata"] == {
        "variable_name": "builtin_name",
        "operation": "set_global_variable",
    }

    get_result = global_keywords.get_global_variable(
        name="builtin_name",
        context=context,
    )
    assert get_result["result"] == {"v": 1}
    assert get_result["metadata"]["operation"] == "get_global_variable"

    delete_result = global_keywords.delete_global_variable(
        name="builtin_name",
        context=context,
    )
    assert delete_result["result"] is True
    assert delete_result["metadata"]["operation"] == "delete_global_variable"

    with pytest.raises(Exception, match="全局变量未定义"):
        global_keywords.get_global_variable(name="builtin_name", context=context)

    clear_result = global_keywords.clear_all_global_variables(context=context)
    assert clear_result["result"] is True
    assert clear_result["metadata"] == {"operation": "clear_all_global_variables"}


@pytest.mark.parametrize(
    "condition",
    [
        "1 + 1 == 2",
        "10 >= 2",
        "2 <= 2",
        "hello world contains world",
        "hello world not_contains bye",
        "abc123 matches ^abc\\d+$",
        "2 in [1, 2, 3]",
        "4 not in [1, 2, 3]",
        "not False",
    ],
)
def test_assert_condition_accepts_supported_operators(condition):
    assert assertion_keywords.assert_condition(condition=condition) is True


def test_assert_condition_replaces_variables_and_rejects_non_boolean_eval():
    replacer = Mock()
    replacer.replace_in_string.side_effect = lambda value: (
        value.replace("${left}", "10").replace("${right}", "5")
    )
    context = SimpleNamespace(
        executor=SimpleNamespace(variable_replacer=replacer),
        get=lambda key, default=None: {"allowed": [1, 2, 3]}.get(key, default),
    )

    assert assertion_keywords.assert_condition(
        condition="${left} > ${right}",
        context=context,
    ) is True
    assert assertion_keywords.assert_condition(
        condition="2 in allowed",
        context=context,
    ) is True

    with pytest.raises(AssertionError, match="表达式结果不是布尔值"):
        assertion_keywords.assert_condition(condition="1 + 1")


def test_assert_condition_failure_and_invalid_regex_are_reported():
    with pytest.raises(AssertionError, match="断言失败详情"):
        assertion_keywords.assert_condition(condition="1 == 2", message="should fail")

    with pytest.raises(ValueError, match="无效的正则表达式"):
        assertion_keywords.assert_condition(condition="abc matches [")


@pytest.mark.parametrize(
    ("actual", "expected", "operator"),
    [
        (1, 2, "!="),
        (3, 2, ">"),
        (2, 3, "<"),
        (3, 3, ">="),
        (3, 3, "<="),
        ("abcdef", "bc", "contains"),
        ("abcdef", "xy", "not_contains"),
        ([1, 2], 2, "contains"),
        ([1, 2], 3, "not_contains"),
        (True, True, "and"),
        (False, True, "or"),
        ([1, 2], 3, "not in"),
        (False, None, "not"),
    ],
)
def test_compare_values_operator_matrix(actual, expected, operator):
    assert assertion_keywords.compare_values(
        actual=actual,
        expected=expected,
        operator=operator,
    ) is True


def test_json_assert_extract_type_and_compare_keywords():
    payload = {
        "status": "ok",
        "items": [
            {"id": 1, "name": "first"},
            {"id": 2, "name": "second"},
        ],
        "meta": {"total": 2},
    }

    assert assertion_keywords.extract_json(json_data=json.dumps(payload), jsonpath="$.status") == "ok"
    assert assertion_keywords.extract_json(json_data=payload, jsonpath="$.items[*].id") == [1, 2]
    assert assertion_keywords.extract_json(json_data=payload, jsonpath="$.missing") is None
    with pytest.raises(ValueError, match="JSONPath提取错误"):
        assertion_keywords.extract_json(json_data=payload, jsonpath="$[")

    assert assertion_keywords.assert_json(
        json_data=payload,
        jsonpath="$.meta.total",
        expected_value=1,
        operator=">",
    ) is True
    with pytest.raises(AssertionError, match="bad json assertion"):
        assertion_keywords.assert_json(
            json_data=payload,
            jsonpath="$.status",
            expected_value="failed",
            message="bad json assertion",
        )
    with pytest.raises(ValueError, match="无效的JSON数据"):
        assertion_keywords.extract_json(json_data="{", jsonpath="$.status")

    assert assertion_keywords.assert_type(value="text", type="string") is True
    assert assertion_keywords.assert_type(value="3.14", type="number") is True
    assert assertion_keywords.assert_type(value="false", type="boolean") is True
    assert assertion_keywords.assert_type(value='["a", "b"]', type="list") is True
    assert assertion_keywords.assert_type(value='{"a": 1}', type="object") is True
    assert assertion_keywords.assert_type(value="{'a': 1}", type="object") is True
    assert assertion_keywords.assert_type(value="null", type="null") is True
    with pytest.raises(AssertionError, match="类型断言失败"):
        assertion_keywords.assert_type(value="text", type="number")
    with pytest.raises(ValueError, match="不支持的类型"):
        assertion_keywords.assert_type(value="text", type="tuple")

    assert assertion_keywords.compare_values(actual="1 + 2", expected=3) is True
    assert assertion_keywords.compare_values(actual="true", expected=True) is True
    assert assertion_keywords.compare_values(actual="abcdef", expected="^abc", operator="matches") is True
    with pytest.raises(AssertionError, match="mismatch"):
        assertion_keywords.compare_values(actual=1, expected=2, message="mismatch")
    with pytest.raises(ValueError, match="不支持的比较运算符"):
        assertion_keywords.compare_values(actual=1, expected=1, operator="===")


def test_http_file_references_and_retry_config_are_normalized(tmp_path):
    json_file = tmp_path / "payload.json"
    json_file.write_text('{"name": "alice", "age": 20}', encoding="utf-8")
    yaml_file = tmp_path / "headers.yaml"
    yaml_file.write_text("X-Test: yes\n", encoding="utf-8")
    text_file = tmp_path / "body.txt"
    text_file.write_text("plain text", encoding="utf-8")
    templated_text_file = tmp_path / "template.txt"
    templated_text_file.write_text("hello ${name}", encoding="utf-8")
    context = DSLContext()
    context.set("name", "alice")

    assert http_keywords._process_file_reference(f"@file:{json_file}") == {
        "name": "alice",
        "age": 20,
    }
    assert http_keywords._process_file_reference(
        {"file_ref": {"path": str(yaml_file), "type": "yaml"}}
    ) == {"X-Test": True}
    assert http_keywords._process_file_reference(
        {"file_ref": {"path": str(text_file), "type": "text"}}
    ) == "plain text"
    assert http_keywords._process_file_reference(
        f"@file_template:{templated_text_file}",
        test_context=context,
    ) == "hello alice"
    assert http_keywords._process_file_reference(
        {"file_ref": str(text_file)},
        allow_vars=False,
    ) == "plain text"
    assert http_keywords._process_file_reference("not a ref") == "not a ref"
    with pytest.raises(ValueError, match="file_ref必须包含path字段"):
        http_keywords._process_file_reference({"file_ref": {"type": "json"}})

    config = {
        "request": {
            "json": f"@file:{json_file}",
            "headers": {"file_ref": {"path": str(yaml_file), "type": "yaml"}},
            "data": {"file_ref": {"path": str(text_file), "type": "text"}},
        }
    }
    processed = http_keywords._process_request_config(config)
    assert processed["request"]["json"]["name"] == "alice"
    assert processed["request"]["headers"] == {"X-Test": True}
    assert processed["request"]["data"] == "plain text"
    assert http_keywords._process_request_config("raw") == "raw"

    assert http_keywords._normalize_retry_config({}) == {
        "enabled": False,
        "count": 3,
        "interval": 1.0,
        "all": False,
        "indices": [],
        "specific": {},
    }

    command_retry = http_keywords._normalize_retry_config(
        {},
        assert_retry_count="2",
        assert_retry_interval="0.1",
    )
    assert command_retry == {
        "enabled": True,
        "count": 2,
        "interval": 0.1,
        "all": True,
        "indices": [],
        "specific": {},
    }

    specific_retry = http_keywords._normalize_retry_config(
        {
            "retry_assertions": {
                "count": 4,
                "interval": 0,
                "indices": [1],
                "specific": {2: {"count": 1}},
            }
        }
    )
    assert specific_retry["enabled"] is True
    assert specific_retry["count"] == 4
    assert specific_retry["indices"] == [1]
    assert specific_retry["specific"][2] == {"count": 1}
    assert specific_retry["specific"]["2"] == {"count": 1}

    legacy_retry = http_keywords._normalize_retry_config(
        {"retry": {"count": 3, "interval": 0.2}}
    )
    assert legacy_retry["enabled"] is True
    assert legacy_retry["count"] == 3
    assert legacy_retry["interval"] == 0.2
    assert legacy_retry["all"] is True

    with pytest.raises(FileNotFoundError, match="找不到引用的文件"):
        http_keywords._process_file_reference(f"@file:{tmp_path / 'missing.json'}")


def test_http_file_reference_reports_invalid_json_and_yaml(tmp_path):
    invalid_json = tmp_path / "bad.json"
    invalid_json.write_text("{", encoding="utf-8")
    invalid_yaml = tmp_path / "bad.yaml"
    invalid_yaml.write_text("key: [", encoding="utf-8")

    with pytest.raises(ValueError, match="无效的JSON文件"):
        http_keywords._process_file_reference(f"@file:{invalid_json}")
    with pytest.raises(ValueError, match="无效的YAML文件"):
        http_keywords._process_file_reference(f"@file:{invalid_yaml}")


def test_deep_merge_recursively_merges_template_and_user_config():
    base = {
        "request": {
            "method": "GET",
            "headers": {"Accept": "application/json", "X-Base": "1"},
        },
        "asserts": [["status", "eq", 200]],
    }
    override = {
        "request": {
            "method": "POST",
            "headers": {"X-User": "2"},
        },
        "captures": {"id": ["jsonpath", "$.id"]},
    }

    merged = http_keywords._deep_merge(base, override)

    assert merged is base
    assert merged == {
        "request": {
            "method": "POST",
            "headers": {
                "Accept": "application/json",
                "X-Base": "1",
                "X-User": "2",
            },
        },
        "asserts": [["status", "eq", 200]],
        "captures": {"id": ["jsonpath", "$.id"]},
    }


def test_http_request_keyword_uses_template_merges_config_and_returns_side_effects(monkeypatch):
    context = DSLContext()
    context.set(
        "http_clients",
        {"default": {"base_url": "https://example.test", "timeout": 5}},
    )
    context.set(
        "http_templates",
        {
            "create_user": {
                "request": {
                    "method": "POST",
                    "path": "/users",
                    "headers": {"X-Template": "yes"},
                },
                "asserts": [["status", "eq", 201]],
            }
        },
    )
    context.set("user_id", 42)

    response = SimpleNamespace(
        status_code=201,
        headers={"Content-Type": "application/json"},
        text='{"ok": true}',
        url="https://example.test/users",
        elapsed=0.25,
        unserializable=lambda: None,
    )
    created = {}

    class FakeHTTPRequest:
        def __init__(self, config, client_name, session_name):
            created["config"] = config
            created["client_name"] = client_name
            created["session_name"] = session_name
            self.config = config
            self.captured_values = {"created_id": 42}

        def execute(self, disable_auth=False):
            created["disable_auth"] = disable_auth
            return response

        def process_asserts(self):
            created["asserted"] = True
            return ([{"result": True}], [])

    monkeypatch.setattr(http_keywords, "HTTPRequest", FakeHTTPRequest)

    result = http_keywords.http_request(
        context=context,
        template="create_user",
        config="""
request:
  headers:
    X-User: ${user_id}
captures:
  created_id: [jsonpath, "$.id"]
""",
        save_response="saved_response",
        disable_auth=True,
    )

    assert created["client_name"] == "default"
    assert created["session_name"] is None
    assert created["disable_auth"] is True
    assert created["asserted"] is True
    assert created["config"]["request"] == {
        "method": "POST",
        "path": "/users",
        "headers": {"X-Template": "yes", "X-User": 42},
    }
    assert created["config"]["captures"] == {"created_id": ["jsonpath", "$.id"]}
    assert result["result"] == {"created_id": 42}
    assert result["side_effects"]["variables"] == {"created_id": 42}
    assert result["side_effects"]["context_updates"]["response"] == {
        "status_code": 201,
        "headers": {"Content-Type": "application/json"},
        "text": '{"ok": true}',
        "url": "https://example.test/users",
    }
    assert result["metadata"] == {
        "response_time": 0.25,
        "status_code": 201,
        "url": "https://example.test/users",
        "keyword_type": "http_request",
    }
    assert context.get("created_id") == 42
    assert context.get("saved_response") is response


def test_http_request_keyword_rejects_missing_template():
    context = DSLContext()

    with pytest.raises(ValueError, match="未找到名为 'missing' 的HTTP请求模板"):
        http_keywords.http_request(context=context, template="missing", config="{}")


def test_http_request_keyword_rejects_invalid_yaml():
    context = DSLContext()

    with pytest.raises(ValueError, match="无效的YAML配置"):
        http_keywords.http_request(context=context, config="request: [")


def test_unified_retry_returns_immediately_when_assertions_pass():
    http_req = Mock()
    http_req.process_asserts.return_value = ([{"result": True}], [])

    result = http_keywords._process_assertions_with_unified_retry(
        http_req,
        {
            "enabled": True,
            "count": 3,
            "interval": 0,
            "all": True,
            "indices": [],
            "specific": {},
        },
    )

    assert result == [{"result": True}]
    http_req.execute.assert_not_called()
