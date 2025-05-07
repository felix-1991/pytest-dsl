"""
pytest-dsl命令行入口

提供独立的命令行工具，用于执行DSL文件。
"""

import sys
import argparse
import pytest
from pathlib import Path

from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import get_parser
from pytest_dsl.core.dsl_executor import DSLExecutor
from pytest_dsl.core.yaml_vars import yaml_vars


def read_file(filename):
    """读取 DSL 文件内容"""
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='执行DSL测试文件')
    parser.add_argument('dsl_file', help='要执行的DSL文件路径')
    parser.add_argument('--yaml-vars', action='append', default=[], 
                       help='YAML变量文件路径，可以指定多个文件 (例如: --yaml-vars vars1.yaml --yaml-vars vars2.yaml)')
    parser.add_argument('--yaml-vars-dir', default=None,
                       help='YAML变量文件目录路径，将加载该目录下所有.yaml文件')
    
    return parser.parse_args()


def load_yaml_variables(args):
    """从命令行参数加载YAML变量"""
    # 加载单个YAML文件
    if args.yaml_vars:
        yaml_vars.load_yaml_files(args.yaml_vars)
        print(f"已加载YAML变量文件: {', '.join(args.yaml_vars)}")
    
    # 加载目录中的YAML文件
    if args.yaml_vars_dir:
        yaml_vars_dir = args.yaml_vars_dir
        try:
            yaml_vars.load_from_directory(yaml_vars_dir)
            print(f"已加载YAML变量目录: {yaml_vars_dir}")
            loaded_files = yaml_vars.get_loaded_files()
            if loaded_files:
                dir_files = [f for f in loaded_files if Path(f).parent == Path(yaml_vars_dir)]
                if dir_files:
                    print(f"目录中加载的文件: {', '.join(dir_files)}")
        except NotADirectoryError:
            print(f"YAML变量目录不存在: {yaml_vars_dir}")
            sys.exit(1)


def main():
    """命令行入口点"""
    args = parse_args()
    
    # 加载YAML变量
    load_yaml_variables(args)
    
    lexer = get_lexer()
    parser = get_parser()
    executor = DSLExecutor()
    
    try:
        dsl_code = read_file(args.dsl_file)
        ast = parser.parse(dsl_code, lexer=lexer)
        executor.execute(ast)
    except Exception as e:
        print(f"执行失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 