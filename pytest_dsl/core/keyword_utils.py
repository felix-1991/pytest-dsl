"""
pytest-dsl关键字工具

提供统一的关键字列表查看、格式化和导出功能，供CLI和其他程序使用。
"""

import json
import os
from typing import Dict, Any, Optional, Union, List

from pytest_dsl.core.keyword_loader import (
    load_all_keywords, categorize_keyword, get_keyword_source_info,
    group_keywords_by_source, keyword_loader
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
        self._functional_category = None
        self._tags = None

    @property
    def category(self) -> str:
        """获取关键字来源类别"""
        if self._category is None:
            self._category = categorize_keyword(
                self.name, self.info, self.project_custom_keywords
            )
        return self._category

    @property
    def category_name(self) -> str:
        """获取关键字功能分类"""
        if self._functional_category is None:
            self._functional_category = self.info.get('category', '其他')
        return self._functional_category

    @property
    def tags(self) -> set:
        """获取关键字标签"""
        if self._tags is None:
            self._tags = self.info.get('tags', set())
        return self._tags

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
                 category_name_filter: str = 'all',
                 tags_filter: Optional[List[str]] = None,
                 include_remote: bool = False,
                 output_file: Optional[str] = None,
                 group_by: str = 'source'):
        self.output_format = output_format
        self.name_filter = name_filter
        self.category_filter = category_filter
        self.category_name_filter = category_name_filter
        self.tags_filter = tags_filter or []
        self.include_remote = include_remote
        self.output_file = output_file
        self.group_by = group_by  # 'source', 'category', 'tags', 'flat'

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

        # 来源类别过滤
        if (self.category_filter != 'all' and
                keyword_info.category != self.category_filter):
            return False

        # 功能分类过滤
        if (self.category_name_filter != 'all' and
                keyword_info.category_name != self.category_name_filter):
            return False

        # 标签过滤
        if self.tags_filter:
            keyword_tags = keyword_info.tags
            tags_filter_set = set(tag.lower() for tag in self.tags_filter)
            keyword_tags_lower = set(tag.lower() for tag in keyword_tags)
            
            # 要求包含所有指定的标签
            if not tags_filter_set.issubset(keyword_tags_lower):
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

        # 获取功能分类名称
        self.category_display_names = {}
        categories = keyword_manager.get_categories()
        for key, info in categories.items():
            self.category_display_names[key] = info['name']

    def format_text(self, keyword_info: KeywordInfo,
                    show_category: bool = True, show_category_name: bool = True,
                    show_tags: bool = True) -> str:
        """格式化为文本格式"""
        lines = []

        # 关键字名称和类别
        title_parts = [f"关键字: {keyword_info.name}"]
        
        if show_category:
            category_display = self.category_names.get(
                keyword_info.category, '未知'
            )
            title_parts.append(f"[{category_display}]")
        
        if show_category_name:
            category_display = self.category_display_names.get(
                keyword_info.category_name, keyword_info.category_name
            )
            title_parts.append(f"({category_display})")
        
        lines.append(" ".join(title_parts))

        # 标签信息
        if show_tags and keyword_info.tags:
            tags_display = ", ".join(sorted(keyword_info.tags))
            lines.append(f"  标签: {tags_display}")

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
            for param in parameters:
                param_desc = f"    - {param['name']}"
                if param.get('default') is not None:
                    param_desc += f" (默认: {param['default']})"
                param_desc += f": {param['description']}"
                lines.append(param_desc)

        # 文档字符串
        if keyword_info.documentation:
            doc_lines = keyword_info.documentation.split('\n')
            if doc_lines:
                lines.append(f"  说明: {doc_lines[0]}")

        # 来源信息
        source_info = keyword_info.source_info
        if source_info.get('module'):
            lines.append(f"  来源: {source_info['name']} ({source_info['module']})")
        else:
            lines.append(f"  来源: {source_info['name']}")

        return '\n'.join(lines)

    def format_json(self, keyword_info: KeywordInfo) -> Dict[str, Any]:
        """格式化为JSON格式"""
        keyword_data = {
            'name': keyword_info.name,
            'category': keyword_info.category,
            'category_name': keyword_info.category_name,
            'tags': list(keyword_info.tags),
            'source_info': keyword_info.source_info,
            'parameters': keyword_info.parameters
        }

        # 添加来源字段，优先显示项目自定义关键字的文件位置
        if keyword_info.file_location:
            keyword_data['source'] = keyword_info.file_location
        else:
            keyword_data['source'] = keyword_info.source_info.get(
                'display_name', keyword_info.source_info.get('name', '未知'))

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
        # 使用新的统计功能
        keywords_dict = {kw.name: kw.info for kw in keywords}
        stats = keyword_loader.get_keyword_statistics(
            keywords_dict, self._project_custom_keywords
        )

        # 添加传统格式以保持兼容性
        legacy_stats = {
            'total_count': stats['total_count'],
            'category_counts': stats['source_counts'],  # 保持原有的命名
            'source_counts': {}
        }

        # 生成传统的source_counts格式
        for keyword in keywords:
            source_name = keyword.source_info['name']
            if keyword.file_location:
                source_name = keyword.file_location

            source_key = f"{keyword.category}:{source_name}"
            legacy_stats['source_counts'][source_key] = legacy_stats['source_counts'].get(source_key, 0) + 1

        # 添加新的统计信息
        legacy_stats.update({
            'category_name_counts': stats['category_name_counts'],
            'tag_counts': stats['tag_counts'],
            'combined_stats': stats['combined_stats']
        })

        return legacy_stats

    def list_keywords_text(self, options: KeywordListOptions) -> str:
        """以文本格式列出关键字"""
        keywords = self.get_keywords(options)
        summary = self.get_keywords_summary(keywords)

        if not keywords:
            if options.name_filter:
                return f"未找到包含 '{options.name_filter}' 的关键字"
            else:
                filters = []
                if options.category_filter != 'all':
                    filters.append(f"来源类别:{options.category_filter}")
                if options.category_name_filter != 'all':
                    filters.append(f"功能分类:{options.category_name_filter}")
                if options.tags_filter:
                    filters.append(f"标签:{','.join(options.tags_filter)}")
                
                filter_text = "、".join(filters) if filters else "all"
                return f"未找到符合条件的关键字 ({filter_text})"

        lines = []

        # 统计信息
        lines.append(f"找到 {summary['total_count']} 个关键字:")
        
        # 按来源统计
        lines.append("按来源分类:")
        for cat, count in summary['category_counts'].items():
            cat_display = self.formatter.category_names.get(cat, cat)
            lines.append(f"  {cat_display}: {count} 个")
        
        # 按功能分类统计
        if summary.get('category_name_counts'):
            lines.append("按功能分类:")
            for cat, count in summary['category_name_counts'].items():
                cat_display = self.formatter.category_display_names.get(cat, cat)
                lines.append(f"  {cat_display}: {count} 个")
        
        lines.append("-" * 60)

        # 根据group_by选项分组显示
        if options.group_by == 'category':
            self._add_category_groups(lines, keywords)
        elif options.group_by == 'tags':
            self._add_tag_groups(lines, keywords)
        elif options.group_by == 'flat':
            self._add_flat_list(lines, keywords)
        else:  # 默认按来源分组
            self._add_source_groups(lines, keywords)

        return '\n'.join(lines)

    def _add_source_groups(self, lines: List[str], keywords: List[KeywordInfo]):
        """添加按来源分组的关键字列表"""
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

    def _add_category_groups(self, lines: List[str], keywords: List[KeywordInfo]):
        """添加按功能分类分组的关键字列表（支持多级分类）"""
        # 使用keyword_manager的层次化分类方法
        all_keywords_dict = {kw.name: kw for kw in keywords}
        hierarchical_groups = {}
        
        # 按多级分类分组
        for keyword_info in keywords:
            category = keyword_info.category_name
            if '/' in category:
                level1, level2 = category.split('/', 1)
            else:
                level1, level2 = category, '基础'
            
            if level1 not in hierarchical_groups:
                hierarchical_groups[level1] = {}
            if level2 not in hierarchical_groups[level1]:
                hierarchical_groups[level1][level2] = []
            
            hierarchical_groups[level1][level2].append(keyword_info)

        # 按预定义的顺序显示一级分类
        level1_order = ['HTTP', 'UI', '数据', '系统', '其他']
        
        for level1 in level1_order:
            if level1 not in hierarchical_groups or not hierarchical_groups[level1]:
                continue

            # 显示一级分类标题
            lines.append(f"\n=== {level1} ===")
            
            # 按二级分类排序并显示
            level2_categories = hierarchical_groups[level1]
            for level2 in sorted(level2_categories.keys()):
                if not level2_categories[level2]:
                    continue
                
                # 如果只有一个二级分类且名为"基础"，不显示二级标题
                if len(level2_categories) == 1 and level2 == '基础':
                    # 直接显示关键字
                    for keyword_info in level2_categories[level2]:
                        lines.append("")
                        lines.append(self.formatter.format_text(
                            keyword_info, show_category=True, show_category_name=False
                        ))
                else:
                    # 显示二级分类标题
                    lines.append(f"\n  -- {level2} --")
                    for keyword_info in level2_categories[level2]:
                        lines.append("")
                        lines.append(self.formatter.format_text(
                            keyword_info, show_category=True, show_category_name=False
                        ))

        # 处理其他未在预定义顺序中的一级分类
        for level1 in hierarchical_groups:
            if level1 not in level1_order:
                lines.append(f"\n=== {level1} ===")
                level2_categories = hierarchical_groups[level1]
                for level2 in sorted(level2_categories.keys()):
                    if not level2_categories[level2]:
                        continue
                    
                    if len(level2_categories) == 1 and level2 == '基础':
                        for keyword_info in level2_categories[level2]:
                            lines.append("")
                            lines.append(self.formatter.format_text(
                                keyword_info, show_category=True, show_category_name=False
                            ))
                    else:
                        lines.append(f"\n  -- {level2} --")
                        for keyword_info in level2_categories[level2]:
                            lines.append("")
                            lines.append(self.formatter.format_text(
                                keyword_info, show_category=True, show_category_name=False
                            ))

    def _add_tag_groups(self, lines: List[str], keywords: List[KeywordInfo]):
        """添加按标签分组的关键字列表"""
        all_keywords_dict = {kw.name: kw.info for kw in keywords}
        grouped = keyword_loader.group_keywords_by_tags(all_keywords_dict)

        # 按标签名称排序
        for tag in sorted(grouped.keys()):
            lines.append(f"\n=== 标签: {tag} ===")

            for keyword_data in grouped[tag]:
                name = keyword_data['name']
                keyword_info = next(kw for kw in keywords if kw.name == name)
                lines.append("")
                lines.append(self.formatter.format_text(
                    keyword_info, show_tags=False
                ))

    def _add_flat_list(self, lines: List[str], keywords: List[KeywordInfo]):
        """添加平铺的关键字列表"""
        # 按名称排序
        keywords.sort(key=lambda x: x.name)

        for keyword_info in keywords:
            lines.append("")
            lines.append(self.formatter.format_text(keyword_info))

    def list_keywords_json(self, options: KeywordListOptions) -> Dict[str, Any]:
        """以JSON格式列出关键字"""
        keywords = self.get_keywords(options)
        summary = self.get_keywords_summary(keywords)

        keywords_data = {
            'summary': summary,
            'categories': keyword_manager.get_categories(),
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
    functional_categories = keywords_data.get('functional_categories', {})

    # 按类别分组
    categories = {}
    for keyword in keywords:
        category = keyword['category']
        if category not in categories:
            categories[category] = []
        categories[category].append(keyword)

    # 按功能分类分组
    functional_groups = {}
    for keyword in keywords:
        functional_category = keyword.get('functional_category', 'other')
        if functional_category not in functional_groups:
            functional_groups[functional_category] = []
        functional_groups[functional_category].append(keyword)

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
        functional_groups=functional_groups,
        functional_categories=functional_categories,
        source_groups=source_groups,
        category_names=category_names,
        title="pytest-dsl 关键字报告"
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
                  category_name_filter: str = 'all',
                  tags_filter: Optional[List[str]] = None,
                  include_remote: bool = False,
                  output_file: Optional[str] = None,
                  print_summary: bool = True,
                  group_by: str = 'source') -> Union[str, Dict[str, Any], None]:
    """列出关键字的便捷函数

    Args:
        output_format: 输出格式 ('text', 'json', 'html')
        name_filter: 名称过滤器（支持部分匹配）
        category_filter: 来源类别过滤器
        category_name_filter: 功能分类过滤器
        tags_filter: 标签过滤器列表
        include_remote: 是否包含远程关键字
        output_file: 输出文件路径（可选）
        print_summary: 是否打印摘要信息
        group_by: 分组方式 ('source', 'functional', 'tags', 'flat')

    Returns:
        根据输出格式返回相应的数据，如果输出到文件则返回None
    """
    options = KeywordListOptions(
        output_format=output_format,
        name_filter=name_filter,
        category_filter=category_filter,
        category_name_filter=category_name_filter,
        tags_filter=tags_filter,
        include_remote=include_remote,
        output_file=output_file,
        group_by=group_by
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
    category_name_counts = summary.get('category_name_counts', {})

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

    print("按来源分类:")
    for cat, count in category_counts.items():
        cat_display = category_names.get(cat, cat)
        print(f"  {cat_display}: {count} 个")

    if category_name_counts:
        print("按功能分类:")
        categories = keyword_manager.get_categories()
        for cat, count in category_name_counts.items():
            cat_display = categories.get(cat, {}).get('name', cat)
            print(f"  {cat_display}: {count} 个")


def search_keywords(pattern: str,
                    include_remote: bool = False,
                    category_name: Optional[str] = None,
                    tags: Optional[List[str]] = None) -> List[KeywordInfo]:
    """搜索匹配模式的关键字

    Args:
        pattern: 搜索模式（支持部分匹配）
        include_remote: 是否包含远程关键字
        category_name: 功能分类过滤
        tags: 标签过滤列表

    Returns:
        匹配的关键字信息列表
    """
    options = KeywordListOptions(
        name_filter=pattern,
        category_name_filter=category_name or 'all',
        tags_filter=tags,
        include_remote=include_remote
    )
    return keyword_lister.get_keywords(options)


def get_keywords_by_category(category_name: str,
                             include_remote: bool = False) -> List[KeywordInfo]:
    """按功能分类获取关键字

    Args:
        category_name: 功能分类
        include_remote: 是否包含远程关键字

    Returns:
        关键字信息列表
    """
    options = KeywordListOptions(
        category_name_filter=category_name,
        include_remote=include_remote
    )
    return keyword_lister.get_keywords(options)


def get_keywords_by_tags(tags: List[str],
                        include_remote: bool = False) -> List[KeywordInfo]:
    """按标签获取关键字

    Args:
        tags: 标签列表
        include_remote: 是否包含远程关键字

    Returns:
        关键字信息列表
    """
    options = KeywordListOptions(
        tags_filter=tags,
        include_remote=include_remote
    )
    return keyword_lister.get_keywords(options)


def get_available_categories() -> Dict[str, Dict[str, str]]:
    """获取可用的功能分类

    Returns:
        功能分类字典
    """
    return keyword_manager.get_categories()


def get_available_tags() -> List[str]:
    """获取所有可用的标签

    Returns:
        标签列表
    """
    return sorted(list(keyword_manager.get_all_tags()))


# 为了向后兼容，保留原有的函数名
def get_keyword_info(keyword_name: str, include_remote: bool = False) -> Optional[KeywordInfo]:
    """获取单个关键字信息

    Args:
        keyword_name: 关键字名称
        include_remote: 是否包含远程关键字

    Returns:
        关键字信息或None
    """
    options = KeywordListOptions(
        name_filter=keyword_name,
        include_remote=include_remote
    )
    keywords = keyword_lister.get_keywords(options)
    
    # 寻找精确匹配
    for kw in keywords:
        if kw.name == keyword_name:
            return kw
    
    return None
