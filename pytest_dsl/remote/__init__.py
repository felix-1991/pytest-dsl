"""
Remote module for pytest-dsl.

This module provides remote keyword server functionality.
"""

__version__ = "0.16.1"

# 导出远程关键字管理器和相关功能
from .keyword_client import remote_keyword_manager, RemoteKeywordManager, RemoteKeywordClient
from .keyword_server import RemoteKeywordServer
from .variable_bridge import VariableBridge

# 导出便捷函数


def register_remote_server(url, alias, api_key=None, sync_config=None):
    """注册远程关键字服务器的便捷函数

    Args:
        url: 服务器URL
        alias: 服务器别名  
        api_key: API密钥(可选)
        sync_config: 变量同步配置(可选)

    Returns:
        bool: 是否成功连接
    """
    return remote_keyword_manager.register_remote_server(url, alias, api_key, sync_config)


def register_multiple_servers(servers_config):
    """批量注册远程服务器

    Args:
        servers_config: 服务器配置列表，每个配置包含url、alias等信息

    Returns:
        dict: 注册结果，键为alias，值为是否成功
    """
    results = {}
    for server_config in servers_config:
        if isinstance(server_config, dict):
            url = server_config.get('url')
            alias = server_config.get('alias')
            api_key = server_config.get('api_key')
            sync_config = server_config.get('sync_config')

            if url and alias:
                success = register_remote_server(
                    url, alias, api_key, sync_config)
                results[alias] = success

    return results


# 导出所有公共接口
__all__ = [
    # 核心类
    'remote_keyword_manager',
    'RemoteKeywordManager',
    'RemoteKeywordClient',
    'RemoteKeywordServer',
    'VariableBridge',

    # 便捷函数
    'register_remote_server',
    'register_multiple_servers',
]
