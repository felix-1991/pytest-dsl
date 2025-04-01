"""pytest-dsl插件的主要入口文件

该文件负责将DSL功能集成到pytest框架中，包括命令行参数处理、YAML变量加载、
自定义目录收集器等功能。
"""
import pytest
import os
from pathlib import Path

# 导入模块化组件
from pytest_dsl.core.yaml_loader import add_yaml_options, load_yaml_variables
from pytest_dsl.core.plugin_discovery import load_all_plugins, scan_local_keywords
from pytest_dsl.core.global_context import global_context


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

    # 加载YAML变量文件
    load_yaml_variables(config)

    # 确保全局变量存储目录存在
    os.makedirs(global_context._storage_dir, exist_ok=True)

    # 加载所有已安装的关键字插件
    load_all_plugins()
    
    # 加载本地关键字（向后兼容）
    scan_local_keywords() 