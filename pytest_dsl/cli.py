"""
pytest-dsl命令行入口

提供独立的命令行工具，用于执行DSL文件。
"""

import sys
import argparse
import pytest
import os
from pathlib import Path

from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import get_parser
from pytest_dsl.core.dsl_executor import DSLExecutor
from pytest_dsl.core.yaml_loader import load_yaml_variables_from_args
from pytest_dsl.core.auto_directory import SETUP_FILE_NAME, TEARDOWN_FILE_NAME, execute_hook_file
from pytest_dsl.core.plugin_discovery import load_all_plugins


def read_file(filename):
    """读取 DSL 文件内容"""
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='执行DSL测试文件')
    parser.add_argument('path', help='要执行的DSL文件路径或包含DSL文件的目录')
    parser.add_argument('--yaml-vars', action='append', default=[],
                       help='YAML变量文件路径，可以指定多个文件 (例如: --yaml-vars vars1.yaml --yaml-vars vars2.yaml)')
    parser.add_argument('--yaml-vars-dir', default=None,
                       help='YAML变量文件目录路径，将加载该目录下所有.yaml文件')

    return parser.parse_args()


def load_yaml_variables(args):
    """从命令行参数加载YAML变量"""
    # 使用统一的加载函数，包含远程服务器自动连接功能
    try:
        load_yaml_variables_from_args(
            yaml_files=args.yaml_vars,
            yaml_vars_dir=args.yaml_vars_dir,
            project_root=os.getcwd()  # CLI模式下使用当前工作目录作为项目根目录
        )
    except Exception as e:
        print(f"加载YAML变量失败: {str(e)}")
        sys.exit(1)


def execute_dsl_file(file_path, lexer, parser, executor):
    """执行单个DSL文件"""
    try:
        print(f"执行文件: {file_path}")
        dsl_code = read_file(file_path)
        ast = parser.parse(dsl_code, lexer=lexer)
        executor.execute(ast)
        return True
    except Exception as e:
        print(f"执行失败 {file_path}: {e}")
        return False


def find_dsl_files(directory):
    """查找目录中的所有DSL文件"""
    dsl_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.dsl', '.auto')) and file not in [SETUP_FILE_NAME, TEARDOWN_FILE_NAME]:
                dsl_files.append(os.path.join(root, file))
    return dsl_files


def main():
    """命令行入口点"""
    args = parse_args()
    path = args.path

    # 加载内置关键字插件
    load_all_plugins()

    # 加载YAML变量（包括远程服务器自动连接）
    load_yaml_variables(args)

    lexer = get_lexer()
    parser = get_parser()
    executor = DSLExecutor()

    # 检查路径是文件还是目录
    if os.path.isfile(path):
        # 执行单个文件
        success = execute_dsl_file(path, lexer, parser, executor)
        if not success:
            sys.exit(1)
    elif os.path.isdir(path):
        # 执行目录中的所有DSL文件
        print(f"执行目录: {path}")

        # 先执行目录的setup文件（如果存在）
        setup_file = os.path.join(path, SETUP_FILE_NAME)
        if os.path.exists(setup_file):
            execute_hook_file(Path(setup_file), True, path)

        # 查找并执行所有DSL文件
        dsl_files = find_dsl_files(path)
        if not dsl_files:
            print(f"目录中没有找到DSL文件: {path}")
            sys.exit(1)

        print(f"找到 {len(dsl_files)} 个DSL文件")

        # 执行所有DSL文件
        failures = 0
        for file_path in dsl_files:
            success = execute_dsl_file(file_path, lexer, parser, executor)
            if not success:
                failures += 1

        # 最后执行目录的teardown文件（如果存在）
        teardown_file = os.path.join(path, TEARDOWN_FILE_NAME)
        if os.path.exists(teardown_file):
            execute_hook_file(Path(teardown_file), False, path)

        # 如果有失败的测试，返回非零退出码
        if failures > 0:
            print(f"总计 {failures}/{len(dsl_files)} 个测试失败")
            sys.exit(1)
        else:
            print(f"所有 {len(dsl_files)} 个测试成功完成")
    else:
        print(f"路径不存在: {path}")
        sys.exit(1)


if __name__ == '__main__':
    main()
