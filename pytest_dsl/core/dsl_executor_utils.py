"""DSL执行器工具模块

该模块提供DSL文件的读取和执行功能，作为conftest.py和DSL执行器之间的桥梁。
"""

from pathlib import Path
from pytest_dsl.core.dsl_executor import DSLExecutor
from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import get_parser

# 获取词法分析器和解析器实例
lexer = get_lexer()
parser = get_parser()


def read_file(filename):
    """读取DSL文件内容

    Args:
        filename: 文件路径

    Returns:
        str: 文件内容
    """
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()


def execute_dsl_file(filename: str, executor: DSLExecutor = None) -> None:
    """执行DSL文件

    Args:
        filename: DSL文件路径
        executor: 可选的DSL执行器实例，如果不提供则创建新的
    """
    try:
        # 读取文件内容
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()

        # 创建或使用提供的执行器
        if executor is None:
            executor = DSLExecutor(enable_tracking=True)

        # 使用带跟踪功能的execute_from_content方法
        # 使用文件路径作为dsl_id以便于跟踪
        dsl_id = str(Path(filename).resolve())
        executor.execute_from_content(content, dsl_id=dsl_id)

    except Exception as e:
        # 如果是语法错误，记录并抛出
        if "语法错误" in str(e):
            print(f"DSL语法错误: {str(e)}")
            raise
        # 其他错误直接抛出
        raise


def extract_metadata_from_ast(ast):
    """从AST中提取元数据

    提取DSL文件中的元数据信息，如@data和@name标记。

    Args:
        ast: 解析后的抽象语法树

    Returns:
        tuple: (data_source, test_title) 元组，如果不存在则为None
    """
    data_source = None
    test_title = None

    for child in ast.children:
        if child.type == 'Metadata':
            for item in child.children:
                if item.type == '@data':
                    data_source = item.value
                elif item.type == '@name':
                    test_title = item.value
            if data_source and test_title:
                break

    return data_source, test_title
