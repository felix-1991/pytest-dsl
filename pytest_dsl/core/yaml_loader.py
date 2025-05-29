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


def load_yaml_variables_from_args(yaml_files=None, yaml_vars_dir=None, project_root=None):
    """从参数加载YAML变量文件（通用函数）

    Args:
        yaml_files: YAML文件列表
        yaml_vars_dir: YAML变量目录路径
        project_root: 项目根目录（用于默认config目录）
    """
    # 加载单个YAML文件
    if yaml_files:
        yaml_vars.load_yaml_files(yaml_files)
        print(f"已加载YAML变量文件: {', '.join(yaml_files)}")

    # 加载目录中的YAML文件
    if yaml_vars_dir is None and project_root:
        # 默认使用项目根目录下的config目录
        yaml_vars_dir = str(Path(project_root) / 'config')
        print(f"使用默认YAML变量目录: {yaml_vars_dir}")

    if yaml_vars_dir and Path(yaml_vars_dir).exists():
        yaml_vars.load_from_directory(yaml_vars_dir)
        print(f"已加载YAML变量目录: {yaml_vars_dir}")
        loaded_files = yaml_vars.get_loaded_files()
        if loaded_files:
            # 过滤出当前目录的文件
            if yaml_vars_dir:
                dir_files = [f for f in loaded_files if Path(f).parent == Path(yaml_vars_dir)]
                if dir_files:
                    print(f"目录中加载的文件: {', '.join(dir_files)}")
            else:
                print(f"加载的文件: {', '.join(loaded_files)}")
    elif yaml_vars_dir:
        print(f"YAML变量目录不存在: {yaml_vars_dir}")

    # 加载完YAML变量后，自动连接远程服务器
    load_remote_servers_from_yaml()


def load_yaml_variables(config):
    """加载YAML变量文件（pytest插件接口）

    从pytest配置对象中获取命令行参数并加载YAML变量。

    Args:
        config: pytest配置对象
    """
    # 获取命令行参数
    yaml_files = config.getoption('--yaml-vars')
    yaml_vars_dir = config.getoption('--yaml-vars-dir')
    project_root = config.rootdir

    # 调用通用加载函数
    load_yaml_variables_from_args(
        yaml_files=yaml_files,
        yaml_vars_dir=yaml_vars_dir,
        project_root=project_root
    )


def load_remote_servers_from_yaml():
    """从YAML配置中自动加载远程服务器

    检查YAML变量中是否包含remote_servers配置，如果有则自动连接这些服务器。
    """
    try:
        # 获取远程服务器配置
        remote_servers_config = yaml_vars.get_variable('remote_servers')
        if not remote_servers_config:
            
            return

        print(f"发现 {len(remote_servers_config)} 个远程服务器配置")

        # 导入远程关键字管理器
        from pytest_dsl.remote.keyword_client import remote_keyword_manager

        # 遍历配置并连接服务器
        for server_name, server_config in remote_servers_config.items():
            try:
                url = server_config.get('url')
                alias = server_config.get('alias', server_name)
                api_key = server_config.get('api_key')
                sync_config = server_config.get('sync_config')

                if not url:
                    print(f"跳过服务器 {server_name}: 缺少URL配置")
                    continue

                print(f"正在连接远程服务器: {server_name} ({url}) 别名: {alias}")

                # 注册远程服务器
                success = remote_keyword_manager.register_remote_server(
                    url=url,
                    alias=alias,
                    api_key=api_key,
                    sync_config=sync_config
                )

                if success:
                    print(f"成功连接到远程服务器: {server_name} ({url})")
                else:
                    print(f"连接远程服务器失败: {server_name} ({url})")

            except Exception as e:
                print(f"连接远程服务器 {server_name} 时发生错误: {str(e)}")

    except Exception as e:
        print(f"加载远程服务器配置时发生错误: {str(e)}")