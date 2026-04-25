from pytest_dsl.core.dsl_executor import DSLExecutor
from pytest_dsl.core.keyword_manager import keyword_manager
from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import parse_with_error_handling
from pytest_dsl.core.variable_utils import VariableReplacer


def _parse_assignment_expr(dsl: str):
    ast, errors = parse_with_error_handling(dsl, lexer=get_lexer())
    assert errors == []
    assignment = ast.children[1].children[0]
    return assignment.children[0]


def _executor_with_vars(**variables):
    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)
    executor.variable_replacer.local_variables.update(variables)
    for name, value in variables.items():
        executor.test_context.set(name, value)
    return executor


def test_expression_index_access_accepts_variable_index():
    expr = _parse_assignment_expr("fruit = items[i]")

    assert expr.type == "IndexAccessExpr"

    executor = _executor_with_vars(items=["苹果", "香蕉", "橙子"], i=1)
    assert executor.eval_expression(expr) == "香蕉"


def test_expression_index_access_accepts_expression_index():
    expr = _parse_assignment_expr("fruit = items[i + 1]")

    executor = _executor_with_vars(items=["苹果", "香蕉", "橙子"], i=1)
    assert executor.eval_expression(expr) == "橙子"


def test_expression_index_access_combines_with_property_access():
    expr = _parse_assignment_expr("name = users[i].name")

    executor = _executor_with_vars(
        users=[
            {"name": "张三", "role": "admin"},
            {"name": "李四", "role": "tester"},
        ],
        i=1,
    )

    assert executor.eval_expression(expr) == "李四"


def test_string_interpolation_uses_dynamic_index_expression():
    expr = _parse_assignment_expr(
        'message = "索引 ${i} 对应的水果: ${items[i]}"'
    )

    executor = _executor_with_vars(items=["苹果", "香蕉", "橙子"], i=2)

    assert executor.eval_expression(expr) == "索引 2 对应的水果: 橙子"


def test_placeholder_token_accepts_expression_body():
    expr = _parse_assignment_expr("next_index = ${i + 1}")

    executor = _executor_with_vars(i=1)

    assert executor.eval_expression(expr) == 2


def test_variable_replacer_keeps_existing_placeholder_api_with_dynamic_index():
    replacer = VariableReplacer(
        local_variables={"items": ["苹果", "香蕉", "橙子"], "i": 0}
    )

    assert replacer.replace_in_string("${items[i]}") == "苹果"


def test_variable_replacer_uses_executor_expression_semantics_for_numeric_strings():
    replacer = VariableReplacer()

    assert replacer.replace_in_string('${"10" > "2"}') is True
    assert replacer.replace_in_string('${"2" + 3}') == 5
    assert replacer.replace_in_string('${"2" - 1}') == 1
    assert replacer.replace_in_string('${2 in "abc2"}') is True


def test_executor_and_variable_replacer_share_placeholder_expression_semantics():
    ast, errors = parse_with_error_handling(
        'value = ${"10" > "2"}',
        lexer=get_lexer()
    )
    assert errors == []

    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)
    expr = ast.children[1].children[0].children[0]
    replacer = VariableReplacer()

    assert (
        replacer.replace_in_string('${"10" > "2"}') ==
        executor.eval_expression(expr)
    )


def test_for_range_loop_can_interpolate_list_item_by_loop_index():
    captured = []

    @keyword_manager.register(
        name="动态索引捕获",
        parameters=[
            {
                "name": "内容",
                "mapping": "content",
                "description": "捕获内容",
                "default": None,
            }
        ],
    )
    def _capture(content=None, context=None):
        captured.append(content)
        return content

    dsl = '''
items = ["苹果", "香蕉", "橙子"]

for i in range(0, 3) do
    [动态索引捕获], 内容: "索引 ${i} 对应的水果: ${items[i]}"
end
'''
    ast, errors = parse_with_error_handling(dsl, lexer=get_lexer())
    assert errors == []

    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)
    executor.execute(ast)

    assert captured == [
        "索引 0 对应的水果: 苹果",
        "索引 1 对应的水果: 香蕉",
        "索引 2 对应的水果: 橙子",
    ]


def test_keyword_assignment_followed_by_keyword_call_keeps_statement_boundary():
    calls = []

    @keyword_manager.register(
        name="动态索引提取",
        parameters=[
            {
                "name": "id",
                "mapping": "item_id",
                "description": "索引",
                "default": None,
            },
            {
                "name": "list",
                "mapping": "items_list",
                "description": "列表",
                "default": None,
            },
        ],
    )
    def _extract(item_id=None, items_list=None, context=None):
        calls.append(("extract", item_id, items_list))
        return items_list[item_id]

    @keyword_manager.register(
        name="动态索引比较",
        parameters=[
            {
                "name": "lhs",
                "mapping": "lhs",
                "description": "左值",
                "default": None,
            },
            {
                "name": "rhs",
                "mapping": "rhs",
                "description": "右值",
                "default": None,
            },
        ],
    )
    def _compare(lhs=None, rhs=None, context=None):
        calls.append(("compare", lhs, rhs))
        return lhs == rhs

    @keyword_manager.register(
        name="动态索引断言",
        parameters=[
            {
                "name": "条件",
                "mapping": "condition",
                "description": "条件",
                "default": None,
            },
        ],
    )
    def _assert(condition=None, context=None):
        calls.append(("assert", condition))
        assert condition == "True == True"
        return True

    dsl = '''
ids = [0, 1, 2]
items = ["A", "B", "C"]
res = ["A", "B", "C"]

for idx in range(0, 3) do
    itemRes = [动态索引提取], id: ${ids[${idx}]}, list: ${res}
    eq = [动态索引比较], lhs: ${items[${idx}]}, rhs: ${itemRes}
    [动态索引断言], 条件: "${eq} == True"
end
'''
    ast, errors = parse_with_error_handling(dsl, lexer=get_lexer())
    assert errors == []

    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)
    executor.execute(ast)

    assert calls == [
        ("extract", 0, ["A", "B", "C"]),
        ("compare", "A", "A"),
        ("assert", "True == True"),
        ("extract", 1, ["A", "B", "C"]),
        ("compare", "B", "B"),
        ("assert", "True == True"),
        ("extract", 2, ["A", "B", "C"]),
        ("compare", "C", "C"),
        ("assert", "True == True"),
    ]


def test_for_item_loop_accepts_list_literal_without_space_after_in():
    captured = []

    @keyword_manager.register(
        name="紧凑列表捕获",
        parameters=[
            {
                "name": "内容",
                "mapping": "content",
                "description": "捕获内容",
                "default": None,
            }
        ],
    )
    def _capture(content=None, context=None):
        captured.append(content)
        return content

    dsl = '''
for item in[1, 2] do
    [紧凑列表捕获], 内容: ${item}
end
'''
    ast, errors = parse_with_error_handling(dsl, lexer=get_lexer())
    assert errors == []

    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)
    executor.execute(ast)

    assert captured == [1, 2]
