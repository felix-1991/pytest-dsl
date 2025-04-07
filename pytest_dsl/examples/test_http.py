"""装饰器测试示例

该示例展示如何使用auto_dsl装饰器创建测试类
"""

from pytest_dsl.core.auto_decorator import auto_dsl


# 同时使用多个目录的测试类
@auto_dsl("./http")
class TestHttp:
    """HTTP测试类
    
    该类使用auto_dsl装饰器，测试http目录下的.auto文件。
    """
    pass

# 特定测试长度捕获功能的测试类
@auto_dsl("./http/http_length_test.auto", is_file=True)
class TestHttpLengthCapture:
    """HTTP长度捕获测试类
    
    该类专门测试HTTP请求中的长度捕获功能。
    """
    pass