# 测试DSL解析器功能

import pytest
from pytest_dsl.core.parser import get_parser, get_lexer
from pytest_dsl.core.dsl_executor import DSLExecutor


@pytest.mark.usefixtures("keep_dsl_variables")
def test_dsl_parser():
    """测试DSL解析器功能"""
    lexer = get_lexer()
    parser = get_parser()
    
    # 测试简单的DSL代码片段
    test_input = """
    @name: 测试用例
    @description: 这是一个测试
    
    [打印],内容:'Hello World'
    number = 5
    """
    # 使用解析器将DSL字符串解析为AST节点
    parsed_ast = parser.parse(test_input, lexer=lexer)
    
    dsl_executor = DSLExecutor()
    dsl_executor.execute(parsed_ast)

    assert dsl_executor.variables["number"] == 5
    
    