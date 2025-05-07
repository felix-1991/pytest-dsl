from pytest_dsl.core.auto_decorator import auto_dsl

@auto_dsl("./custom")
class TestCustomKeyword:
    """自定义关键字测试
    
    此测试类将自动加载当前目录下的所有.auto文件
    """
    pass 