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
from pytest_dsl.core.plugin_discovery import (
    load_all_plugins, scan_local_keywords
)
from pytest_dsl.core.keyword_manager import keyword_manager


def read_file(filename):
    """读取 DSL 文件内容"""
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()


def parse_args():
    """解析命令行参数"""
    import sys
    argv = sys.argv[1:]  # 去掉脚本名

    # 检查是否使用了子命令格式
    if argv and argv[0] in ['run', 'list-keywords']:
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
        list_parser.add_argument(
            '--format', choices=['text', 'json'],
            default='json',
            help='输出格式：json(默认) 或 text'
        )
        list_parser.add_argument(
            '--output', '-o', type=str, default=None,
            help='输出文件路径（仅对 json 格式有效，默认为 keywords.json）'
        )
        list_parser.add_argument(
            '--filter', type=str, default=None,
            help='过滤关键字名称（支持部分匹配）'
        )
        list_parser.add_argument(
            '--category',
            choices=['builtin', 'custom', 'remote', 'all'],
            default='all',
            help='关键字类别：builtin(内置)、custom(自定义)、'
                 'remote(远程)、all(全部，默认)'
        )

        return parser.parse_args(argv)
    else:
        # 向后兼容模式
        parser = argparse.ArgumentParser(description='执行DSL测试文件')

        # 检查是否是list-keywords的旧格式
        if '--list-keywords' in argv:
            parser.add_argument('--list-keywords', action='store_true')
            parser.add_argument(
                '--format', choices=['text', 'json'], default='json'
            )
            parser.add_argument(
                '--output', '-o', type=str, default=None
            )
            parser.add_argument('--filter', type=str, default=None)
            parser.add_argument(
                '--category',
                choices=['builtin', 'custom', 'remote', 'all'],
                default='all'
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


def load_all_keywords():
    """加载所有可用的关键字"""
    # 首先导入内置关键字模块，确保内置关键字被注册
    try:
        import pytest_dsl.keywords  # noqa: F401
        print("内置关键字模块加载完成")
    except ImportError as e:
        print(f"加载内置关键字模块失败: {e}")

    # 加载已安装的关键字插件
    load_all_plugins()

    # 扫描本地关键字
    scan_local_keywords()


def categorize_keyword(keyword_name, keyword_info):
    """判断关键字的类别"""
    if keyword_info.get('remote', False):
        return 'remote'

    # 检查是否是内置关键字（通过检查函数所在模块）
    func = keyword_info.get('func')
    if func and hasattr(func, '__module__'):
        module_name = func.__module__
        if module_name and module_name.startswith('pytest_dsl.keywords'):
            return 'builtin'

    return 'custom'


def format_keyword_info_text(keyword_name, keyword_info, show_category=True):
    """格式化关键字信息为文本格式"""
    lines = []

    # 关键字名称和类别
    category = categorize_keyword(keyword_name, keyword_info)
    category_names = {'builtin': '内置', 'custom': '自定义', 'remote': '远程'}

    if show_category:
        category_display = category_names.get(category, '未知')
        lines.append(f"关键字: {keyword_name} [{category_display}]")
    else:
        lines.append(f"关键字: {keyword_name}")

    # 远程关键字特殊标识
    if keyword_info.get('remote', False):
        alias = keyword_info.get('alias', '未知')
        original_name = keyword_info.get('original_name', keyword_name)
        lines.append(f"  远程服务器: {alias}")
        lines.append(f"  原始名称: {original_name}")

    # 参数信息
    parameters = keyword_info.get('parameters', [])
    if parameters:
        lines.append("  参数:")
        for param in parameters:
            param_name = getattr(param, 'name', str(param))
            param_mapping = getattr(param, 'mapping', '')
            param_desc = getattr(param, 'description', '')
            param_default = getattr(param, 'default', None)

            # 构建参数描述
            param_info = []
            if param_mapping and param_mapping != param_name:
                param_info.append(f"{param_name} ({param_mapping})")
            else:
                param_info.append(param_name)
            
            param_info.append(f": {param_desc}")
            
            # 添加默认值信息
            if param_default is not None:
                param_info.append(f" (默认值: {param_default})")
            
            lines.append(f"    {''.join(param_info)}")
    else:
        lines.append("  参数: 无")

    # 函数文档
    func = keyword_info.get('func')
    if func and hasattr(func, '__doc__') and func.__doc__:
        lines.append(f"  说明: {func.__doc__.strip()}")

    return '\n'.join(lines)


def format_keyword_info_json(keyword_name, keyword_info):
    """格式化关键字信息为JSON格式"""
    category = categorize_keyword(keyword_name, keyword_info)

    keyword_data = {
        'name': keyword_name,
        'category': category,
        'parameters': []
    }

    # 远程关键字特殊信息
    if keyword_info.get('remote', False):
        keyword_data['remote'] = {
            'alias': keyword_info.get('alias', ''),
            'original_name': keyword_info.get('original_name', keyword_name)
        }

    # 参数信息
    parameters = keyword_info.get('parameters', [])
    for param in parameters:
        param_data = {
            'name': getattr(param, 'name', str(param)),
            'mapping': getattr(param, 'mapping', ''),
            'description': getattr(param, 'description', '')
        }
        
        # 添加默认值信息
        param_default = getattr(param, 'default', None)
        if param_default is not None:
            param_data['default'] = param_default
        
        keyword_data['parameters'].append(param_data)

    # 函数文档
    func = keyword_info.get('func')
    if func and hasattr(func, '__doc__') and func.__doc__:
        keyword_data['documentation'] = func.__doc__.strip()

    return keyword_data


def list_keywords(output_format='json', name_filter=None,
                  category_filter='all', output_file=None):
    """罗列所有关键字信息"""
    import json

    print("正在加载关键字...")
    load_all_keywords()

    # 获取所有注册的关键字
    all_keywords = keyword_manager._keywords

    if not all_keywords:
        print("未发现任何关键字")
        return

    # 过滤关键字
    filtered_keywords = {}

    for name, info in all_keywords.items():
        # 名称过滤
        if name_filter and name_filter.lower() not in name.lower():
            continue

        # 类别过滤
        if category_filter != 'all':
            keyword_category = categorize_keyword(name, info)
            if keyword_category != category_filter:
                continue

        filtered_keywords[name] = info

    if not filtered_keywords:
        if name_filter:
            print(f"未找到包含 '{name_filter}' 的关键字")
        else:
            print(f"未找到 {category_filter} 类别的关键字")
        return

    # 输出统计信息
    total_count = len(filtered_keywords)
    category_counts = {}
    for name, info in filtered_keywords.items():
        cat = categorize_keyword(name, info)
        category_counts[cat] = category_counts.get(cat, 0) + 1

    if output_format == 'text':
        print(f"\n找到 {total_count} 个关键字:")
        for cat, count in category_counts.items():
            cat_names = {'builtin': '内置', 'custom': '自定义', 'remote': '远程'}
            print(f"  {cat_names.get(cat, cat)}: {count} 个")
        print("-" * 60)

        # 按类别分组显示
        for category in ['builtin', 'custom', 'remote']:
            cat_keywords = {
                name: info for name, info in filtered_keywords.items()
                if categorize_keyword(name, info) == category
            }

            if cat_keywords:
                cat_names = {
                    'builtin': '内置关键字',
                    'custom': '自定义关键字',
                    'remote': '远程关键字'
                }
                print(f"\n=== {cat_names[category]} ===")

                for name in sorted(cat_keywords.keys()):
                    info = cat_keywords[name]
                    print()
                    print(format_keyword_info_text(
                        name, info, show_category=False
                    ))

    elif output_format == 'json':
        keywords_data = {
            'summary': {
                'total_count': total_count,
                'category_counts': category_counts
            },
            'keywords': []
        }

        for name in sorted(filtered_keywords.keys()):
            info = filtered_keywords[name]
            keyword_data = format_keyword_info_json(name, info)
            keywords_data['keywords'].append(keyword_data)

        json_output = json.dumps(keywords_data, ensure_ascii=False, indent=2)
        
        # 确定输出文件名
        if output_file is None:
            output_file = 'keywords.json'
        
        # 写入到文件
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"关键字信息已保存到文件: {output_file}")
            print(f"共 {total_count} 个关键字")
            for cat, count in category_counts.items():
                cat_names = {'builtin': '内置', 'custom': '自定义', 'remote': '远程'}
                print(f"  {cat_names.get(cat, cat)}: {count} 个")
        except Exception as e:
            print(f"保存文件失败: {e}")
            # 如果写入文件失败，则回退到打印
            print(json_output)


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

    # 加载内置关键字插件
    load_all_keywords()

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


