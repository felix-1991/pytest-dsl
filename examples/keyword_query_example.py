#!/usr/bin/env python3
"""
pytest-dsl关键字查询示例

演示如何在其他程序中使用pytest-dsl的关键字查询功能。
"""

import sys
import os
# 添加上级目录到路径，以便导入pytest_dsl
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest_dsl


def example_list_all_keywords():
    """示例：列出所有关键字"""
    print("=== 列出所有关键字（JSON格式）===")
    
    # 获取JSON格式的关键字数据
    keywords_data = pytest_dsl.list_keywords(
        output_format='json',
        print_summary=False  # 不打印摘要信息
    )
    
    if keywords_data:
        summary = keywords_data['summary']
        print(f"总数: {summary['total_count']} 个关键字")
        print("分类统计:")
        for category, count in summary['category_counts'].items():
            print(f"  {category}: {count} 个")
        
        # 显示前3个关键字作为示例
        print("\n前3个关键字:")
        for keyword in keywords_data['keywords'][:3]:
            print(f"  - {keyword['name']} ({keyword['category']})")


def example_search_keywords():
    """示例：搜索特定关键字"""
    print("\n=== 搜索包含 'HTTP' 的关键字 ===")
    
    # 搜索包含HTTP的关键字
    keywords = pytest_dsl.search_keywords('HTTP')
    
    print(f"找到 {len(keywords)} 个匹配的关键字:")
    for keyword_info in keywords:
        print(f"  - {keyword_info.name}")
        print(f"    类别: {keyword_info.category}")
        print(f"    参数数量: {len(keyword_info.parameters)}")
        if keyword_info.documentation:
            doc = keyword_info.documentation.split('\n')[0]  # 只显示第一行
            print(f"    说明: {doc}")
        print()


def example_get_single_keyword():
    """示例：获取单个关键字的详细信息"""
    print("=== 获取单个关键字详细信息 ===")
    
    # 获取特定关键字的信息
    keyword_info = pytest_dsl.get_keyword_info('HTTP请求')
    
    if keyword_info:
        print(f"关键字名称: {keyword_info.name}")
        print(f"类别: {keyword_info.category}")
        print(f"来源: {keyword_info.source_info['name']}")
        
        print("参数列表:")
        for param in keyword_info.parameters:
            print(f"  - {param['name']}: {param['description']}")
            if 'default' in param:
                print(f"    默认值: {param['default']}")
        
        if keyword_info.documentation:
            print(f"文档: {keyword_info.documentation}")
    else:
        print("未找到指定的关键字")


def example_filter_by_category():
    """示例：按类别筛选关键字"""
    print("\n=== 按类别筛选关键字 ===")
    
    # 只获取内置关键字
    builtin_keywords_data = pytest_dsl.list_keywords(
        output_format='json',
        category_filter='builtin',
        print_summary=False
    )
    
    if builtin_keywords_data:
        print(f"内置关键字数量: {builtin_keywords_data['summary']['total_count']}")
        
        # 按功能分组显示
        functionality_groups = {}
        for keyword in builtin_keywords_data['keywords']:
            # 根据关键字名称简单分组（实际应用中可以更复杂）
            if 'HTTP' in keyword['name'] or '请求' in keyword['name']:
                group = 'HTTP相关'
            elif '断言' in keyword['name'] or '检查' in keyword['name']:
                group = '断言相关'
            elif '数据' in keyword['name'] or '操作' in keyword['name']:
                group = '数据操作'
            else:
                group = '其他'
            
            if group not in functionality_groups:
                functionality_groups[group] = []
            functionality_groups[group].append(keyword['name'])
        
        for group, keywords in functionality_groups.items():
            print(f"\n{group}:")
            for kw_name in keywords:
                print(f"  - {kw_name}")


def example_programmatic_usage():
    """示例：程序化使用关键字信息"""
    print("\n=== 程序化使用示例 ===")
    
    # 获取所有关键字信息用于自动化处理
    keywords_data = pytest_dsl.list_keywords(
        output_format='json',
        print_summary=False
    )
    
    if not keywords_data:
        print("未找到任何关键字")
        return
    
    # 统计分析
    param_counts = {}
    total_params = 0
    
    for keyword in keywords_data['keywords']:
        param_count = len(keyword['parameters'])
        total_params += param_count
        
        if param_count not in param_counts:
            param_counts[param_count] = 0
        param_counts[param_count] += 1
    
    print("关键字参数统计:")
    for param_count in sorted(param_counts.keys()):
        keyword_count = param_counts[param_count]
        print(f"  {param_count} 个参数: {keyword_count} 个关键字")
    
    avg_params = total_params / len(keywords_data['keywords'])
    print(f"\n平均每个关键字有 {avg_params:.1f} 个参数")
    
    # 找出参数最多的关键字
    max_params_keyword = max(
        keywords_data['keywords'], 
        key=lambda x: len(x['parameters'])
    )
    print(f"参数最多的关键字: {max_params_keyword['name']} "
          f"({len(max_params_keyword['parameters'])} 个参数)")


def example_export_for_documentation():
    """示例：导出用于文档生成"""
    print("\n=== 导出文档示例 ===")
    
    # 生成markdown格式的关键字文档
    keywords_data = pytest_dsl.list_keywords(
        output_format='json',
        print_summary=False
    )
    
    if not keywords_data:
        return
    
    # 按类别分组生成markdown
    markdown_content = ["# pytest-dsl 关键字参考\n"]
    
    categories = {}
    for keyword in keywords_data['keywords']:
        category = keyword['category']
        if category not in categories:
            categories[category] = []
        categories[category].append(keyword)
    
    category_names = {
        'builtin': '内置关键字',
        'plugin': '插件关键字', 
        'custom': '自定义关键字',
        'project_custom': '项目自定义关键字',
        'remote': '远程关键字'
    }
    
    for category, keywords in categories.items():
        category_name = category_names.get(category, category)
        markdown_content.append(f"\n## {category_name}\n")
        
        for keyword in sorted(keywords, key=lambda x: x['name']):
            markdown_content.append(f"### {keyword['name']}\n")
            
            if keyword.get('documentation'):
                markdown_content.append(f"{keyword['documentation']}\n")
            
            if keyword['parameters']:
                markdown_content.append("**参数:**\n")
                for param in keyword['parameters']:
                    param_desc = f"- `{param['name']}`: {param['description']}"
                    if param.get('default') is not None:
                        param_desc += f" (默认: `{param['default']}`)"
                    markdown_content.append(param_desc + "\n")
            else:
                markdown_content.append("**参数:** 无\n")
            
            markdown_content.append("\n---\n")
    
    # 保存到文件（示例中只打印前几行）
    full_markdown = ''.join(markdown_content)
    lines = full_markdown.split('\n')
    
    print("生成的markdown文档预览（前20行）:")
    for line in lines[:20]:
        print(line)
    
    print(f"\n... (总共 {len(lines)} 行)")
    print("可以保存到文件用于生成项目文档")


if __name__ == '__main__':
    print("pytest-dsl 关键字查询功能演示\n")
    
    # 运行各种示例
    example_list_all_keywords()
    example_search_keywords()
    example_get_single_keyword()
    example_filter_by_category()
    example_programmatic_usage()
    example_export_for_documentation()
    
    print("\n=== 演示完成 ===")
    print("您可以在自己的程序中使用这些功能来查询和使用pytest-dsl的关键字信息。") 