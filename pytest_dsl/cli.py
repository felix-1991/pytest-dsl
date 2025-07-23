"""
pytest-dsl命令行入口

提供独立的命令行工具，用于执行DSL文件。
"""

import sys
import argparse
import os
from pathlib import Path

from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import get_parser
from pytest_dsl.core.dsl_executor import DSLExecutor
from pytest_dsl.core.yaml_loader import load_yaml_variables_from_args
from pytest_dsl.core.auto_directory import (
    SETUP_FILE_NAME, TEARDOWN_FILE_NAME, execute_hook_file
)
from pytest_dsl.core.keyword_loader import load_all_keywords
from pytest_dsl.core.keyword_utils import list_keywords as utils_list_keywords


def read_file(filename):
    """读取 DSL 文件内容"""
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()


def parse_args():
    """解析命令行参数"""
    import sys
    argv = sys.argv[1:]  # 去掉脚本名

    # 检查是否使用了子命令格式
    if argv and argv[0] in ['run', 'list-keywords', 'list']:
        # 使用新的子命令格式
        parser = argparse.ArgumentParser(description='执行DSL测试文件')
        subparsers = parser.add_subparsers(dest='command', help='可用命令')

        # 执行命令
        run_parser = subparsers.add_parser('run', help='执行DSL文件')
        run_parser.add_argument(
            'path',
            help='要执行的DSL文件路径或包含DSL文件的目录'
        )
        run_parser.add_argument(
            '--yaml-vars', action='append', default=[],
            help='YAML变量文件路径，可以指定多个文件 '
                 '(例如: --yaml-vars vars1.yaml '
                 '--yaml-vars vars2.yaml)'
        )
        run_parser.add_argument(
            '--yaml-vars-dir', default=None,
            help='YAML变量文件目录路径，'
                 '将加载该目录下所有.yaml文件'
        )

        # 关键字列表命令
        list_parser = subparsers.add_parser(
            'list-keywords',
            help='罗列所有可用关键字和参数信息'
        )
        
        # 简化的list命令（同list-keywords）
        list_simple_parser = subparsers.add_parser(
            'list',
            help='罗列所有可用关键字和参数信息'
        )
        # 为list-keywords添加参数
        for parser_obj in [list_parser, list_simple_parser]:
            parser_obj.add_argument(
                '--format', choices=['text', 'json', 'html'],
                default='text',
                help='输出格式：text(默认)、json 或 html'
            )
            parser_obj.add_argument(
                '--output', '-o', type=str, default=None,
                help='输出文件路径（json格式默认为keywords.json，html格式默认为keywords.html）'
            )
            parser_obj.add_argument(
                '--filter', type=str, default=None,
                help='过滤关键字名称（支持部分匹配）'
            )
            parser_obj.add_argument(
                '--category',
                choices=[
                    'builtin', 'plugin', 'custom',
                    'project_custom', 'remote', 'all'
                ],
                default='all',
                help='关键字类别：builtin(内置)、plugin(插件)、custom(自定义)、'
                     'project_custom(项目自定义)、remote(远程)、all(全部，默认)'
            )
            parser_obj.add_argument(
                '--include-remote', action='store_true',
                help='是否包含远程关键字（默认不包含）'
            )

        return parser.parse_args(argv)
    else:
        # 向后兼容模式
        parser = argparse.ArgumentParser(description='执行DSL测试文件')

        # 检查是否是list-keywords的旧格式
        if '--list-keywords' in argv:
            parser.add_argument('--list-keywords', action='store_true')
            parser.add_argument(
                '--format', choices=['text', 'json', 'html'], default='json'
            )
            parser.add_argument(
                '--output', '-o', type=str, default=None
            )
            parser.add_argument('--filter', type=str, default=None)
            parser.add_argument(
                '--category',
                choices=[
                    'builtin', 'plugin', 'custom',
                    'project_custom', 'remote', 'all'
                ],
                default='all'
            )
            parser.add_argument(
                '--include-remote', action='store_true'
            )
            parser.add_argument('path', nargs='?')  # 可选的路径参数
            parser.add_argument(
                '--yaml-vars', action='append', default=[]
            )
            parser.add_argument('--yaml-vars-dir', default=None)

            args = parser.parse_args(argv)
            args.command = 'list-keywords-compat'  # 标记为兼容模式
        else:
            # 默认为run命令的向后兼容模式
            parser.add_argument('path', nargs='?')
            parser.add_argument(
                '--yaml-vars', action='append', default=[]
            )
            parser.add_argument('--yaml-vars-dir', default=None)

            args = parser.parse_args(argv)
            args.command = 'run-compat'  # 标记为兼容模式

        return args


