"""
自动导入所有关键字模块以注册关键字
"""
from . import system_keywords
from . import api_keywords

# 可以在这里添加更多关键字模块的导入
__all__ = ['system_keywords', 'api_keywords']
