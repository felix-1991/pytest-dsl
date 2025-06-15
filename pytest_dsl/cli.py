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
from pytest_dsl.core.keyword_loader import (
    load_all_keywords, categorize_keyword, get_keyword_source_info,
    group_keywords_by_source, scan_project_custom_keywords
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
            '--format', choices=['text', 'json', 'html'],
            default='json',
            help='输出格式：json(默认)、text 或 html'
        )
        list_parser.add_argument(
            '--output', '-o', type=str, default=None,
            help='输出文件路径（json格式默认为keywords.json，html格式默认为keywords.html）'
        )
        list_parser.add_argument(
            '--filter', type=str, default=None,
            help='过滤关键字名称（支持部分匹配）'
        )
        list_parser.add_argument(
            '--category',
            choices=[
                'builtin', 'plugin', 'custom',
                'project_custom', 'remote', 'all'
            ],
            default='all',
            help='关键字类别：builtin(内置)、plugin(插件)、custom(自定义)、'
                 'project_custom(项目自定义)、remote(远程)、all(全部，默认)'
        )
        list_parser.add_argument(
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





def format_keyword_info_text(keyword_name, keyword_info, show_category=True,
                             project_custom_keywords=None):
    """格式化关键字信息为文本格式"""
    lines = []

    # 关键字名称和类别
    category = categorize_keyword(
        keyword_name, keyword_info, project_custom_keywords
    )
    category_names = {
        'builtin': '内置',
        'custom': '自定义',
        'project_custom': '项目自定义',
        'remote': '远程'
    }

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

    # 项目自定义关键字特殊标识
    if category == 'project_custom' and project_custom_keywords:
        custom_info = project_custom_keywords[keyword_name]
        lines.append(f"  文件位置: {custom_info['file']}")

        # 对于项目自定义关键字，使用从AST中提取的参数信息
        custom_parameters = custom_info.get('parameters', [])
        if custom_parameters:
            lines.append("  参数:")
            for param_info in custom_parameters:
                param_name = param_info['name']
                param_mapping = param_info.get('mapping', '')
                param_desc = param_info.get('description', '')
                param_default = param_info.get('default', None)

                # 构建参数描述
                param_parts = []
                if param_mapping and param_mapping != param_name:
                    param_parts.append(f"{param_name} ({param_mapping})")
                else:
                    param_parts.append(param_name)

                param_parts.append(f": {param_desc}")

                # 添加默认值信息
                if param_default is not None:
                    param_parts.append(f" (默认值: {param_default})")

                lines.append(f"    {''.join(param_parts)}")
        else:
            lines.append("  参数: 无")
    else:
        # 参数信息（对于其他类型的关键字）
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


def format_keyword_info_json(keyword_name, keyword_info,
                             project_custom_keywords=None):
    """格式化关键字信息为JSON格式"""
    category = categorize_keyword(
        keyword_name, keyword_info, project_custom_keywords
    )
    source_info = get_keyword_source_info(keyword_info)

    keyword_data = {
        'name': keyword_name,
        'category': category,
        'source_info': source_info,
        'parameters': []
    }

    # 远程关键字特殊信息
    if keyword_info.get('remote', False):
        keyword_data['remote'] = {
            'alias': keyword_info.get('alias', ''),
            'original_name': keyword_info.get('original_name', keyword_name)
        }

    # 项目自定义关键字特殊信息
    if category == 'project_custom' and project_custom_keywords:
        custom_info = project_custom_keywords[keyword_name]
        keyword_data['file_location'] = custom_info['file']

        # 对于项目自定义关键字，使用从AST中提取的参数信息
        for param_info in custom_info.get('parameters', []):
            keyword_data['parameters'].append(param_info)
    else:
        # 参数信息（对于其他类型的关键字）
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


def generate_html_report(keywords_data, output_file):
    """生成HTML格式的关键字报告"""
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    import os

    # 准备数据
    summary = keywords_data['summary']
    keywords = keywords_data['keywords']

    # 按类别分组
    categories = {}
    for keyword in keywords:
        category = keyword['category']
        if category not in categories:
            categories[category] = []
        categories[category].append(keyword)

    # 按来源分组（用于更详细的分组视图）
    source_groups = {}
    for keyword in keywords:
        source_info = keyword.get('source_info', {})
        category = keyword['category']
        source_name = source_info.get('name', '未知来源')

        # 构建分组键
        if category == 'plugin':
            group_key = f"插件 - {source_name}"
        elif category == 'builtin':
            group_key = "内置关键字"
        elif category == 'project_custom':
            group_key = f"项目自定义 - {keyword.get('file_location', source_name)}"
        elif category == 'remote':
            group_key = f"远程 - {source_name}"
        else:
            group_key = f"自定义 - {source_name}"

        if group_key not in source_groups:
            source_groups[group_key] = []
        source_groups[group_key].append(keyword)

    # 按位置分组（用于全部关键字视图，保持向后兼容）
    location_groups = {}
    for keyword in keywords:
        # 优先使用file_location，然后使用source_info中的name
        location = keyword.get('file_location')
        if not location:
            source_info = keyword.get('source_info', {})
            location = source_info.get('name', '内置/插件')

        if location not in location_groups:
            location_groups[location] = []
        location_groups[location].append(keyword)

    # 类别名称映射
    category_names = {
        'builtin': '内置',
        'plugin': '插件',
        'custom': '自定义',
        'project_custom': '项目自定义',
        'remote': '远程'
    }

    # 设置Jinja2环境
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')

    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )

    # 加载模板
    template = env.get_template('keywords_report.html')

    # 渲染模板
    html_content = template.render(
        summary=summary,
        keywords=keywords,
        categories=categories,
        source_groups=source_groups,
        location_groups=location_groups,
        category_names=category_names
    )

    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"HTML报告已生成: {output_file}")