def list_keywords(output_format='json', name_filter=None,
                  category_filter='all', category_name_filter='all', 
                  tags_filter=None, output_file=None,
                  include_remote=False, group_by='source'):
    """罗列所有关键字信息（简化版，调用统一的工具函数）"""
    print("正在加载关键字...")

    # 使用统一的工具函数
    try:
        utils_list_keywords(
            output_format=output_format,
            name_filter=name_filter,
            category_filter=category_filter,
            category_name_filter=category_name_filter,
            tags_filter=tags_filter,
            include_remote=include_remote,
            output_file=output_file,
            print_summary=True,
            group_by=group_by
        )
    except Exception as e:
        print(f"列出关键字失败: {e}")
        raise


def load_yaml_variables(args):
    """从命令行参数加载YAML变量"""
    # 使用统一的加载函数，包含远程服务器自动连接功能和hook支持
    try:
        # 尝试从环境变量获取环境名称
        environment = (os.environ.get('PYTEST_DSL_ENVIRONMENT') or
                       os.environ.get('ENVIRONMENT'))

        # 智能判断是否应该加载默认配置
        # 如果用户指定了YAML文件或目录，则不自动加载默认配置
        user_specified_files = bool(args.yaml_vars)
        user_specified_dir = bool(args.yaml_vars_dir)
        auto_load_default = not (user_specified_files or user_specified_dir)

        load_yaml_variables_from_args(
            yaml_files=args.yaml_vars,
            yaml_vars_dir=args.yaml_vars_dir,
            project_root=os.getcwd(),  # CLI模式下使用当前工作目录作为项目根目录
            environment=environment,
            auto_load_default=auto_load_default  # 使用智能判断的结果
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
            if (file.endswith(('.dsl', '.auto')) and
                    file not in [SETUP_FILE_NAME, TEARDOWN_FILE_NAME]):
                dsl_files.append(os.path.join(root, file))
    return dsl_files


def run_dsl_tests(args):
    """执行DSL测试的主函数"""
    path = args.path

    if not path:
        print("错误: 必须指定要执行的DSL文件路径或目录")
        sys.exit(1)

    # 加载内置关键字插件（运行时总是包含远程关键字）
    load_all_keywords(include_remote=True)

    # 加载YAML变量（包括远程服务器自动连接）
    load_yaml_variables(args)

    # 支持hook机制的执行 - 使用DSLExecutor原生Hook支持
    # hookable_executor已被移除，DSLExecutor原生支持Hook机制

    # 创建支持Hook的DSL执行器
    executor = DSLExecutor(enable_hooks=True)

    # 检查是否有hook提供的用例列表
    hook_cases = []
    if executor.enable_hooks and executor.hook_manager:
        try:
            case_results = executor.hook_manager.pm.hook.dsl_list_cases()
            for result in case_results:
                if result:
                    hook_cases.extend(result)
        except Exception as e:
            print(f"获取Hook用例失败: {e}")

    if hook_cases:
        # 如果有hook提供的用例，优先执行这些用例
        print(f"通过Hook发现 {len(hook_cases)} 个DSL用例")
        failures = 0
        for case in hook_cases:
            case_id = case.get('id') or case.get('name', 'unknown')
            try:
                print(f"执行用例: {case.get('name', case_id)}")
                # 使用DSLExecutor执行，内容为空时会通过Hook加载
                executor.execute_from_content("", str(case_id))
                print(f"✓ 用例 {case.get('name', case_id)} 执行成功")
            except Exception as e:
                print(f"✗ 用例 {case.get('name', case_id)} 执行失败: {e}")
                failures += 1

        if failures > 0:
            print(f"总计 {failures}/{len(hook_cases)} 个测试失败")
            sys.exit(1)
        else:
            print(f"所有 {len(hook_cases)} 个测试成功完成")
        return

    # 如果没有hook用例，使用传统的文件执行方式
    lexer = get_lexer()
    parser = get_parser()
    # 复用之前创建的executor，如果没有则创建新的
    if 'executor' not in locals():
        executor = DSLExecutor(enable_hooks=True)

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


def main():
    """命令行入口点"""
    args = parse_args()

    # 处理子命令
    if args.command in ['list-keywords', 'list']:
        list_keywords(
            output_format=args.format,
            name_filter=args.filter,
            category_filter=args.category,
            output_file=args.output,
            include_remote=args.include_remote
        )
    elif args.command == 'run':
        run_dsl_tests(args)
    elif args.command == 'list-keywords-compat':
        # 向后兼容：旧的--list-keywords格式
        output_file = getattr(args, 'output', None)
        include_remote = getattr(args, 'include_remote', False)
        list_keywords(
            output_format=args.format,
            name_filter=args.filter,
            category_filter=args.category,
            output_file=output_file,
            include_remote=include_remote
        )
    elif args.command == 'run-compat':
        # 向后兼容：默认执行DSL测试
        run_dsl_tests(args)
    else:
        # 如果没有匹配的命令，显示帮助
        print("错误: 未知命令")
        sys.exit(1)


def main_list_keywords():
    """关键字列表命令的专用入口点"""
    parser = argparse.ArgumentParser(description='查看pytest-dsl可用关键字列表')
    parser.add_argument(
        '--format', choices=['text', 'json', 'html'],
        default='json',
        help='输出格式：json(默认)、text 或 html'
    )
    parser.add_argument(
        '--output', '-o', type=str, default=None,
        help='输出文件路径（json格式默认为keywords.json，html格式默认为keywords.html）'
    )
    parser.add_argument(
        '--filter', type=str, default=None,
        help='过滤关键字名称（支持部分匹配）'
    )
    parser.add_argument(
        '--category',
        choices=[
            'builtin', 'plugin', 'custom', 'project_custom', 'remote', 'all'
        ],
        default='all',
        help='关键字来源类别：builtin(内置)、plugin(插件)、custom(自定义)、'
             'project_custom(项目自定义)、remote(远程)、all(全部，默认)'
    )
    parser.add_argument(
        '--functional-category',
        choices=[
            'http', 'assertion', 'data', 'system', 'variable', 'utility', 
            'control', 'file', 'database', 'ui', 'performance', 'security', 'other', 'all'
        ],
        default='all',
        help='功能分类：http(HTTP请求)、assertion(断言验证)、data(数据操作)、'
             'system(系统操作)、variable(变量管理)、utility(实用工具)、'
             'control(控制流程)、file(文件操作)、database(数据库)、'
             'ui(UI操作)、performance(性能测试)、security(安全测试)、'
             'other(其他)、all(全部，默认)'
    )
    parser.add_argument(
        '--tags', nargs='*', default=None,
        help='按标签过滤关键字（可指定多个标签，关键字需包含所有指定标签）'
    )
    parser.add_argument(
        '--group-by',
        choices=['source', 'functional', 'tags', 'flat'],
        default='source',
        help='分组方式：source(按来源分组，默认)、functional(按功能分类分组)、'
             'tags(按标签分组)、flat(平铺显示)'
    )
    parser.add_argument(
        '--include-remote', action='store_true',
        help='是否包含远程关键字（默认不包含）'
    )

    args = parser.parse_args()

    list_keywords(
        output_format=args.format,
        name_filter=args.filter,
        category_filter=args.category,
        category_name_filter=args.functional_category,
        tags_filter=args.tags,
        output_file=args.output,
        include_remote=args.include_remote,
        group_by=args.group_by
    )


if __name__ == '__main__':
    main()
