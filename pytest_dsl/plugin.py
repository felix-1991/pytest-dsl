"""pytest-dsl插件的主要入口文件

该文件负责将DSL功能集成到pytest框架中，包括命令行参数处理、YAML变量加载、
自定义目录收集器等功能。
"""
import pytest
import os

# 导入模块化组件
from pytest_dsl.core.yaml_loader import add_yaml_options, load_yaml_variables
from pytest_dsl.core.plugin_discovery import (
    load_all_plugins, scan_local_keywords
)
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

    # 首先导入内置关键字模块，确保内置关键字被注册
    try:
        import pytest_dsl.keywords  # noqa: F401
        print("pytest环境：内置关键字模块加载完成")
    except ImportError as e:
        print(f"pytest环境：加载内置关键字模块失败: {e}")

    # 加载所有已安装的关键字插件
    load_all_plugins()

    # 加载本地关键字（向后兼容）
    scan_local_keywords()

    # 自动导入项目中的resources目录
    try:
        from pytest_dsl.core.custom_keyword_manager import (
            custom_keyword_manager
        )

        # 获取pytest的根目录
        project_root = str(config.rootdir) if config.rootdir else os.getcwd()

        # 检查是否存在resources目录
        resources_dir = os.path.join(project_root, "resources")
        if os.path.exists(resources_dir) and os.path.isdir(resources_dir):
            custom_keyword_manager.auto_import_resources_directory(
                project_root)
            print(f"pytest环境：已自动导入resources目录 {resources_dir}")

    except Exception as e:
        print(f"pytest环境：自动导入resources目录时出现警告: {str(e)}")
