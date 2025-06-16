"""
pytest-dsl关键字工具

提供统一的关键字列表查看、格式化和导出功能，供CLI和其他程序使用。
"""

import json
import os
from typing import Dict, Any, Optional, Union, List

from pytest_dsl.core.keyword_loader import (
    load_all_keywords, categorize_keyword, get_keyword_source_info,
    group_keywords_by_source
)
from pytest_dsl.core.keyword_manager import keyword_manager


class KeywordInfo:
    """关键字信息类"""

    def __init__(self, name: str, info: Dict[str, Any],
                 project_custom_keywords: Optional[Dict[str, Any]] = None):
        self.name = name
        self.info = info
        self.project_custom_keywords = project_custom_keywords
        self._category = None
        self._source_info = None

    @property
    def category(self) -> str:
        """获取关键字类别"""
        if self._category is None:
            self._category = categorize_keyword(
                self.name, self.info, self.project_custom_keywords
            )
        return self._category

    @property
    def source_info(self) -> Dict[str, Any]:
        """获取来源信息"""
        if self._source_info is None:
            self._source_info = get_keyword_source_info(self.info)
        return self._source_info

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        """获取参数信息"""
        if (self.category == 'project_custom' and
            self.project_custom_keywords and
                self.name in self.project_custom_keywords):
            return self.project_custom_keywords[self.name].get('parameters', [])

        # 对于其他类型的关键字
        parameters = self.info.get('parameters', [])
        param_list = []
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

            param_list.append(param_data)

        return param_list

    @property
    def documentation(self) -> str:
        """获取文档信息"""
        func = self.info.get('func')
        if func and hasattr(func, '__doc__') and func.__doc__:
            return func.__doc__.strip()
        return ""

    @property
    def file_location(self) -> Optional[str]:
        """获取文件位置（仅适用于项目自定义关键字）"""
        if (self.category == 'project_custom' and
            self.project_custom_keywords and
                self.name in self.project_custom_keywords):
            return self.project_custom_keywords[self.name]['file']
        return None

    @property
    def remote_info(self) -> Optional[Dict[str, str]]:
        """获取远程关键字信息"""
        if self.info.get('remote', False):
            return {
                'alias': self.info.get('alias', ''),
                'original_name': self.info.get('original_name', self.name)
            }
        return None


class KeywordListOptions:
    """关键字列表选项"""

    def __init__(self,
                 output_format: str = 'json',
                 name_filter: Optional[str] = None,
                 category_filter: str = 'all',
                 include_remote: bool = False,
                 output_file: Optional[str] = None):
        self.output_format = output_format
        self.name_filter = name_filter
        self.category_filter = category_filter
        self.include_remote = include_remote
        self.output_file = output_file

    def should_include_keyword(self, keyword_info: KeywordInfo) -> bool:
        """判断是否应该包含此关键字"""
        # 名称过滤
        if (self.name_filter and
                self.name_filter.lower() not in keyword_info.name.lower()):
            return False

        # 远程关键字过滤
        if (not self.include_remote and
                keyword_info.info.get('remote', False)):
            return False

        # 类别过滤
        if (self.category_filter != 'all' and
                keyword_info.category != self.category_filter):
            return False

        return True


class KeywordFormatter:
    """关键字格式化器"""

    def __init__(self):
        self.category_names = {
            'builtin': '内置',
            'plugin': '插件',
            'custom': '自定义',
            'project_custom': '项目自定义',
            'remote': '远程'
        }

    def format_text(self, keyword_info: KeywordInfo,
                    show_category: bool = True) -> str:
        """格式化为文本格式"""
        lines = []

        # 关键字名称和类别
        if show_category:
            category_display = self.category_names.get(
                keyword_info.category, '未知'
            )
            lines.append(f"关键字: {keyword_info.name} [{category_display}]")
        else:
            lines.append(f"关键字: {keyword_info.name}")

        # 远程关键字特殊信息
        if keyword_info.remote_info:
            remote = keyword_info.remote_info
            lines.append(f"  远程服务器: {remote['alias']}")
            lines.append(f"  原始名称: {remote['original_name']}")

        # 项目自定义关键字文件位置
        if keyword_info.file_location:
            lines.append(f"  文件位置: {keyword_info.file_location}")

        # 参数信息
        parameters = keyword_info.parameters
        if parameters:
            lines.append("  参数:")
            for param_info in parameters:
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

        # 函数文档
        if keyword_info.documentation:
            lines.append(f"  说明: {keyword_info.documentation}")

        return '\n'.join(lines)

    def format_json(self, keyword_info: KeywordInfo) -> Dict[str, Any]:
        """格式化为JSON格式"""
        keyword_data = {
            'name': keyword_info.name,
            'category': keyword_info.category,
            'source_info': keyword_info.source_info,
            'parameters': keyword_info.parameters
        }

        # 远程关键字特殊信息
        if keyword_info.remote_info:
            keyword_data['remote'] = keyword_info.remote_info

        # 项目自定义关键字文件位置
        if keyword_info.file_location:
            keyword_data['file_location'] = keyword_info.file_location

        # 函数文档
        if keyword_info.documentation:
            keyword_data['documentation'] = keyword_info.documentation

        return keyword_data


