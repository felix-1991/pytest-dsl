"""
pytest-dsl - 基于pytest的DSL测试框架

使用自定义的领域特定语言(DSL)来编写测试用例，使测试更加直观、易读和易维护。

主要功能：
- DSL语法解析和执行
- 关键字管理和注册
- Hook机制支持插件扩展
- DSL格式校验
- 远程关键字支持
- 自定义关键字支持
"""

__version__ = "0.16.1"

# 核心执行器
from pytest_dsl.core.dsl_executor import DSLExecutor

# 关键字管理器
from pytest_dsl.core.keyword_manager import keyword_manager, KeywordManager

# Hook系统
from pytest_dsl.core.hookspecs import hookimpl, hookspec, DSLHookSpecs
from pytest_dsl.core.hook_manager import hook_manager, DSLHookManager
from pytest_dsl.core.hookable_keyword_manager import hookable_keyword_manager

# DSL格式校验
from pytest_dsl.core.validator import (
    DSLValidator,
    DSLValidationError,
    validate_dsl,
    check_dsl_syntax
)

# 自动装饰器
from pytest_dsl.core.auto_decorator import auto_dsl

# 核心工具类
from pytest_dsl.core.parser import Node, get_parser
from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.context import TestContext
from pytest_dsl.core.global_context import global_context

# 变量工具
from pytest_dsl.core.variable_utils import VariableReplacer

# 自定义关键字管理器
from pytest_dsl.core.custom_keyword_manager import custom_keyword_manager

# 远程服务器注册器
from pytest_dsl.core.remote_server_registry import (
    remote_server_registry, RemoteServerRegistry,
    register_remote_server_with_variables,
    create_database_variable_provider,
    create_config_file_variable_provider
)

# 远程服务器配置加载器
from pytest_dsl.core.yaml_loader import (
    load_remote_servers_from_yaml,
    register_remote_servers_from_config
)

# 关键字加载器
from pytest_dsl.core.keyword_loader import (
    keyword_loader, KeywordLoader,
    load_all_keywords, categorize_keyword, get_keyword_source_info,
    group_keywords_by_source, scan_project_custom_keywords
)

# 关键字工具
from pytest_dsl.core.keyword_utils import (
    KeywordInfo, KeywordListOptions, KeywordFormatter, KeywordLister,
    keyword_lister, list_keywords, get_keyword_info, search_keywords,
    generate_html_report
)

# 远程关键字功能
try:
    from pytest_dsl.remote import (
        remote_keyword_manager, RemoteKeywordManager, RemoteKeywordClient,
        register_remote_server, register_multiple_servers
    )
    _REMOTE_AVAILABLE = True
except ImportError:
    # 如果远程功能依赖不可用，设置为None
    remote_keyword_manager = None
    RemoteKeywordManager = None
    RemoteKeywordClient = None
    register_remote_server = None
    register_multiple_servers = None
    _REMOTE_AVAILABLE = False

# 便捷导入的别名
Executor = DSLExecutor
Validator = DSLValidator
HookManager = DSLHookManager
KeywordLoader = KeywordLoader

# 导出所有公共接口
__all__ = [
    # 版本信息
    '__version__',

    # 核心执行器
    'DSLExecutor', 'Executor',

    # 关键字管理
    'keyword_manager', 'KeywordManager',
    'custom_keyword_manager',

    # 关键字加载器
    'keyword_loader', 'KeywordLoader',
    'load_all_keywords', 'categorize_keyword', 'get_keyword_source_info',
    'group_keywords_by_source', 'scan_project_custom_keywords',

    # 关键字工具
    'KeywordInfo', 'KeywordListOptions', 'KeywordFormatter', 'KeywordLister',
    'keyword_lister', 'list_keywords', 'get_keyword_info', 'search_keywords',
    'generate_html_report',

    # Hook系统
    'hookimpl', 'hookspec', 'DSLHookSpecs',
    'hook_manager', 'DSLHookManager', 'HookManager', 'hookable_keyword_manager',

    # DSL校验
    'DSLValidator', 'Validator',
    'DSLValidationError',
    'validate_dsl',
    'check_dsl_syntax',

    # 自动装饰器
    'auto_dsl',

    # 核心组件
    'Node', 'get_parser', 'get_lexer',
    'TestContext', 'global_context',
    'VariableReplacer',

    # 远程关键字功能（如果可用）
    'remote_keyword_manager', 'RemoteKeywordManager', 'RemoteKeywordClient',
    'register_remote_server', 'register_multiple_servers',

    # 远程服务器注册器
    'remote_server_registry', 'RemoteServerRegistry',
    'register_remote_server_with_variables',
    'create_database_variable_provider', 
    'create_config_file_variable_provider',
    'load_remote_servers_from_yaml', 'register_remote_servers_from_config',
]

# 快捷函数


def create_executor(enable_hooks: bool = True) -> DSLExecutor:
    """创建DSL执行器实例

    Args:
        enable_hooks: 是否启用hook机制

    Returns:
        DSL执行器实例
    """
    return DSLExecutor(enable_hooks=enable_hooks)


def parse_dsl(content: str) -> Node:
    """解析DSL内容为AST

    Args:
        content: DSL内容

    Returns:
        解析后的AST根节点
    """
    lexer = get_lexer()
    parser = get_parser()
    return parser.parse(content, lexer=lexer)


def execute_dsl(content: str, context: dict = None,
                enable_hooks: bool = True) -> any:
    """执行DSL内容的便捷函数

    Args:
        content: DSL内容
        context: 执行上下文（可选）
        enable_hooks: 是否启用hook机制

    Returns:
        执行结果
    """
    executor = create_executor(enable_hooks=enable_hooks)
    if context:
        executor.variables.update(context)
        for key, value in context.items():
            executor.test_context.set(key, value)

    ast = parse_dsl(content)
    return executor.execute(ast)


def register_keyword(name: str, parameters: list = None,
                     source_type: str = "external",
                     source_name: str = "user_defined"):
    """注册关键字的装饰器

    Args:
        name: 关键字名称
        parameters: 参数列表
        source_type: 来源类型
        source_name: 来源名称

    Returns:
        装饰器函数
    """
    if parameters is None:
        parameters = []

    return keyword_manager.register_with_source(
        name=name,
        parameters=parameters,
        source_type=source_type,
        source_name=source_name
    )


# 版本兼容性检查
def check_version_compatibility():
    """检查版本兼容性"""
    try:
        import sys
        if sys.version_info < (3, 7):
            import warnings
            warnings.warn(
                "pytest-dsl 需要 Python 3.7 或更高版本",
                UserWarning,
                stacklevel=2
            )
    except Exception:
        pass


# 远程功能检查
def is_remote_available() -> bool:
    """检查远程功能是否可用"""
    return _REMOTE_AVAILABLE


# 初始化时进行版本检查
check_version_compatibility()

# 自动初始化hook管理器
try:
    hook_manager.initialize()
except Exception as e:
    import warnings
    warnings.warn(f"Hook管理器初始化失败: {e}", UserWarning, stacklevel=2)
