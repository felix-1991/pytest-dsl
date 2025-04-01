"""装饰器测试示例

该示例展示如何使用auto_dsl装饰器创建测试类
"""

from pytest_dsl.core.auto_decorator import auto_dsl


# 同时使用多个目录的测试类
@auto_dsl("./assert")
class TestAssert:
    """断言测试类
    
    该类使用auto_dsl装饰器，测试assert目录下的.auto文件。
    """
    pass