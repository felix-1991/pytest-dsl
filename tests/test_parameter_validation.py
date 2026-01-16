import pytest

from pytest_dsl.core.dsl_executor import DSLExecutor, DSLExecutionError
from pytest_dsl.core.keyword_manager import keyword_manager
from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import parse_with_error_handling


def test_unknown_keyword_param_raises_dsl_execution_error():
    @keyword_manager.register(
        name="ParamValidationTestKeyword",
        parameters=[
            {
                "name": "内容",
                "mapping": "content",
                "description": "内容",
                "default": None,
            }
        ],
    )
    def _kw(content=None, context=None):
        return content

    dsl = '[ParamValidationTestKeyword], 错误参数: "x"'
    ast, errors = parse_with_error_handling(dsl, lexer=get_lexer())
    assert errors == []
    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)

    with pytest.raises(DSLExecutionError) as exc:
        executor.execute(ast)

    msg = str(exc.value)
    print(msg)
    assert "不支持参数" in msg
    assert "错误参数" in msg
    assert "支持的参数" in msg

