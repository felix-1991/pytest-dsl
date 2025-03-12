"""插件发现模块

该模块提供了发现和加载第三方关键字插件的功能。
它使用Python的entry_points机制来发现已安装的插件包，并动态加载其中的关键字。
"""

import importlib
import importlib.util
import importlib.metadata
import pkgutil
from typing import List

from core.keyword_manager import keyword_manager


def discover_installed_plugins() -> List[str]:
    """
    发现所有已安装的pytest-dsl关键字插件
    
    通过entry_points机制查找所有声明了'pytest_dsl.keywords'入口点的包
    
    Returns:
        List[str]: 已安装的插件包名列表
    """
    plugins = []
    try:
        eps = importlib.metadata.entry_points(group='pytest_dsl.keywords')
        for ep in eps:
            plugins.append(ep.module)
    except Exception as e:
        print(f"发现插件时出错: {e}")
    return plugins


def load_plugin_keywords(plugin_name: str) -> None:
    """
    加载指定插件包中的所有关键字
    
    Args:
        plugin_name: 插件包名
    """
    try:
        # 导入插件包
        plugin = importlib.import_module(plugin_name)
        
        # 如果插件有register_keywords函数，调用它
        if hasattr(plugin, 'register_keywords') and callable(plugin.register_keywords):
            plugin.register_keywords(keyword_manager)
            return
        
        # 否则，遍历包中的所有模块
        if hasattr(plugin, '__path__'):
            for _, name, is_pkg in pkgutil.iter_modules(plugin.__path__, plugin.__name__ + '.'):
                if not is_pkg:
                    try:
                        module = importlib.import_module(name)
                        # 模块已导入，关键字装饰器会自动注册
                    except ImportError as e:
                        print(f"无法导入模块 {name}: {e}")
    except ImportError as e:
        print(f"无法导入插件 {plugin_name}: {e}")


def load_all_plugins() -> None:
    """
    发现并加载所有已安装的关键字插件
    """
    plugins = discover_installed_plugins()
    for plugin_name in plugins:
        load_plugin_keywords(plugin_name)


def scan_local_keywords() -> None:
    """
    扫描本地keywords目录中的关键字
    
    这个函数保留了向后兼容性，确保内置关键字仍然可用
    """
    try:
        import keywords
    except ImportError:
        print("警告: 未找到内置关键字包")


if __name__ == "__main__":
    load_all_plugins()