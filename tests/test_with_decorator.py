"""装饰器测试示例

该示例展示如何使用auto_dsl装饰器创建测试类，而不依赖于conftest.py中的目录收集器。
"""

import pytest
from core.auto_decorator import auto_dsl


# 同时使用多个目录的测试类
@auto_dsl("./login")
@auto_dsl("./register")
@auto_dsl("./driver")
class TestMultiDirectories:
    """多目录测试类
    
    该类使用多个auto_dsl装饰器，同时测试多个目录下的.auto文件。
    """
    pass