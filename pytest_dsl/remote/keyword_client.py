import xmlrpc.client
import json
from functools import partial
import logging

from pytest_dsl.core.keyword_manager import keyword_manager, Parameter

# 配置日志
logger = logging.getLogger(__name__)

class RemoteKeywordClient:
    """远程关键字客户端，用于连接远程关键字服务器并执行关键字"""

    def __init__(self, url='http://localhost:8270/', api_key=None, alias=None):
        self.url = url
        self.server = xmlrpc.client.ServerProxy(url, allow_none=True)
        self.keyword_cache = {}
        self.param_mappings = {}  # 存储每个关键字的参数映射
        self.api_key = api_key
        self.alias = alias or url.replace('http://', '').replace('https://', '').split(':')[0]

    def connect(self):
        """连接到远程服务器并获取可用关键字"""
        try:
            print(f"RemoteKeywordClient: 正在连接到远程服务器 {self.url}")
            keyword_names = self.server.get_keyword_names()
            print(f"RemoteKeywordClient: 获取到 {len(keyword_names)} 个关键字")
            for name in keyword_names:
                self._register_remote_keyword(name)
            logger.info(f"已连接到远程关键字服务器: {self.url}, 别名: {self.alias}")
            print(f"RemoteKeywordClient: 成功连接到远程服务器 {self.url}, 别名: {self.alias}")
            return True
        except Exception as e:
            error_msg = f"连接远程关键字服务器失败: {str(e)}"
            logger.error(error_msg)
            print(f"RemoteKeywordClient: {error_msg}")
            return False

    def _register_remote_keyword(self, name):
        """注册远程关键字到本地关键字管理器"""
        # 获取关键字参数信息
        try:
            param_names = self.server.get_keyword_arguments(name)
            doc = self.server.get_keyword_documentation(name)

            print(f"注册远程关键字: {name}, 参数: {param_names}")

            # 创建参数列表
            parameters = []
            param_mapping = {}  # 为每个关键字创建参数映射

            for param_name in param_names:
                # 确保参数名称正确映射
                # 这里我们保持原始参数名称，但在执行时会进行正确映射
                parameters.append({
                    'name': param_name,
                    'mapping': param_name,  # 保持原始参数名称
                    'description': f'远程关键字参数: {param_name}'
                })
                # 添加到参数映射
                param_mapping[param_name] = param_name

            # 添加步骤名称参数，这是所有关键字都应该有的
            if not any(p['name'] == '步骤名称' for p in parameters):
                parameters.append({
                    'name': '步骤名称',
                    'mapping': 'step_name',
                    'description': '自定义的步骤名称，用于在报告中显示'
                })
                param_mapping['步骤名称'] = 'step_name'

            # 创建远程关键字执行函数
            remote_func = partial(self._execute_remote_keyword, name=name)
            remote_func.__doc__ = doc

            # 注册到关键字管理器，使用别名前缀
            remote_keyword_name = f"{self.alias}|{name}"
            keyword_manager._keywords[remote_keyword_name] = {
                'func': remote_func,
                'mapping': {p['name']: p['mapping'] for p in parameters},
                'parameters': [Parameter(**p) for p in parameters],
                'remote': True,  # 标记为远程关键字
                'alias': self.alias,
                'original_name': name
            }

            # 缓存关键字信息
            self.keyword_cache[name] = {
                'parameters': param_names,  # 注意这里只缓存原始参数，不包括步骤名称
                'doc': doc
            }

            # 保存参数映射
            self.param_mappings[name] = param_mapping

            logger.debug(f"已注册远程关键字: {remote_keyword_name}")
        except Exception as e:
            logger.error(f"注册远程关键字 {name} 失败: {str(e)}")

    def _execute_remote_keyword(self, **kwargs):
        """执行远程关键字"""
        name = kwargs.pop('name')

        # 移除context参数，因为它不能被序列化
        if 'context' in kwargs:
            kwargs.pop('context', None)

        # 移除step_name参数，这是自动添加的，不需要传递给远程服务器
        if 'step_name' in kwargs:
            kwargs.pop('step_name', None)

        # 打印调试信息
        print(f"远程关键字调用: {name}, 参数: {kwargs}")

        # 创建反向映射字典，用于检查参数是否已经映射
        reverse_mapping = {}

        # 使用动态注册的参数映射
        if name in self.param_mappings:
            param_mapping = self.param_mappings[name]
            print(f"使用动态参数映射: {param_mapping}")
            for cn_name, en_name in param_mapping.items():
                reverse_mapping[en_name] = cn_name
        else:
            # 如果没有任何映射，使用原始参数名
            param_mapping = None
            print(f"没有找到参数映射，使用原始参数名")

        # 映射参数名称
        mapped_kwargs = {}
        if param_mapping:
            for k, v in kwargs.items():
                if k in param_mapping:
                    mapped_key = param_mapping[k]
                    mapped_kwargs[mapped_key] = v
                    print(f"参数映射: {k} -> {mapped_key} = {v}")
                else:
                    mapped_kwargs[k] = v
        else:
            mapped_kwargs = kwargs

        # 确保参数名称正确映射
        # 获取关键字的参数信息
        if name in self.keyword_cache:
            param_names = self.keyword_cache[name]['parameters']
            print(f"远程关键字 {name} 的参数列表: {param_names}")

            # 不再显示警告信息，因为参数已经在服务器端正确处理
            # 服务器端会使用默认值或者报错，客户端不需要重复警告

        # 执行远程调用
        # 检查是否需要传递API密钥
        if self.api_key:
            result = self.server.run_keyword(name, mapped_kwargs, self.api_key)
        else:
            result = self.server.run_keyword(name, mapped_kwargs)

        print(f"远程关键字执行结果: {result}")

        if result['status'] == 'PASS':
            return result['return']
        else:
            error_msg = result.get('error', '未知错误')
            traceback = '\n'.join(result.get('traceback', []))
            raise Exception(f"远程关键字执行失败: {error_msg}\n{traceback}")

# 远程关键字客户端管理器
class RemoteKeywordManager:
    """远程关键字客户端管理器，管理多个远程服务器连接"""

    def __init__(self):
        self.clients = {}  # 别名 -> 客户端实例

    def register_remote_server(self, url, alias, api_key=None):
        """注册远程关键字服务器

        Args:
            url: 服务器URL
            alias: 服务器别名
            api_key: API密钥(可选)

        Returns:
            bool: 是否成功连接
        """
        print(f"RemoteKeywordManager: 正在注册远程服务器 {url} 别名 {alias}")
        client = RemoteKeywordClient(url=url, api_key=api_key, alias=alias)
        success = client.connect()

        if success:
            print(f"RemoteKeywordManager: 成功连接到远程服务器 {url}")
            self.clients[alias] = client
        else:
            print(f"RemoteKeywordManager: 连接远程服务器 {url} 失败")

        return success

    def get_client(self, alias):
        """获取指定别名的客户端实例"""
        return self.clients.get(alias)

    def execute_remote_keyword(self, alias, keyword_name, **kwargs):
        """执行远程关键字

        Args:
            alias: 服务器别名
            keyword_name: 关键字名称
            **kwargs: 关键字参数

        Returns:
            执行结果
        """
        client = self.get_client(alias)
        if not client:
            raise Exception(f"未找到别名为 {alias} 的远程服务器")

        return client._execute_remote_keyword(name=keyword_name, **kwargs)

# 创建全局远程关键字管理器实例
remote_keyword_manager = RemoteKeywordManager()
