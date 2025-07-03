"""
pytest-dsl关键字加载器

提供统一的关键字加载和管理功能，包括：
- 内置关键字加载
- 插件关键字发现和加载
- 本地关键字扫描
- 项目自定义关键字扫描
- 远程关键字支持
- 关键字分类和信息获取
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

from pytest_dsl.core.plugin_discovery import load_all_plugins, scan_local_keywords
from pytest_dsl.core.keyword_manager import keyword_manager
from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import get_parser


class KeywordLoader:
    """关键字加载器类"""
    
    def __init__(self):
        self._project_custom_keywords = None
    
    def load_all_keywords(self, include_remote: bool = False) -> Dict[str, Any]:
        """加载所有可用的关键字

        Args:
            include_remote: 是否包含远程关键字，默认为False

        Returns:
            项目自定义关键字信息字典
        """
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

        # 自动导入项目中的resources目录
        self._load_resources_directory()

        # 扫描项目中的自定义关键字（.resource文件中定义的）
        project_custom_keywords = self.scan_project_custom_keywords()
        if project_custom_keywords:
            print(f"发现 {len(project_custom_keywords)} 个项目自定义关键字")
            self._load_resource_files(project_custom_keywords)

        # 根据参数决定是否加载远程关键字
        if include_remote:
            print("正在扫描远程关键字...")
            # 这里可以添加远程关键字的扫描逻辑
            # 目前远程关键字是通过DSL文件中的@remote导入指令动态加载的
        else:
            print("跳过远程关键字扫描")

        self._project_custom_keywords = project_custom_keywords
        return project_custom_keywords

    def _load_resources_directory(self):
        """自动导入项目中的resources目录"""
        try:
            from pytest_dsl.core.custom_keyword_manager import custom_keyword_manager

            # 尝试从多个可能的项目根目录位置导入resources
            possible_roots = [
                os.getcwd(),  # 当前工作目录
                os.path.dirname(os.getcwd()),  # 上级目录
            ]

            # 尝试每个可能的根目录
            for project_root in possible_roots:
                if project_root and os.path.exists(project_root):
                    resources_dir = os.path.join(project_root, "resources")
                    if (os.path.exists(resources_dir) and
                            os.path.isdir(resources_dir)):
                        custom_keyword_manager.auto_import_resources_directory(
                            project_root)
                        break
        except Exception as e:
            print(f"自动导入resources目录时出现警告: {str(e)}")

    def _load_resource_files(self, project_custom_keywords: Dict[str, Any]):
        """加载.resource文件中的关键字到关键字管理器"""
        from pytest_dsl.core.custom_keyword_manager import custom_keyword_manager

        project_root = Path(os.getcwd())
        resource_files = list(project_root.glob('**/*.resource'))

        for resource_file in resource_files:
            try:
                custom_keyword_manager.load_resource_file(str(resource_file))
                print(f"已加载资源文件: {resource_file}")
            except Exception as e:
                print(f"加载资源文件失败 {resource_file}: {e}")

    def scan_project_custom_keywords(self, project_root: Optional[str] = None) -> Dict[str, Any]:
        """扫描项目中.resource文件中的自定义关键字

        Args:
            project_root: 项目根目录，默认为当前工作目录

        Returns:
            自定义关键字信息，格式为 
            {keyword_name: {'file': file_path, 'node': ast_node, 'parameters': [...]}}
        """
        if project_root is None:
            project_root = os.getcwd()

        project_root = Path(project_root)
        custom_keywords = {}

        # 查找所有.resource文件
        resource_files = list(project_root.glob('**/*.resource'))

        if not resource_files:
            return custom_keywords

        lexer = get_lexer()
        parser = get_parser()

        for file_path in resource_files:
            try:
                # 读取并解析文件
                content = self._read_file(str(file_path))
                ast = parser.parse(content, lexer=lexer)

                # 查找自定义关键字定义
                keywords_in_file = self._extract_custom_keywords_from_ast(
                    ast, str(file_path)
                )
                custom_keywords.update(keywords_in_file)

            except Exception as e:
                print(f"解析资源文件 {file_path} 时出错: {e}")

        return custom_keywords

    def _read_file(self, filename: str) -> str:
        """读取文件内容"""
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()

    def _extract_custom_keywords_from_ast(self, ast, file_path: str) -> Dict[str, Any]:
        """从AST中提取自定义关键字定义

        Args:
            ast: 抽象语法树
            file_path: 文件路径

        Returns:
            自定义关键字信息字典
        """
        custom_keywords = {}

        if ast.type != 'Start' or len(ast.children) < 2:
            return custom_keywords

        # 遍历语句节点
        statements_node = ast.children[1]
        if statements_node.type != 'Statements':
            return custom_keywords

        for node in statements_node.children:
            # 支持两种格式：CustomKeyword（旧格式）和Function（新格式）
            if node.type in ['CustomKeyword', 'Function']:
                keyword_name = node.value

                # 提取参数信息
                params_node = node.children[0] if node.children else None
                parameters = []

                if params_node:
                    for param in params_node:
                        param_name = param.value
                        param_default = None

                        # 检查是否有默认值
                        if param.children and param.children[0]:
                            param_default = param.children[0].value

                        param_info = {
                            'name': param_name,
                            'mapping': param_name,
                            'description': f'自定义关键字参数 {param_name}'
                        }

                        if param_default is not None:
                            param_info['default'] = param_default

                        parameters.append(param_info)

                custom_keywords[keyword_name] = {
                    'file': file_path,
                    'node': node,
                    'type': 'project_custom',
                    'parameters': parameters
                }

        return custom_keywords

    def categorize_keyword(self, keyword_name: str, keyword_info: Dict[str, Any],
                          project_custom_keywords: Optional[Dict[str, Any]] = None) -> str:
        """判断关键字的来源类别

        Args:
            keyword_name: 关键字名称
            keyword_info: 关键字信息
            project_custom_keywords: 项目自定义关键字信息

        Returns:
            关键字来源类别：'builtin', 'plugin', 'custom', 'project_custom', 'remote'
        """
        # 优先使用存储的来源信息
        source_type = keyword_info.get('source_type')
        if source_type:
            if source_type == 'builtin':
                return 'builtin'
            elif source_type == 'plugin':
                return 'plugin'
            elif source_type in ['external', 'local']:
                return 'custom'
            elif source_type == 'project_custom':
                return 'project_custom'

        # 向后兼容：使用原有的判断逻辑
        if keyword_info.get('remote', False):
            return 'remote'

        # 检查是否是项目自定义关键字（DSL文件中定义的）
        if project_custom_keywords and keyword_name in project_custom_keywords:
            return 'project_custom'

        # 检查是否是内置关键字（通过检查函数所在模块）
        func = keyword_info.get('func')
        if func and hasattr(func, '__module__'):
            module_name = func.__module__
            if module_name and module_name.startswith('pytest_dsl.keywords'):
                return 'builtin'

        return 'custom'

    def get_functional_category(self, keyword_info: Dict[str, Any]) -> str:
        """获取关键字的功能分类"""
        return keyword_info.get('functional_category', 'other')

    def get_keyword_tags(self, keyword_info: Dict[str, Any]) -> set:
        """获取关键字的标签"""
        return keyword_info.get('tags', set())

    def get_keyword_source_info(self, keyword_info: Dict[str, Any]) -> Dict[str, Any]:
        """获取关键字的详细来源信息

        Args:
            keyword_info: 关键字信息

        Returns:
            来源信息字典
        """
        source_type = keyword_info.get('source_type', 'unknown')
        source_name = keyword_info.get('source_name', '未知')

        return {
            'type': source_type,
            'name': source_name,
            'display_name': source_name,
            'module': keyword_info.get('module_name', ''),
            'plugin_module': keyword_info.get('plugin_module', '')
        }

    def group_keywords_by_source(self, keywords_dict: Dict[str, Any],
                                project_custom_keywords: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, List]]:
        """按来源分组关键字

        Args:
            keywords_dict: 关键字字典
            project_custom_keywords: 项目自定义关键字信息

        Returns:
            分组后的关键字字典，格式为 {source_group: {source_name: [keywords]}}
        """
        groups = {
            'builtin': {},
            'plugin': {},
            'custom': {},
            'project_custom': {},
            'remote': {}
        }

        for keyword_name, keyword_info in keywords_dict.items():
            category = self.categorize_keyword(
                keyword_name, keyword_info, project_custom_keywords
            )
            source_info = self.get_keyword_source_info(keyword_info)

            # 特殊处理项目自定义关键字
            if category == 'project_custom' and project_custom_keywords:
                custom_info = project_custom_keywords[keyword_name]
                source_name = custom_info['file']
            else:
                source_name = source_info['name']

            if source_name not in groups[category]:
                groups[category][source_name] = []

            groups[category][source_name].append({
                'name': keyword_name,
                'info': keyword_info,
                'source_info': source_info
            })

        return groups

    def group_keywords_by_functional_category(self, keywords_dict: Dict[str, Any]) -> Dict[str, List]:
        """按功能分类分组关键字

        Args:
            keywords_dict: 关键字字典

        Returns:
            按功能分类分组的关键字字典
        """
        groups = {}

        for keyword_name, keyword_info in keywords_dict.items():
            functional_category = self.get_functional_category(keyword_info)
            
            if functional_category not in groups:
                groups[functional_category] = []
            
            groups[functional_category].append({
                'name': keyword_name,
                'info': keyword_info,
                'tags': list(self.get_keyword_tags(keyword_info))
            })

        return groups

    def group_keywords_by_tags(self, keywords_dict: Dict[str, Any]) -> Dict[str, List]:
        """按标签分组关键字

        Args:
            keywords_dict: 关键字字典

        Returns:
            按标签分组的关键字字典
        """
        groups = {}

        for keyword_name, keyword_info in keywords_dict.items():
            tags = self.get_keyword_tags(keyword_info)
            
            for tag in tags:
                if tag not in groups:
                    groups[tag] = []
                
                groups[tag].append({
                    'name': keyword_name,
                    'info': keyword_info,
                    'functional_category': self.get_functional_category(keyword_info)
                })

        return groups

    def get_keyword_statistics(self, keywords_dict: Dict[str, Any],
                              project_custom_keywords: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取关键字统计信息

        Args:
            keywords_dict: 关键字字典
            project_custom_keywords: 项目自定义关键字信息

        Returns:
            统计信息字典
        """
        stats = {
            'total_count': len(keywords_dict),
            'source_counts': {},
            'category_name_counts': {},
            'tag_counts': {},
            'combined_stats': {}
        }

        # 按来源统计
        for keyword_name, keyword_info in keywords_dict.items():
            source_category = self.categorize_keyword(
                keyword_name, keyword_info, project_custom_keywords
            )
            stats['source_counts'][source_category] = stats['source_counts'].get(source_category, 0) + 1

        # 按功能分类统计
        for keyword_name, keyword_info in keywords_dict.items():
            category_name = keyword_info.get('category', '其他')
            stats['category_name_counts'][category_name] = stats['category_name_counts'].get(category_name, 0) + 1

        # 按标签统计
        for keyword_name, keyword_info in keywords_dict.items():
            tags = self.get_keyword_tags(keyword_info)
            for tag in tags:
                stats['tag_counts'][tag] = stats['tag_counts'].get(tag, 0) + 1

        # 组合统计（来源+功能分类）
        for keyword_name, keyword_info in keywords_dict.items():
            source_category = self.categorize_keyword(
                keyword_name, keyword_info, project_custom_keywords
            )
            functional_category = self.get_functional_category(keyword_info)
            combined_key = f"{source_category}:{functional_category}"
            stats['combined_stats'][combined_key] = stats['combined_stats'].get(combined_key, 0) + 1

        return stats

    def get_all_keywords(self) -> Dict[str, Any]:
        """获取所有已注册的关键字

        Returns:
            所有关键字的字典
        """
        return keyword_manager._keywords

    def get_project_custom_keywords(self) -> Optional[Dict[str, Any]]:
        """获取项目自定义关键字信息

        Returns:
            项目自定义关键字信息，如果尚未加载则返回None
        """
        return self._project_custom_keywords


