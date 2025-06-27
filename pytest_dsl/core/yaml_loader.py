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
                                  project_root=None, environment=None,
                                  auto_load_default=None):
    """从命令行参数加载YAML变量

    Args:
        yaml_files: YAML文件列表
        yaml_vars_dir: YAML变量目录路径
        project_root: 项目根目录
        environment: 环境名称（用于hook加载）
        auto_load_default: 是否自动加载默认配置
                          None - 根据用户输入智能判断
                          True - 强制加载默认配置  
                          False - 不加载默认配置
    """
    # 智能判断是否应该加载默认配置
    if auto_load_default is None:
        # 如果用户指定了具体的YAML文件，不自动加载默认配置
        # 如果用户指定了具体的目录，也不自动加载默认配置
        user_specified_files = bool(yaml_files)
        user_specified_dir = bool(yaml_vars_dir)
        auto_load_default = not (user_specified_files or user_specified_dir)

        if not auto_load_default:
            print("🎯 检测到用户指定了配置，跳过默认配置自动加载")
        else:
            print("📁 未指定配置，将自动加载默认配置目录")

    # 首先尝试通过hook加载变量（最高优先级）
    hook_variables = _load_variables_through_hooks(
        project_root=project_root, environment=environment)

    if hook_variables:
        print(f"🔌 通过Hook加载了 {len(hook_variables)} 个变量")
        # 将hook变量加载到yaml_vars中
        yaml_vars._variables.update(hook_variables)

    # 加载用户指定的YAML文件（第二优先级）
    if yaml_files:
        yaml_vars.load_yaml_files(yaml_files)
        print(f"📄 已加载用户指定的YAML文件: {', '.join(yaml_files)}")

    # 加载用户指定的目录中的YAML文件（第三优先级）
    if yaml_vars_dir:
        if Path(yaml_vars_dir).exists():
            yaml_vars.load_from_directory(yaml_vars_dir)
            print(f"📂 已加载用户指定的YAML目录: {yaml_vars_dir}")
            loaded_files = yaml_vars.get_loaded_files()
            if loaded_files:
                # 过滤出当前目录的文件
                dir_files = [f for f in loaded_files if Path(
                    f).parent == Path(yaml_vars_dir)]
                if dir_files:
                    print(f"   目录中加载的文件: {', '.join(dir_files)}")
        else:
            print(f"⚠️ 用户指定的YAML目录不存在: {yaml_vars_dir}")

    # 自动加载默认配置（最低优先级，仅在用户未指定配置时）
    if auto_load_default:
        default_yaml_vars_dir = None
        if project_root:
            # 默认使用项目根目录下的config目录
            default_yaml_vars_dir = str(Path(project_root) / 'config')
            print(f"🏠 使用默认YAML变量目录: {default_yaml_vars_dir}")

        if default_yaml_vars_dir and Path(default_yaml_vars_dir).exists():
            yaml_vars.load_from_directory(default_yaml_vars_dir)
            print(f"📁 已加载默认YAML变量目录: {default_yaml_vars_dir}")
            loaded_files = yaml_vars.get_loaded_files()
            if loaded_files:
                # 过滤出默认目录的文件
                dir_files = [f for f in loaded_files if Path(
                    f).parent == Path(default_yaml_vars_dir)]
                if dir_files:
                    print(f"   默认目录中加载的文件: {', '.join(dir_files)}")
        elif default_yaml_vars_dir:
            print(f"📁 默认YAML变量目录不存在: {default_yaml_vars_dir}")

    # 显示最终加载的变量汇总
    all_loaded_files = yaml_vars.get_loaded_files()
    if all_loaded_files:
        print(f"✅ 变量加载完成，共加载 {len(all_loaded_files)} 个文件")
        if len(yaml_vars._variables) > 0:
            print(f"📊 总共加载了 {len(yaml_vars._variables)} 个变量")
    else:
        print("⚠️ 未加载任何YAML变量文件")

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


