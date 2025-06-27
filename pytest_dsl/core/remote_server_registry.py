"""
远程服务器注册模块

提供独立的远程服务器注册功能，方便其他系统集成pytest-dsl时使用自己的变量系统。
这个模块不依赖于YAML配置，完全通过编程方式进行服务器注册。
"""

from typing import Dict, List, Optional, Any, Callable
import logging

logger = logging.getLogger(__name__)


class RemoteServerRegistry:
    """远程服务器注册器

    提供灵活的API用于注册和管理远程关键字服务器，
    支持自定义变量获取方式，方便第三方系统集成。
    """

    def __init__(self):
        self._variable_providers = []  # 变量提供者列表
        self._server_configs = []      # 服务器配置列表
        self._connection_callbacks = []  # 连接成功后的回调

    def add_variable_provider(self, provider: Callable[[], Dict[str, Any]]):
        """添加变量提供者

        变量提供者是一个无参数的可调用对象，返回字典形式的变量。
        这允许第三方系统提供自己的变量获取逻辑。

        Args:
            provider: 返回变量字典的可调用对象

        Examples:
            >>> def my_vars():
            ...     return {'api_key': 'secret', 'env': 'prod'}
            >>> registry.add_variable_provider(my_vars)
        """
        if callable(provider):
            self._variable_providers.append(provider)
        else:
            raise ValueError("变量提供者必须是可调用对象")

    def add_connection_callback(self, callback: Callable[[str, bool], None]):
        """添加连接回调

        连接回调会在每次连接远程服务器后被调用，
        无论连接成功还是失败。

        Args:
            callback: 接受(alias, success)参数的回调函数
        """
        if callable(callback):
            self._connection_callbacks.append(callback)
        else:
            raise ValueError("连接回调必须是可调用对象")

    def register_server(self,
                        url: str,
                        alias: str,
                        api_key: Optional[str] = None,
                        sync_global_vars: bool = True,
                        sync_custom_vars: bool = True,
                        exclude_patterns: Optional[List[str]] = None) -> bool:
        """注册单个远程服务器

        Args:
            url: 服务器URL
            alias: 服务器别名
            api_key: API密钥
            sync_global_vars: 是否同步全局变量
            sync_custom_vars: 是否同步自定义变量（通过变量提供者）
            exclude_patterns: 要排除的变量名模式列表

        Returns:
            bool: 是否连接成功
        """
        # 构建同步配置
        sync_config = {
            'sync_global_vars': sync_global_vars,
            'sync_yaml_vars': False,  # 不使用YAML变量
            'sync_custom_vars': sync_custom_vars,
            'exclude_patterns': exclude_patterns or ['password', 'secret', 'token']
        }

        # 收集要同步的变量
        variables_to_sync = {}

        if sync_custom_vars:
            variables_to_sync.update(self._collect_custom_variables())

        # 尝试连接
        success = self._connect_to_server(
            url, alias, api_key, sync_config, variables_to_sync)

        # 调用连接回调
        for callback in self._connection_callbacks:
            try:
                callback(alias, success)
            except Exception as e:
                logger.warning(f"连接回调执行失败: {e}")

        if success:
            # 保存配置以便后续使用
            self._server_configs.append({
                'url': url,
                'alias': alias,
                'api_key': api_key,
                'sync_config': sync_config
            })

        return success

    def register_servers_from_config(self, servers: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """从配置列表批量注册服务器

        Args:
            servers: 服务器配置列表，每个配置包含url、alias等字段

        Returns:
            dict: 注册结果，键为alias，值为结果详情字典

        Examples:
            >>> servers = [
            ...     {'url': 'http://server1:8270', 'alias': 'server1'},
            ...     {'url': 'http://server2:8270', 'alias': 'server2', 'api_key': 'secret'}
            ... ]
            >>> results = registry.register_servers_from_config(servers)
        """
        results = {}

        for server_config in servers:
            if not isinstance(server_config, dict):
                continue

            url = server_config.get('url')
            alias = server_config.get('alias')

            if not url or not alias:
                logger.warning(f"服务器配置缺少必要字段: {server_config}")
                results[alias or 'unknown'] = {
                    'success': False,
                    'url': url or 'unknown',
                    'alias': alias or 'unknown',
                    'error': '缺少必要字段'
                }
                continue

            api_key = server_config.get('api_key')
            sync_global_vars = server_config.get('sync_global_vars', True)
            sync_custom_vars = server_config.get('sync_custom_vars', True)
            exclude_patterns = server_config.get('exclude_patterns')

            success = self.register_server(
                url=url,
                alias=alias,
                api_key=api_key,
                sync_global_vars=sync_global_vars,
                sync_custom_vars=sync_custom_vars,
                exclude_patterns=exclude_patterns
            )

            results[alias] = {
                'success': success,
                'url': url,
                'alias': alias
            }

        return results

    def _collect_custom_variables(self) -> Dict[str, Any]:
        """收集自定义变量"""
        variables = {}

        for provider in self._variable_providers:
            try:
                provider_vars = provider()
                if isinstance(provider_vars, dict):
                    variables.update(provider_vars)
                else:
                    logger.warning(f"变量提供者返回了非字典类型: {type(provider_vars)}")
            except Exception as e:
                logger.warning(f"变量提供者执行失败: {e}")

        return variables

    def _connect_to_server(self,
                           url: str,
                           alias: str,
                           api_key: Optional[str],
                           sync_config: Dict[str, Any],
                           variables: Dict[str, Any]) -> bool:
        """连接到远程服务器"""
        try:
            # 导入远程关键字管理器
            from pytest_dsl.remote import remote_keyword_manager

            # 创建扩展的同步配置
            extended_sync_config = sync_config.copy()
            extended_sync_config['custom_variables'] = variables

            # 注册服务器
            success = remote_keyword_manager.register_remote_server(
                url=url,
                alias=alias,
                api_key=api_key,
                sync_config=extended_sync_config
            )

            if success:
                logger.info(f"成功连接到远程服务器: {alias} ({url})")
            else:
                logger.error(f"连接远程服务器失败: {alias} ({url})")

            return success

        except ImportError:
            logger.error("远程功能不可用，请检查依赖安装")
            return False
        except Exception as e:
            logger.error(f"连接远程服务器时发生错误: {e}")
            return False

    def get_registered_servers(self) -> List[Dict[str, Any]]:
        """获取已注册的服务器列表"""
        return self._server_configs.copy()

    def clear_variable_providers(self):
        """清空所有变量提供者"""
        self._variable_providers.clear()

    def clear_connection_callbacks(self):
        """清空所有连接回调"""
        self._connection_callbacks.clear()


# 创建全局注册器实例
remote_server_registry = RemoteServerRegistry()


# 便捷函数
def register_remote_server_with_variables(url: str,
                                          alias: str,
                                          variables: Dict[str, Any],
                                          api_key: Optional[str] = None) -> bool:
    """使用指定变量注册远程服务器的便捷函数

    Args:
        url: 服务器URL
        alias: 服务器别名
        variables: 要同步的变量字典
        api_key: API密钥

    Returns:
        bool: 是否连接成功
    """
    # 创建临时变量提供者
    def temp_provider():
        return variables

    # 临时添加变量提供者
    original_providers = remote_server_registry._variable_providers.copy()
    remote_server_registry._variable_providers = [temp_provider]

    try:
        return remote_server_registry.register_server(url, alias, api_key)
    finally:
        # 恢复原来的变量提供者
        remote_server_registry._variable_providers = original_providers


def create_database_variable_provider(connection_string: str):
    """创建数据库变量提供者示例

    这是一个示例函数，展示如何创建从数据库获取变量的提供者。
    实际使用时需要根据具体的数据库类型进行调整。

    Args:
        connection_string: 数据库连接字符串

    Returns:
        callable: 变量提供者函数
    """
    def database_provider():
        # 这里是示例代码，实际需要根据数据库类型实现
        # import sqlite3
        # conn = sqlite3.connect(connection_string)
        # cursor = conn.cursor()
        # cursor.execute("SELECT key, value FROM variables")
        # variables = dict(cursor.fetchall())
        # conn.close()
        # return variables

        return {
            'db_host': 'localhost',
            'db_port': '5432',
            'db_name': 'test_db'
        }

    return database_provider


def create_config_file_variable_provider(config_file_path: str):
    """创建配置文件变量提供者

    从JSON或其他配置文件读取变量。

    Args:
        config_file_path: 配置文件路径

    Returns:
        callable: 变量提供者函数
    """
    import json
    import os

    def config_file_provider():
        if not os.path.exists(config_file_path):
            return {}

        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                if config_file_path.endswith('.json'):
                    return json.load(f)
                else:
                    # 可以扩展支持其他格式
                    return {}
        except Exception as e:
            logger.warning(f"读取配置文件失败: {e}")
            return {}

    return config_file_provider
