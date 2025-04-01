"""
pytest-dsl命令行入口

提供独立的命令行工具，用于执行DSL文件。
"""

import sys
import pytest
from pathlib import Path

from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import get_parser
from pytest_dsl.core.dsl_executor import DSLExecutor


def read_file(filename):
    """读取 DSL 文件内容"""
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()


def main():
    """命令行入口点"""
    if len(sys.argv) < 2:
        print("用法: python -m pytest_dsl.cli <dsl_file>")
        sys.exit(1)
        
    filename = sys.argv[1]
    
    lexer = get_lexer()
    parser = get_parser()
    executor = DSLExecutor()
    
    try:
        dsl_code = read_file(filename)
        ast = parser.parse(dsl_code, lexer=lexer)
        executor.execute(ast)
    except Exception as e:
        print(f"执行失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 