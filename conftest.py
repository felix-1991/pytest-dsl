"""pytest-dsl插件的主要配置文件

该文件负责将DSL功能集成到pytest框架中，包括命令行参数处理、YAML变量加载、
自定义目录收集器等功能。
"""

import pytest
import os
from pathlib import Path
from core.global_context import global_context

# 导入模块化组件
from core.yaml_loader import add_yaml_options, load_yaml_variables
from core.auto_directory import AutoDirectory, init_setup_teardown_tracking


def pytest_addoption(parser):
    """添加命令行参数选项
    
    Args:
        parser: pytest命令行参数解析器
    """
    # 使用yaml_loader模块添加YAML相关选项
    add_yaml_options(parser)


@pytest.hookimpl
def pytest_configure(config):
    """配置测试会话，加载已执行的setup/teardown信息和YAML变量
    
    Args:
        config: pytest配置对象
    """
    # 初始化setup和teardown跟踪状态
    init_setup_teardown_tracking()
    
    # 加载YAML变量文件
    load_yaml_variables(config)
    
    # 确保全局变量存储目录存在
    os.makedirs(global_context._storage_dir, exist_ok=True)