# 创建全局实例
keyword_loader = KeywordLoader()


# 便捷函数
def load_all_keywords(include_remote: bool = False) -> Dict[str, Any]:
    """加载所有可用的关键字

    Args:
        include_remote: 是否包含远程关键字，默认为False

    Returns:
        项目自定义关键字信息字典
    """
    return keyword_loader.load_all_keywords(include_remote=include_remote)


def categorize_keyword(keyword_name: str, keyword_info: Dict[str, Any],
                      project_custom_keywords: Optional[Dict[str, Any]] = None) -> str:
    """判断关键字的类别

    Args:
        keyword_name: 关键字名称
        keyword_info: 关键字信息
        project_custom_keywords: 项目自定义关键字信息

    Returns:
        关键字类别
    """
    return keyword_loader.categorize_keyword(keyword_name, keyword_info, project_custom_keywords)


def get_keyword_source_info(keyword_info: Dict[str, Any]) -> Dict[str, Any]:
    """获取关键字的详细来源信息

    Args:
        keyword_info: 关键字信息

    Returns:
        来源信息字典
    """
    return keyword_loader.get_keyword_source_info(keyword_info)


def group_keywords_by_source(keywords_dict: Dict[str, Any],
                            project_custom_keywords: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, List]]:
    """按来源分组关键字

    Args:
        keywords_dict: 关键字字典
        project_custom_keywords: 项目自定义关键字信息

    Returns:
        分组后的关键字字典
    """
    return keyword_loader.group_keywords_by_source(keywords_dict, project_custom_keywords)


def scan_project_custom_keywords(project_root: Optional[str] = None) -> Dict[str, Any]:
    """扫描项目中.resource文件中的自定义关键字

    Args:
        project_root: 项目根目录，默认为当前工作目录

    Returns:
        自定义关键字信息字典
    """
    return keyword_loader.scan_project_custom_keywords(project_root) 