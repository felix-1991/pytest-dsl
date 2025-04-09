"""
pytest-dsl - 基于pytest的DSL测试框架

使用自定义的领域特定语言(DSL)来编写测试用例，使测试更加直观、易读和易维护。
"""

__version__ = "0.1.0" 

# 导出 auto_dsl 装饰器，使其可以直接从包导入
from pytest_dsl.core.auto_decorator import auto_dsl