class KeywordLister:
    """关键字列表器"""

    def __init__(self):
        self.formatter = KeywordFormatter()
        self._project_custom_keywords = None

    def get_keywords(self, options: KeywordListOptions) -> List[KeywordInfo]:
        """获取关键字列表

        Args:
            options: 列表选项

        Returns:
            符合条件的关键字信息列表
        """
        # 加载关键字
        if self._project_custom_keywords is None:
            self._project_custom_keywords = load_all_keywords(
                include_remote=options.include_remote
            )

        # 获取所有注册的关键字
        all_keywords = keyword_manager._keywords

        if not all_keywords:
            return []

        # 过滤关键字
        filtered_keywords = []
        for name, info in all_keywords.items():
            keyword_info = KeywordInfo(
                name, info, self._project_custom_keywords
            )

            if options.should_include_keyword(keyword_info):
                filtered_keywords.append(keyword_info)

        return filtered_keywords

    def get_keywords_summary(self, keywords: List[KeywordInfo]) -> Dict[str, Any]:
        """获取关键字统计摘要

        Args:
            keywords: 关键字列表

        Returns:
            统计摘要信息
        """
        total_count = len(keywords)
        category_counts = {}
        source_counts = {}

        for keyword_info in keywords:
            # 类别统计
            cat = keyword_info.category
            category_counts[cat] = category_counts.get(cat, 0) + 1

            # 来源统计
            source_name = keyword_info.source_info['name']
            if keyword_info.file_location:
                source_name = keyword_info.file_location

            source_key = f"{cat}:{source_name}"
            source_counts[source_key] = source_counts.get(source_key, 0) + 1

        return {
            'total_count': total_count,
            'category_counts': category_counts,
            'source_counts': source_counts
        }

    def list_keywords_text(self, options: KeywordListOptions) -> str:
        """以文本格式列出关键字"""
        keywords = self.get_keywords(options)
        summary = self.get_keywords_summary(keywords)

        if not keywords:
            if options.name_filter:
                return f"未找到包含 '{options.name_filter}' 的关键字"
            else:
                return f"未找到 {options.category_filter} 类别的关键字"

        lines = []

        # 统计信息
        lines.append(f"找到 {summary['total_count']} 个关键字:")
        for cat, count in summary['category_counts'].items():
            cat_display = self.formatter.category_names.get(cat, cat)
            lines.append(f"  {cat_display}: {count} 个")
        lines.append("-" * 60)

        # 按类别和来源分组显示
        all_keywords_dict = {kw.name: kw.info for kw in keywords}
        grouped = group_keywords_by_source(
            all_keywords_dict, self._project_custom_keywords
        )

        for category in ['builtin', 'plugin', 'custom', 'project_custom', 'remote']:
            if category not in grouped or not grouped[category]:
                continue

            cat_names = {
                'builtin': '内置关键字',
                'plugin': '插件关键字',
                'custom': '自定义关键字',
                'project_custom': '项目自定义关键字',
                'remote': '远程关键字'
            }
            lines.append(f"\n=== {cat_names[category]} ===")

            for source_name, keyword_list in grouped[category].items():
                if len(grouped[category]) > 1:  # 如果有多个来源，显示来源名
                    lines.append(f"\n--- {source_name} ---")

                for keyword_data in keyword_list:
                    name = keyword_data['name']
                    keyword_info = next(
                        kw for kw in keywords if kw.name == name)
                    lines.append("")
                    lines.append(self.formatter.format_text(
                        keyword_info, show_category=False
                    ))

        return '\n'.join(lines)

    def list_keywords_json(self, options: KeywordListOptions) -> Dict[str, Any]:
        """以JSON格式列出关键字"""
        keywords = self.get_keywords(options)
        summary = self.get_keywords_summary(keywords)

        keywords_data = {
            'summary': summary,
            'keywords': []
        }

        # 按名称排序
        keywords.sort(key=lambda x: x.name)

        for keyword_info in keywords:
            keyword_data = self.formatter.format_json(keyword_info)
            keywords_data['keywords'].append(keyword_data)

        return keywords_data

    def list_keywords(self, options: KeywordListOptions) -> Union[str, Dict[str, Any]]:
        """列出关键字（根据格式返回不同类型）

        Args:
            options: 列表选项

        Returns:
            文本格式返回str，JSON格式返回dict，HTML格式返回dict
        """
        if options.output_format == 'text':
            return self.list_keywords_text(options)
        elif options.output_format in ['json', 'html']:
            return self.list_keywords_json(options)
        else:
            raise ValueError(f"不支持的输出格式: {options.output_format}")


