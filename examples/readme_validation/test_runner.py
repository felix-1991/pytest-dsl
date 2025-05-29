#!/usr/bin/env python3
"""
pytest集成示例
演示如何使用pytest运行DSL文件，包括数据驱动测试
"""

from pytest_dsl.core.auto_decorator import auto_dsl

@auto_dsl("./")
class TestReadmeExamples:
    """README.md示例测试套件
    
    自动加载当前目录下的所有DSL文件
    """
    pass

# 如果直接运行此文件，执行pytest
if __name__ == "__main__":
    import pytest
    import sys
    
    # 运行pytest，包括数据驱动测试
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short"
    ])
    
    sys.exit(exit_code)