def load_remote_servers_from_yaml(variable_source=None):
    """从YAML变量中加载远程服务器配置

    Args:
        variable_source: 自定义变量源，如果不提供则使用全局上下文
    """
    try:
        from pytest_dsl.remote.keyword_client import remote_keyword_manager

        # 支持自定义变量源
        if variable_source and callable(variable_source):
            variables = variable_source()
            remote_servers = variables.get(
                'remote_servers') if isinstance(variables, dict) else None
        else:
            # 使用默认的全局上下文
            from pytest_dsl.core.global_context import global_context
            remote_servers = global_context.get_variable('remote_servers')

        if not remote_servers:
            return []

        # 支持两种格式：数组和字典
        server_configs = []

        if isinstance(remote_servers, list):
            # 数组格式: [{'url': '...', 'alias': '...'}, ...]
            server_configs = remote_servers
            print(f"发现 {len(remote_servers)} 个远程服务器配置（数组格式）")
        elif isinstance(remote_servers, dict):
            # 字典格式: {'server1': {'url': '...', 'alias': '...'}, ...}
            for server_name, server_config in remote_servers.items():
                if isinstance(server_config, dict):
                    # 如果没有指定alias，使用键名作为alias
                    if 'alias' not in server_config:
                        server_config = server_config.copy()
                        server_config['alias'] = server_name
                    server_configs.append(server_config)
            print(f"发现 {len(server_configs)} 个远程服务器配置（字典格式）")
        else:
            print(
                f"警告：remote_servers配置格式不支持，期望数组或字典，得到 {type(remote_servers)}")
            return []

        results = []

        # 注册远程服务器
        for server_config in server_configs:
            if isinstance(server_config, dict):
                url = server_config.get('url')
                alias = server_config.get('alias')
                api_key = server_config.get('api_key')
                sync_config = server_config.get('sync_config')

                if url and alias:
                    print(f"自动连接远程服务器: {alias} -> {url}")
                    success = remote_keyword_manager.register_remote_server(
                        url, alias, api_key=api_key, sync_config=sync_config
                    )
                    if success:
                        print(f"✓ 远程服务器 {alias} 连接成功")
                    else:
                        print(f"✗ 远程服务器 {alias} 连接失败")

                    results.append(
                        {'alias': alias, 'url': url, 'success': success})
                else:
                    print(f"警告：服务器配置缺少必要字段 url 或 alias: {server_config}")

        return results

    except ImportError:
        # 如果远程功能不可用，跳过
        return []
    except Exception as e:
        print(f"自动连接远程服务器时出现警告: {e}")
        return []


def register_remote_servers_from_config(servers_config, variable_providers=None):
    """从配置注册远程服务器的独立函数

    这个函数可以被其他系统独立调用，不依赖YAML配置。

    Args:
        servers_config: 服务器配置列表或单个配置
        variable_providers: 变量提供者列表，用于同步自定义变量

    Returns:
        dict: 注册结果

    Examples:
        >>> # 单个服务器
        >>> config = {'url': 'http://server:8270', 'alias': 'test'}
        >>> result = register_remote_servers_from_config(config)

        >>> # 多个服务器
        >>> configs = [
        ...     {'url': 'http://server1:8270', 'alias': 'server1'},
        ...     {'url': 'http://server2:8270', 'alias': 'server2'}
        ... ]
        >>> results = register_remote_servers_from_config(configs)

        >>> # 带变量提供者
        >>> def my_vars():
        ...     return {'env': 'prod', 'api_key': 'secret'}
        >>> results = register_remote_servers_from_config(configs, [my_vars])
    """
    try:
        from pytest_dsl.core.remote_server_registry import remote_server_registry

        # 如果有变量提供者，先添加它们
        if variable_providers:
            remote_server_registry.clear_variable_providers()
            for provider in variable_providers:
                if callable(provider):
                    remote_server_registry.add_variable_provider(provider)

        # 确保servers_config是列表
        if isinstance(servers_config, dict):
            servers_config = [servers_config]
        elif not isinstance(servers_config, list):
            raise ValueError("servers_config必须是字典或字典列表")

        # 使用注册器批量注册
        return remote_server_registry.register_servers_from_config(servers_config)

    except ImportError:
        print("远程功能不可用，请检查依赖安装")
        return {}
    except Exception as e:
        print(f"注册远程服务器时发生错误: {e}")
        return {}