def list_keywords(output_format='json', name_filter=None,
                  category_filter='all', output_file=None,
                  include_remote=False):
    """罗列所有关键字信息"""
    import json

    print("正在加载关键字...")
    project_custom_keywords = load_all_keywords(include_remote=include_remote)

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

        # 远程关键字过滤
        if not include_remote and info.get('remote', False):
            continue

        # 类别过滤
        if category_filter != 'all':
            keyword_category = categorize_keyword(
                name, info, project_custom_keywords
            )
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
    source_counts = {}

    for name, info in filtered_keywords.items():
        cat = categorize_keyword(name, info, project_custom_keywords)
        category_counts[cat] = category_counts.get(cat, 0) + 1

        # 统计各来源的关键字数量
        source_info = get_keyword_source_info(info)
        source_name = source_info['name']
        if cat == 'project_custom' and project_custom_keywords:
            custom_info = project_custom_keywords[name]
            source_name = custom_info['file']

        source_key = f"{cat}:{source_name}"
        source_counts[source_key] = source_counts.get(source_key, 0) + 1

    if output_format == 'text':
        print(f"\n找到 {total_count} 个关键字:")
        for cat, count in category_counts.items():
            cat_names = {
                'builtin': '内置', 'plugin': '插件', 'custom': '自定义',
                'project_custom': '项目自定义', 'remote': '远程'
            }
            print(f"  {cat_names.get(cat, cat)}: {count} 个")
        print("-" * 60)

        # 按类别和来源分组显示
        grouped = group_keywords_by_source(
            filtered_keywords, project_custom_keywords
        )

        for category in [
            'builtin', 'plugin', 'custom', 'project_custom', 'remote'
        ]:
            if category not in grouped or not grouped[category]:
                continue

            cat_names = {
                'builtin': '内置关键字',
                'plugin': '插件关键字',
                'custom': '自定义关键字',
                'project_custom': '项目自定义关键字',
                'remote': '远程关键字'
            }
            print(f"\n=== {cat_names[category]} ===")

            for source_name, keyword_list in grouped[category].items():
                if len(grouped[category]) > 1:  # 如果有多个来源，显示来源名
                    print(f"\n--- {source_name} ---")

                for keyword_data in keyword_list:
                    name = keyword_data['name']
                    info = keyword_data['info']
                    print()
                    print(format_keyword_info_text(
                        name, info, show_category=False,
                        project_custom_keywords=project_custom_keywords
                    ))

    elif output_format == 'json':
        keywords_data = {
            'summary': {
                'total_count': total_count,
                'category_counts': category_counts,
                'source_counts': source_counts
            },
            'keywords': []
        }

        for name in sorted(filtered_keywords.keys()):
            info = filtered_keywords[name]
            keyword_data = format_keyword_info_json(
                name, info, project_custom_keywords
            )
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
                cat_names = {
                    'builtin': '内置', 'plugin': '插件', 'custom': '自定义',
                    'project_custom': '项目自定义', 'remote': '远程'
                }
                print(f"  {cat_names.get(cat, cat)}: {count} 个")
        except Exception as e:
            print(f"保存文件失败: {e}")
            # 如果写入文件失败，则回退到打印
            print(json_output)

    elif output_format == 'html':
        keywords_data = {
            'summary': {
                'total_count': total_count,
                'category_counts': category_counts,
                'source_counts': source_counts
            },
            'keywords': []
        }

        for name in sorted(filtered_keywords.keys()):
            info = filtered_keywords[name]
            keyword_data = format_keyword_info_json(
                name, info, project_custom_keywords
            )
            keywords_data['keywords'].append(keyword_data)

        # 确定输出文件名
        if output_file is None:
            output_file = 'keywords.html'

        # 生成HTML报告
        try:
            generate_html_report(keywords_data, output_file)
            print(f"共 {total_count} 个关键字")
            for cat, count in category_counts.items():
                cat_names = {
                    'builtin': '内置', 'plugin': '插件', 'custom': '自定义',
                    'project_custom': '项目自定义', 'remote': '远程'
                }
                print(f"  {cat_names.get(cat, cat)}: {count} 个")
        except Exception as e:
            print(f"生成HTML报告失败: {e}")
            raise


def load_yaml_variables(args):
    """从命令行参数加载YAML变量"""
    # 使用统一的加载函数，包含远程服务器自动连接功能和hook支持
    try:
        # 尝试从环境变量获取环境名称
        environment = (os.environ.get('PYTEST_DSL_ENVIRONMENT') or
                       os.environ.get('ENVIRONMENT'))

        load_yaml_variables_from_args(
            yaml_files=args.yaml_vars,
            yaml_vars_dir=args.yaml_vars_dir,
            project_root=os.getcwd(),  # CLI模式下使用当前工作目录作为项目根目录
            environment=environment
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

    # 支持hook机制的执行
    from pytest_dsl.core.hookable_executor import hookable_executor

    # 检查是否有hook提供的用例列表
    hook_cases = hookable_executor.list_dsl_cases()
    if hook_cases:
        # 如果有hook提供的用例，优先执行这些用例
        print(f"通过Hook发现 {len(hook_cases)} 个DSL用例")
        failures = 0
        for case in hook_cases:
            case_id = case.get('id') or case.get('name', 'unknown')
            try:
                print(f"执行用例: {case.get('name', case_id)}")
                hookable_executor.execute_dsl(str(case_id))
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
        help='关键字类别：builtin(内置)、plugin(插件)、custom(自定义)、'
             'project_custom(项目自定义)、remote(远程)、all(全部，默认)'
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
        output_file=args.output,
        include_remote=args.include_remote
    )





if __name__ == '__main__':
    main()
