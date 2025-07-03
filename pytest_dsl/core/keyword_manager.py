from typing import Dict, Any, Callable, List, Optional, Set
import functools
import allure


class Parameter:
    def __init__(self, name: str, mapping: str, description: str,
                 default: Any = None):
        self.name = name
        self.mapping = mapping
        self.description = description
        self.default = default


class KeywordManager:
    def __init__(self):
        self._keywords: Dict[str, Dict] = {}
        self.current_context = None
        # 支持多级分类的中文分类系统
        self._predefined_categories = {
            # HTTP相关（包含请求和断言）
            'HTTP': {'name': 'HTTP接口', 'description': 'HTTP接口测试和断言'},

            # UI相关
            'UI/浏览器': {'name': 'UI浏览器', 'description': '浏览器管理操作'},
            'UI/导航': {'name': 'UI导航', 'description': '页面导航操作'},
            'UI/元素': {'name': 'UI元素', 'description': '元素交互操作'},
            'UI/认证': {'name': 'UI认证', 'description': '认证状态管理'},
            'UI/网络': {'name': 'UI网络', 'description': '网络监控'},
            'UI/下载': {'name': 'UI下载', 'description': '文件下载'},
            'UI/验证码': {'name': 'UI验证码', 'description': '验证码处理'},

            # 数据相关
            '数据/JSON': {'name': '数据JSON', 'description': 'JSON数据处理'},
            '数据/变量': {'name': '数据变量', 'description': '变量管理'},
            '数据/文件': {'name': '数据文件', 'description': '文件操作'},

            # 系统相关
            '系统/调试': {'name': '系统调试', 'description': '调试输出'},
            '系统/等待': {'name': '系统等待', 'description': '等待操作'},

            # 其他
            '用户关键字': {'name': '用户关键字', 'description': '未分类功能'}
        }

    def register(self, name: str, parameters: List[Dict],
                 source_info: Optional[Dict] = None,
                 category: Optional[str] = None,
                 tags: Optional[List[str]] = None):
        """关键字注册装饰器

        Args:
            name: 关键字名称
            parameters: 参数列表
            source_info: 来源信息
            category: 功能分类（支持多级，如：UI/浏览器、HTTP/请求等）
            tags: 自定义标签列表
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(**kwargs):
                # 获取自定义步骤名称，如果未指定则使用关键字名称
                step_name = kwargs.pop('step_name', name)

                # 检查是否已经在DSL执行器的步骤中，避免重复记录
                skip_logging = kwargs.pop('skip_logging', False)

                with allure.step(f"{step_name}"):
                    try:
                        result = func(**kwargs)
                        if not skip_logging:
                            self._log_execution(step_name, kwargs, result)
                        return result
                    except Exception as e:
                        if not skip_logging:
                            self._log_failure(step_name, kwargs, e)
                        raise

            param_list = [Parameter(**p) for p in parameters]
            mapping = {p.name: p.mapping for p in param_list}
            defaults = {
                p.mapping: p.default for p in param_list
                if p.default is not None
            }

            # 自动添加 step_name 到 mapping 中
            mapping["步骤名称"] = "step_name"

            # 构建关键字信息，包含来源信息
            keyword_info = {
                'func': wrapper,
                'mapping': mapping,
                'parameters': param_list,
                'defaults': defaults  # 存储默认值
            }

            # 添加来源信息
            if source_info:
                keyword_info.update(source_info)
            else:
                # 尝试从函数模块推断来源信息
                keyword_info.update(self._infer_source_info(func))

            # 添加功能分类信息（显式指定或默认为其他）
            keyword_info['category'] = (
                self._normalize_category(category or '用户关键字')
            )

            # 添加标签信息
            keyword_info['tags'] = set(tags or [])

            self._keywords[name] = keyword_info
            return wrapper
        return decorator

    def _normalize_category(self, category: str) -> str:
        """标准化功能分类名称，支持多级分类"""
        if not category:
            return '用户关键字'

        # 直接返回用户指定的分类，支持自定义分类
        # 只有在没有指定分类的情况下才返回'用户关键字'
        return category.strip()

    def _infer_source_info(self, func: Callable) -> Dict:
        """从函数推断来源信息"""
        source_info = {}

        if hasattr(func, '__module__'):
            module_name = func.__module__
            source_info['module_name'] = module_name

            if module_name.startswith('pytest_dsl.keywords'):
                # 内置关键字
                source_info['source_type'] = 'builtin'
                source_info['source_name'] = 'pytest-dsl内置'
            elif 'pytest_dsl' in module_name:
                # pytest-dsl相关但不是内置的
                source_info['source_type'] = 'internal'
                source_info['source_name'] = 'pytest-dsl'
            else:
                # 第三方插件或用户自定义
                source_info['source_type'] = 'external'
                # 提取可能的包名
                parts = module_name.split('.')
                if len(parts) > 1:
                    source_info['source_name'] = parts[0]
                else:
                    source_info['source_name'] = module_name

        return source_info

    def register_with_source(self, name: str, parameters: List[Dict],
                             source_type: str, source_name: str,
                             category: Optional[str] = None,
                             tags: Optional[List[str]] = None, **kwargs):
        """带来源信息的关键字注册装饰器

        Args:
            name: 关键字名称
            parameters: 参数列表
            source_type: 来源类型
            source_name: 来源名称
            category: 功能分类
            tags: 自定义标签列表
            **kwargs: 其他来源相关信息
        """
        source_info = {
            'source_type': source_type,
            'source_name': source_name,
            **kwargs
        }
        return self.register(name, parameters, source_info, category, tags)

    def register_with_category(self, name: str, parameters: List[Dict],
                               category: str,
                               tags: Optional[List[str]] = None):
        """带功能分类的关键字注册装饰器

        Args:
            name: 关键字名称
            parameters: 参数列表  
            category: 功能分类
            tags: 自定义标签列表
        """
        return self.register(name, parameters, None, category, tags)

    def execute(self, keyword_name: str, **params: Any) -> Any:
        """执行关键字"""
        keyword_info = self._keywords.get(keyword_name)
        if not keyword_info:
            raise KeyError(f"未注册的关键字: {keyword_name}")

        # 应用默认值
        final_params = {}
        defaults = keyword_info.get('defaults', {})

        # 首先设置所有默认值
        for param_key, default_value in defaults.items():
            final_params[param_key] = default_value

        # 然后用传入的参数覆盖默认值
        final_params.update(params)

        return keyword_info['func'](**final_params)

    def get_keyword_info(self, keyword_name: str) -> Dict:
        """获取关键字信息"""
        keyword_info = self._keywords.get(keyword_name)
        if not keyword_info:
            return None

        # 动态添加step_name参数到参数列表中
        if not any(p.name == "步骤名称" for p in keyword_info['parameters']):
            keyword_info['parameters'].append(Parameter(
                name="步骤名称",
                mapping="step_name",
                description="自定义的步骤名称，用于在报告中显示"
            ))

        return keyword_info

    def get_keywords_by_category(self) -> Dict[str, List[str]]:
        """按功能分类分组获取关键字"""
        by_category = {}

        for name, info in self._keywords.items():
            category = info.get('category', '用户关键字')
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(name)

        return by_category

    def get_keywords_by_level1_category(self) -> Dict[str, List[str]]:
        """按一级分类分组获取关键字"""
        by_level1 = {}

        for name, info in self._keywords.items():
            category = info.get('category', '用户关键字')
            # 提取一级分类
            level1 = category.split('/')[0] if '/' in category else category

            if level1 not in by_level1:
                by_level1[level1] = []
            by_level1[level1].append(name)

        return by_level1

    def get_keywords_by_hierarchical_category(
            self) -> Dict[str, Dict[str, List[str]]]:
        """按层次化分类分组获取关键字"""
        hierarchical = {}

        for name, info in self._keywords.items():
            category = info.get('category', '用户关键字')

            if '/' in category:
                level1, level2 = category.split('/', 1)
            else:
                level1, level2 = category, '基础'

            if level1 not in hierarchical:
                hierarchical[level1] = {}
            if level2 not in hierarchical[level1]:
                hierarchical[level1][level2] = []

            hierarchical[level1][level2].append(name)

        return hierarchical

    def get_keywords_by_tags(self, tags: List[str]) -> List[str]:
        """根据标签获取关键字"""
        matching_keywords = []
        tags_set = set(tag.lower() for tag in tags)

        for name, info in self._keywords.items():
            keyword_tags = info.get('tags', set())
            keyword_tags_lower = set(tag.lower() for tag in keyword_tags)

            # 如果关键字包含任何指定的标签
            if tags_set & keyword_tags_lower:
                matching_keywords.append(name)

        return matching_keywords

    def get_keywords_by_source(self) -> Dict[str, List[str]]:
        """按来源分组获取关键字"""
        by_source = {}

        for name, info in self._keywords.items():
            source_name = info.get('source_name', '未知来源')
            if source_name not in by_source:
                by_source[source_name] = []
            by_source[source_name].append(name)

        return by_source

    def get_categories(self) -> Dict[str, Dict[str, str]]:
        """获取所有可用的功能分类"""
        return self._predefined_categories.copy()

    def add_category(self, key: str, name: str, description: str = ''):
        """添加新的功能分类（支持多级分类）

        Args:
            key: 分类键名（如：UI/新分类）
            name: 分类显示名称
            description: 分类描述
        """
        self._predefined_categories[key] = {
            'name': name,
            'description': description
        }

    def get_level1_categories(self) -> Set[str]:
        """获取所有一级分类（包含预定义和实际使用的分类）"""
        level1_categories = set()

        # 从预定义分类中获取
        for category_key in self._predefined_categories.keys():
            if '/' in category_key:
                level1 = category_key.split('/')[0]
                level1_categories.add(level1)
            else:
                level1_categories.add(category_key)

        # 从实际使用的关键字分类中获取
        for info in self._keywords.values():
            category = info.get('category', '用户关键字')
            if '/' in category:
                level1 = category.split('/')[0]
                level1_categories.add(level1)
            else:
                level1_categories.add(category)

        return level1_categories

    def get_level2_categories(self, level1: str) -> Set[str]:
        """获取指定一级分类下的所有二级分类（包含预定义和实际使用的分类）"""
        level2_categories = set()

        # 从预定义分类中获取
        for category_key in self._predefined_categories.keys():
            if category_key.startswith(f"{level1}/"):
                level2 = category_key.split('/', 1)[1]
                level2_categories.add(level2)

        # 从实际使用的关键字分类中获取
        for info in self._keywords.values():
            category = info.get('category', '用户关键字')
            if category.startswith(f"{level1}/"):
                level2 = category.split('/', 1)[1]
                level2_categories.add(level2)

        return level2_categories

    def get_all_tags(self) -> Set[str]:
        """获取所有使用过的标签"""
        all_tags = set()
        for info in self._keywords.values():
            all_tags.update(info.get('tags', set()))
        return all_tags

    def _log_execution(self, keyword_name: str, params: Dict,
                       result: Any) -> None:
        """记录关键字执行结果"""
        allure.attach(
            f"参数: {params}\n返回值: {result}",
            name=f"关键字 {keyword_name} 执行详情",
            attachment_type=allure.attachment_type.TEXT
        )

    def _log_failure(self, keyword_name: str, params: Dict,
                     error: Exception) -> None:
        """记录关键字执行失败"""
        allure.attach(
            f"参数: {params}\n异常: {str(error)}",
            name=f"关键字 {keyword_name} 执行失败",
            attachment_type=allure.attachment_type.TEXT
        )

    def generate_docs(self) -> str:
        """生成关键字文档"""
        docs = []
        for name, info in self._keywords.items():
            docs.append(f"关键字: {name}")
            docs.append("参数:")
            # 确保step_name参数在文档中显示
            if not any(p.name == "步骤名称" for p in info['parameters']):
                info['parameters'].append(Parameter(
                    name="步骤名称",
                    mapping="step_name",
                    description="自定义的步骤名称，用于在报告中显示"
                ))
            for param in info['parameters']:
                default_info = (
                    f" (默认值: {param.default})"
                    if param.default is not None else ""
                )
                docs.append(
                    f"  {param.name} ({param.mapping}): "
                    f"{param.description}{default_info}"
                )
            docs.append("")
        return "\n".join(docs)


# 创建全局关键字管理器实例
keyword_manager = KeywordManager()
