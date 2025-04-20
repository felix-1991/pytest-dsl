"""入门示例

该文件展示了如何使用pytest-dsl创建简单的API测试
"""

from pytest_dsl.core.auto_decorator import auto_dsl

@auto_dsl("./quickstart")
class TestQuickstart:
    """入门示例测试类
    
    该类将自动加载quickstart目录下的所有.auto文件作为测试方法
    """
    pass 