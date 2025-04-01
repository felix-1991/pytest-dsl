"""YAML变量加载器模块

该模块负责处理YAML变量文件的加载和管理，支持从命令行参数加载单个文件或目录。
"""

import os
from pathlib import Path
from pytest_dsl.core.yaml_vars import yaml_vars


def add_yaml_options(parser):
    """添加YAML变量相关的命令行参数选项
    
    Args:
        parser: pytest命令行参数解析器
    """
    group = parser.getgroup('yaml-vars')
    group.addoption(
        '--yaml-vars',
        action='append',
        default=[],
        help='YAML变量文件路径，可以指定多个文件 (例如: --yaml-vars vars1.yaml --yaml-vars vars2.yaml)'
    )
    group.addoption(
        '--yaml-vars-dir',
        action='store',
        default=None,
        help='YAML变量文件目录路径，将加载该目录下所有.yaml文件，默认为项目根目录下的config目录'
    )


def load_yaml_variables(config):
    """加载YAML变量文件
    
    从命令行参数指定的文件和目录加载YAML变量。
    
    Args:
        config: pytest配置对象
    """
    # 加载单个YAML文件
    yaml_files = config.getoption('--yaml-vars')
    if yaml_files:
        yaml_vars.load_yaml_files(yaml_files)
        print(f"已加载YAML变量文件: {', '.join(yaml_files)}")

    # 加载目录中的YAML文件
    yaml_vars_dir = config.getoption('--yaml-vars-dir')
    if yaml_vars_dir is None:
        # 默认使用使用者项目根目录下的config目录
        # 通过pytest的rootdir获取使用者的项目根目录
        project_root = config.rootdir
        yaml_vars_dir = str(project_root / 'config')
        print(f"使用默认YAML变量目录: {yaml_vars_dir}")
    
    if Path(yaml_vars_dir).exists():
        yaml_vars.load_from_directory(yaml_vars_dir)
        print(f"已加载YAML变量目录: {yaml_vars_dir}")
        loaded_files = yaml_vars.get_loaded_files()
        if loaded_files:
            print(f"目录中加载的文件: {', '.join(loaded_files)}")
    else:
        print(f"YAML变量目录不存在: {yaml_vars_dir}")