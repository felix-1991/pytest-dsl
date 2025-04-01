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


def execute_dsl_file(file_path, executor=None):
    """执行DSL文件
    
    解析并执行指定的DSL文件。如果没有提供执行器实例，将创建一个新的实例。
    
    Args:
        file_path: DSL文件路径
        executor: 可选的DSLExecutor实例，如果不提供则创建新实例
        
    Returns:
        None
    """
    if not Path(file_path).exists():
        return
    print(f"执行DSL文件: {file_path}")
    dsl_code = read_file(file_path)
    ast = parser.parse(dsl_code, lexer=lexer)
    if executor is None:
        executor = DSLExecutor()
    executor.execute(ast)


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