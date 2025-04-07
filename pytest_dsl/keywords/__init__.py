"""
自动导入所有关键字模块以注册关键字
"""
from . import system_keywords
from . import global_keywords  # 全局变量关键字
from . import assertion_keywords
from . import http_keywords  # HTTP请求关键字

# 可以在这里添加更多关键字模块的导入
__all__ = ['system_keywords', 'global_keywords', 'assertion_keywords', 'http_keywords']