def generate_html_report(keywords_data: Dict[str, Any], output_file: str):
    """生成HTML格式的关键字报告

    Args:
        keywords_data: 关键字数据（JSON格式）
        output_file: 输出文件路径
    """
    from jinja2 import Environment, FileSystemLoader, select_autoescape

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

    # 按来源分组
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

    # 类别名称映射
    category_names = {
        'builtin': '内置',
        'plugin': '插件',
        'custom': '自定义',
        'project_custom': '项目自定义',
        'remote': '远程'
    }

    # 设置Jinja2环境
    template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')

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
        category_names=category_names
    )

    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)


# 创建全局实例
keyword_lister = KeywordLister()


# 便捷函数
def list_keywords(output_format: str = 'json',
                  name_filter: Optional[str] = None,
                  category_filter: str = 'all',
                  include_remote: bool = False,
                  output_file: Optional[str] = None,
                  print_summary: bool = True) -> Union[str, Dict[str, Any], None]:
    """列出关键字的便捷函数

    Args:
        output_format: 输出格式 ('text', 'json', 'html')
        name_filter: 名称过滤器（支持部分匹配）
        category_filter: 类别过滤器
        include_remote: 是否包含远程关键字
        output_file: 输出文件路径（可选）
        print_summary: 是否打印摘要信息

    Returns:
        根据输出格式返回相应的数据，如果输出到文件则返回None
    """
    options = KeywordListOptions(
        output_format=output_format,
        name_filter=name_filter,
        category_filter=category_filter,
        include_remote=include_remote,
        output_file=output_file
    )

    # 获取数据
    result = keyword_lister.list_keywords(options)

    if isinstance(result, str):
        # 文本格式
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result)
            if print_summary:
                print(f"关键字信息已保存到文件: {output_file}")
            return None
        else:
            return result

    elif isinstance(result, dict):
        # JSON或HTML格式
        if output_format == 'json':
            json_output = json.dumps(result, ensure_ascii=False, indent=2)

            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(json_output)
                if print_summary:
                    _print_json_summary(result, output_file)
                return None
            else:
                return result

        elif output_format == 'html':
            if not output_file:
                output_file = 'keywords.html'

            try:
                generate_html_report(result, output_file)
                if print_summary:
                    _print_json_summary(result, output_file, is_html=True)
                return None
            except Exception as e:
                if print_summary:
                    print(f"生成HTML报告失败: {e}")
                raise

    return result


def _print_json_summary(keywords_data: Dict[str, Any],
                        output_file: str, is_html: bool = False):
    """打印JSON数据的摘要信息"""
    summary = keywords_data['summary']
    total_count = summary['total_count']
    category_counts = summary['category_counts']

    if is_html:
        print(f"HTML报告已生成: {output_file}")
    else:
        print(f"关键字信息已保存到文件: {output_file}")

    print(f"共 {total_count} 个关键字")

    category_names = {
        'builtin': '内置',
        'plugin': '插件',
        'custom': '自定义',
        'project_custom': '项目自定义',
        'remote': '远程'
    }

    for cat, count in category_counts.items():
        cat_display = category_names.get(cat, cat)
        print(f"  {cat_display}: {count} 个")


def get_keyword_info(keyword_name: str,
                     include_remote: bool = False) -> Optional[KeywordInfo]:
    """获取单个关键字的详细信息

    Args:
        keyword_name: 关键字名称
        include_remote: 是否包含远程关键字

    Returns:
        关键字信息对象，如果未找到则返回None
    """
    # 加载关键字
    project_custom_keywords = load_all_keywords(include_remote=include_remote)

    # 获取关键字信息
    keyword_info = keyword_manager.get_keyword_info(keyword_name)
    if not keyword_info:
        return None

    return KeywordInfo(keyword_name, keyword_info, project_custom_keywords)


def search_keywords(pattern: str,
                    include_remote: bool = False) -> List[KeywordInfo]:
    """搜索匹配模式的关键字

    Args:
        pattern: 搜索模式（支持部分匹配）
        include_remote: 是否包含远程关键字

    Returns:
        匹配的关键字信息列表
    """
    options = KeywordListOptions(
        name_filter=pattern,
        include_remote=include_remote
    )
    return keyword_lister.get_keywords(options)