def main():
    """命令行入口点"""
    args = parse_args()

    # 处理子命令
    if args.command == 'list-keywords':
        list_keywords(
            output_format=args.format,
            name_filter=args.filter,
            category_filter=args.category,
            output_file=args.output
        )
    elif args.command == 'run':
        run_dsl_tests(args)
    elif args.command == 'list-keywords-compat':
        # 向后兼容：旧的--list-keywords格式
        output_file = getattr(args, 'output', None)
        list_keywords(
            output_format=args.format,
            name_filter=args.filter,
            category_filter=args.category,
            output_file=output_file
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
        '--format', choices=['text', 'json'],
        default='json',
        help='输出格式：json(默认) 或 text'
    )
    parser.add_argument(
        '--output', '-o', type=str, default=None,
        help='输出文件路径（仅对 json 格式有效，默认为 keywords.json）'
    )
    parser.add_argument(
        '--filter', type=str, default=None,
        help='过滤关键字名称（支持部分匹配）'
    )
    parser.add_argument(
        '--category',
        choices=['builtin', 'custom', 'remote', 'all'],
        default='all',
        help='关键字类别：builtin(内置)、custom(自定义)、remote(远程)、all(全部，默认)'
    )

    args = parser.parse_args()

    list_keywords(
        output_format=args.format,
        name_filter=args.filter,
        category_filter=args.category,
        output_file=args.output
    )


if __name__ == '__main__':
    main()
