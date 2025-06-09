"""自动导入resources目录示例

该示例展示如何在项目中使用自动导入resources目录的功能。
系统会自动扫描并导入项目根目录下的resources目录中的所有.resource文件。
"""

from pytest_dsl.core.auto_decorator import auto_dsl


@auto_dsl("./")
class TestAutoImport:
    """自动导入测试类
    
    该类使用auto_dsl装饰器，会自动加载当前目录下的DSL文件。
    同时，pytest-dsl会自动导入项目中的resources目录。
    """
    pass


if __name__ == "__main__":
    import pytest
    import sys
    
    # 直接运行这个文件时，执行pytest
    sys.exit(pytest.main([__file__, "-v", "-s"])) 