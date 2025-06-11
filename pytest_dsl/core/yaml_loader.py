"""YAML变量加载器模块

该模块负责处理YAML变量文件的加载和管理，支持从命令行参数加载单个文件或目录。
同时支持通过hook机制从外部系统动态加载变量。
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


def load_yaml_variables_from_args(yaml_files=None, yaml_vars_dir=None,
                                  project_root=None, environment=None):
    """从参数加载YAML变量文件（通用函数）

    Args:
        yaml_files: YAML文件列表
        yaml_vars_dir: YAML变量目录路径
        project_root: 项目根目录（用于默认config目录）
        environment: 环境名称（用于hook加载）
    """
    # 首先尝试通过hook加载变量
    hook_variables = _load_variables_through_hooks(
        project_root=project_root, environment=environment)

    if hook_variables:
        print(f"通过Hook加载了 {len(hook_variables)} 个变量")
        # 将hook变量加载到yaml_vars中
        yaml_vars._variables.update(hook_variables)

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
                dir_files = [f for f in loaded_files if Path(
                    f).parent == Path(yaml_vars_dir)]
                if dir_files:
                    print(f"目录中加载的文件: {', '.join(dir_files)}")
            else:
                print(f"加载的文件: {', '.join(loaded_files)}")
    elif yaml_vars_dir:
        print(f"YAML变量目录不存在: {yaml_vars_dir}")

    # 加载完YAML变量后，自动连接远程服务器
    load_remote_servers_from_yaml()


def _load_variables_through_hooks(project_root=None, environment=None):
    """通过hook机制加载变量

    Args:
        project_root: 项目根目录
        environment: 环境名称

    Returns:
        dict: 通过hook加载的变量字典
    """
    try:
        from .hook_manager import hook_manager

        # 确保hook管理器已初始化
        hook_manager.initialize()

        # 如果没有已注册的插件，直接返回
        if not hook_manager.get_plugins():
            return {}

        # 提取project_id（如果可以从项目根目录推断）
        project_id = None
        if project_root:
            # 可以根据项目结构推断project_id，这里暂时不实现
            pass

        # 通过hook加载变量
        hook_variables = {}

        # 调用dsl_load_variables hook
        try:
            variable_results = hook_manager.pm.hook.dsl_load_variables(
                project_id=project_id,
                environment=environment,
                filters={}
            )

            # 合并所有hook返回的变量
            for result in variable_results:
                if result and isinstance(result, dict):
                    hook_variables.update(result)

        except Exception as e:
            print(f"通过Hook加载变量时出现警告: {e}")

        # 列出变量源（用于调试）
        try:
            source_results = hook_manager.pm.hook.dsl_list_variable_sources(
                project_id=project_id
            )

            sources = []
            for result in source_results:
                if result and isinstance(result, list):
                    sources.extend(result)

            if sources:
                print(f"发现 {len(sources)} 个变量源")
                for source in sources:
                    source_name = source.get('name', '未知')
                    source_type = source.get('type', '未知')
                    print(f"  - {source_name} ({source_type})")

        except Exception as e:
            print(f"列出变量源时出现警告: {e}")

        # 验证变量（如果有变量的话）
        if hook_variables:
            try:
                validation_results = hook_manager.pm.hook.dsl_validate_variables(
                    variables=hook_variables,
                    project_id=project_id
                )

                validation_errors = []
                for result in validation_results:
                    if result and isinstance(result, list):
                        validation_errors.extend(result)

                if validation_errors:
                    print(f"变量验证发现 {len(validation_errors)} 个问题:")
                    for error in validation_errors:
                        print(f"  - {error}")

            except Exception as e:
                print(f"验证变量时出现警告: {e}")

        return hook_variables

    except ImportError:
        # 如果没有安装pluggy或hook_manager不可用，跳过hook加载
        return {}
    except Exception as e:
        print(f"Hook变量加载失败: {e}")
        return {}


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

    # 尝试从环境变量获取环境名称
    environment = os.environ.get(
        'PYTEST_DSL_ENVIRONMENT') or os.environ.get('ENVIRONMENT')

    # 调用通用加载函数
    load_yaml_variables_from_args(
        yaml_files=yaml_files,
        yaml_vars_dir=yaml_vars_dir,
        project_root=project_root,
        environment=environment
    )


def load_remote_servers_from_yaml():
    """从YAML变量中加载远程服务器配置"""
    try:
        from pytest_dsl.remote.keyword_client import remote_keyword_manager

        # 获取远程服务器配置
        remote_servers = yaml_vars.get_variable('remote_servers')
        if not remote_servers:
            return

        print(f"发现 {len(remote_servers)} 个远程服务器配置")

        # 注册远程服务器
        for server_config in remote_servers:
            if isinstance(server_config, dict):
                url = server_config.get('url')
                alias = server_config.get('alias')
                api_key = server_config.get('api_key')

                if url and alias:
                    print(f"自动连接远程服务器: {alias} -> {url}")
                    success = remote_keyword_manager.register_remote_server(
                        url, alias, api_key=api_key
                    )
                    if success:
                        print(f"✓ 远程服务器 {alias} 连接成功")
                    else:
                        print(f"✗ 远程服务器 {alias} 连接失败")

    except ImportError:
        # 如果远程功能不可用，跳过
        pass
    except Exception as e:
        print(f"自动连接远程服务器时出现警告: {e}")
