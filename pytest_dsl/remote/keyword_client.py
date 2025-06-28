import xmlrpc.client
from functools import partial
import logging

from pytest_dsl.core.keyword_manager import keyword_manager, Parameter

# 配置日志
logger = logging.getLogger(__name__)


class RemoteKeywordClient:
    """远程关键字客户端，用于连接远程关键字服务器并执行关键字"""

    def __init__(self, url='http://localhost:8270/', api_key=None, alias=None,
                 sync_config=None):
        self.url = url
        self.server = xmlrpc.client.ServerProxy(url, allow_none=True)
        self.keyword_cache = {}
        self.param_mappings = {}  # 存储每个关键字的参数映射
        self.api_key = api_key
        self.alias = alias or url.replace('http://', '').replace(
            'https://', '').split(':')[0]

        # 变量传递配置（简化版）
        self.sync_config = sync_config or {
            'sync_global_vars': True,   # 连接时传递全局变量（g_开头）
            'sync_yaml_vars': True,     # 连接时传递YAML配置变量
            'yaml_sync_keys': None,     # 指定要同步的YAML键列表，None表示同步所有（除了排除的）
            'yaml_exclude_patterns': [  # 排除包含这些模式的YAML变量
                'private', 'remote_servers'  # 排除远程服务器配置避免循环
            ]
        }

    def connect(self):
        """连接到远程服务器并获取可用关键字"""
        try:
            print(f"RemoteKeywordClient: 正在连接到远程服务器 {self.url}")
            keyword_names = self.server.get_keyword_names()
            print(f"RemoteKeywordClient: 获取到 {len(keyword_names)} 个关键字")
            for name in keyword_names:
                self._register_remote_keyword(name)

            # 连接时传递变量到远程服务器
            self._send_initial_variables()

            logger.info(f"已连接到远程关键字服务器: {self.url}, 别名: {self.alias}")
            print(f"RemoteKeywordClient: 成功连接到远程服务器 {self.url}, "
                  f"别名: {self.alias}")
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

            # 尝试获取参数详细信息（包括默认值）
            param_details = []
            try:
                param_details = self.server.get_keyword_parameter_details(name)
            except Exception as e:
                print(f"获取关键字 {name} 的参数详细信息失败，使用基本信息: {e}")
                # 如果新方法不可用，使用旧的方式
                for param_name in param_names:
                    param_details.append({
                        'name': param_name,
                        'mapping': param_name,
                        'description': f'远程关键字参数: {param_name}',
                        'default': None
                    })

            print(f"注册远程关键字: {name}, 参数详情: {param_details}")

            # 创建参数列表
            parameters = []
            param_mapping = {}  # 为每个关键字创建参数映射

            for param_detail in param_details:
                param_name = param_detail['name']
                param_mapping_name = param_detail.get('mapping', param_name)
                param_desc = param_detail.get('description',
                                              f'远程关键字参数: {param_name}')
                param_default = param_detail.get('default')

                # 确保参数名称正确映射
                parameters.append({
                    'name': param_name,
                    'mapping': param_mapping_name,
                    'description': param_desc,
                    'default': param_default  # 添加默认值支持
                })
                # 添加到参数映射
                param_mapping[param_name] = param_mapping_name

            # 添加步骤名称参数，这是所有关键字都应该有的
            if not any(p['name'] == '步骤名称' for p in parameters):
                parameters.append({
                    'name': '步骤名称',
                    'mapping': 'step_name',
                    'description': '自定义的步骤名称，用于在报告中显示',
                    'default': None
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
                'defaults': {
                    p['mapping']: p['default'] for p in parameters
                    if p['default'] is not None
                },  # 添加默认值支持
                'remote': True,  # 标记为远程关键字
                'alias': self.alias,
                'original_name': name
            }

            # 缓存关键字信息
            self.keyword_cache[name] = {
                'parameters': param_names,  # 注意这里只缓存原始参数，不包括步骤名称
                'doc': doc,
                'param_details': param_details  # 缓存详细参数信息
            }
            # 保存参数映射
            self.param_mappings[name] = param_mapping

            logger.debug(f"已注册远程关键字: {remote_keyword_name}")
        except Exception as e:
            logger.error(f"注册远程关键字 {name} 失败: {str(e)}")

    def _execute_remote_keyword(self, **kwargs):
        """执行远程关键字"""
        name = kwargs.pop('name')

        # 在执行前同步最新的上下文变量
        self._sync_context_variables_before_execution(kwargs.get('context'))

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
            print("没有找到参数映射，使用原始参数名")

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
            return_data = result['return']

            # 处理新的返回格式
            if isinstance(return_data, dict):
                # 处理捕获的变量 - 这里需要访问本地上下文
                if 'captures' in return_data and return_data['captures']:
                    print(f"远程关键字捕获的变量: {return_data['captures']}")

                # 处理会话状态
                if ('session_state' in return_data and
                        return_data['session_state']):
                    print(f"远程关键字会话状态: {return_data['session_state']}")

                # 处理响应数据
                if 'response' in return_data and return_data['response']:
                    print("远程关键字响应数据: 已接收")

                # 检查是否为新的统一返回格式（包含captures等字段）
                if ('captures' in return_data or
                        'session_state' in return_data or
                        'metadata' in return_data):
                    # 返回完整的新格式，让DSL执行器处理变量捕获
                    return return_data
                elif 'result' in return_data:
                    # 返回主要结果，保持向后兼容
                    return return_data['result']
                else:
                    return return_data

            return return_data
        else:
            error_msg = result.get('error', '未知错误')
            traceback = '\n'.join(result.get('traceback', []))
            raise Exception(f"远程关键字执行失败: {error_msg}\n{traceback}")

    def _sync_context_variables_before_execution(self, context):
        """在执行远程关键字前同步最新的上下文变量

        Args:
            context: TestContext实例，如果为None则跳过同步
        """
        if context is None:
            return

        try:
            # 获取所有上下文变量
            context_variables = context.get_all_context_variables()

            if not context_variables:
                print("没有上下文变量需要同步")
                return

            # 使用统一的序列化工具进行变量过滤
            from pytest_dsl.core.serialization_utils import XMLRPCSerializer
            
            # 扩展排除模式
            exclude_patterns = self.sync_config.get('yaml_exclude_patterns', [
                'password', 'secret', 'token', 'credential', 'auth',
                'private', 'remote_servers'
            ])
            
            variables_to_sync = XMLRPCSerializer.filter_variables(
                context_variables, exclude_patterns)

            if variables_to_sync:
                # 调用远程服务器的变量同步接口
                try:
                    result = self.server.sync_variables_from_client(
                        variables_to_sync, self.api_key)
                    if result.get('status') == 'success':
                        print(f"✅ 实时同步 {len(variables_to_sync)} 个上下文变量到远程服务器")
                    else:
                        print(f"❌ 实时同步变量失败: {result.get('error', '未知错误')}")
                except Exception as e:
                    print(f"❌ 调用远程变量同步接口失败: {str(e)}")
            else:
                print("没有需要实时同步的变量")

        except Exception as e:
            logger.warning(f"实时变量同步失败: {str(e)}")
            print(f"❌ 实时变量同步失败: {str(e)}")

    def _collect_context_variables(self, context):
        """从TestContext收集所有变量（包括外部提供者变量）

        Args:
            context: TestContext实例

        Returns:
            dict: 包含所有上下文变量的字典
        """
        if context is None:
            return {}

        try:
            # 使用新的get_all_context_variables方法
            return context.get_all_context_variables()
        except Exception as e:
            logger.warning(f"收集上下文变量失败: {str(e)}")
            return {}

    def _send_initial_variables(self):
        """连接时发送初始变量到远程服务器"""
        try:
            variables_to_send = {}

            # 收集全局变量
            if self.sync_config.get('sync_global_vars', True):
                variables_to_send.update(self._collect_global_variables())

            # 收集YAML变量
            if self.sync_config.get('sync_yaml_vars', True):
                variables_to_send.update(self._collect_yaml_variables())

            if variables_to_send:
                # 使用统一的序列化工具进行变量过滤和转换
                from pytest_dsl.core.serialization_utils import (
                    XMLRPCSerializer
                )
                serializable_variables = XMLRPCSerializer.filter_variables(
                    variables_to_send)
                
                if serializable_variables:
                    try:
                        # 调用远程服务器的变量接收接口
                        result = self.server.sync_variables_from_client(
                            serializable_variables, self.api_key)
                        if result.get('status') == 'success':
                            print(f"成功传递 {len(serializable_variables)} "
                                  f"个变量到远程服务器")
                        else:
                            print(f"传递变量到远程服务器失败: "
                                  f"{result.get('error', '未知错误')}")
                    except Exception as e:
                        print(f"调用远程变量接口失败: {str(e)}")
                else:
                    print("没有可序列化的变量需要传递")
            else:
                print("没有需要传递的变量")

        except Exception as e:
            logger.warning(f"初始变量传递失败: {str(e)}")
            print(f"初始变量传递失败: {str(e)}")

    def _collect_global_variables(self):
        """收集全局变量"""
        from pytest_dsl.core.global_context import global_context
        variables = {}

        # 获取所有全局变量（包括g_开头的变量）
        try:
            # 这里需要访问全局上下文的内部存储
            # 由于GlobalContext使用文件存储，我们需要直接读取
            import json
            import os
            from filelock import FileLock

            storage_file = global_context._storage_file
            lock_file = global_context._lock_file

            if os.path.exists(storage_file):
                with FileLock(lock_file):
                    with open(storage_file, 'r', encoding='utf-8') as f:
                        stored_vars = json.load(f)
                        # 只同步g_开头的全局变量
                        global_vars = {
                            name: value for name, value in stored_vars.items() 
                            if name.startswith('g_')
                        }
                        if global_vars:
                            from pytest_dsl.core.serialization_utils import (
                                XMLRPCSerializer
                            )
                            filtered_global_vars = XMLRPCSerializer.filter_variables(
                                global_vars)
                            variables.update(filtered_global_vars)
        except Exception as e:
            logger.warning(f"收集全局变量失败: {str(e)}")

        return variables

    def _collect_yaml_variables(self):
        """收集YAML配置变量"""
        from pytest_dsl.core.yaml_vars import yaml_vars
        variables = {}

        try:
            # 获取所有YAML变量
            yaml_data = yaml_vars._variables
            if yaml_data:
                print(f"客户端YAML变量总数: {len(yaml_data)}")

                # 检查同步配置中是否指定了特定的键
                sync_keys = self.sync_config.get('yaml_sync_keys', None)
                exclude_patterns = self.sync_config.get(
                    'yaml_exclude_patterns', [
                        'password', 'secret', 'token', 'credential', 'auth',
                        'private', 'remote_servers'  # 排除远程服务器配置避免循环
                    ]
                )

                if sync_keys:
                    # 如果指定了特定键，只传递这些键，直接使用原始变量名
                    specific_vars = {
                        key: yaml_data[key] for key in sync_keys 
                        if key in yaml_data
                    }
                    if specific_vars:
                        from pytest_dsl.core.serialization_utils import (
                            XMLRPCSerializer
                        )
                        filtered_specific_vars = XMLRPCSerializer.filter_variables(
                            specific_vars)
                        variables.update(filtered_specific_vars)
                        for key in filtered_specific_vars:
                            print(f"传递指定YAML变量: {key}")
                else:
                    # 传递所有YAML变量，但排除敏感信息
                    from pytest_dsl.core.serialization_utils import (
                        XMLRPCSerializer
                    )
                    filtered_yaml_vars = XMLRPCSerializer.filter_variables(
                        yaml_data, exclude_patterns)
                    variables.update(filtered_yaml_vars)
                    for key in filtered_yaml_vars:
                        print(f"传递YAML变量: {key}")

        except Exception as e:
            logger.warning(f"收集YAML变量失败: {str(e)}")
            print(f"收集YAML变量失败: {str(e)}")

        return variables


# 远程关键字客户端管理器
class RemoteKeywordManager:
    """远程关键字客户端管理器，管理多个远程服务器连接"""

    def __init__(self):
        self.clients = {}  # 别名 -> 客户端实例

    def register_remote_server(self, url, alias, api_key=None,
                               sync_config=None):
        """注册远程关键字服务器

        Args:
            url: 服务器URL
            alias: 服务器别名
            api_key: API密钥(可选)
            sync_config: 变量同步配置(可选)

        Returns:
            bool: 是否成功连接
        """
        print(f"RemoteKeywordManager: 正在注册远程服务器 {url} 别名 {alias}")
        client = RemoteKeywordClient(url=url, api_key=api_key, alias=alias,
                                     sync_config=sync_config)
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
