import xmlrpc.server
from functools import partial
import inspect
import json
import sys
import traceback

from pytest_dsl.core.keyword_manager import keyword_manager

class RemoteKeywordServer:
    """远程关键字服务器，提供关键字的远程调用能力"""

    def __init__(self, host='localhost', port=8270, api_key=None):
        self.host = host
        self.port = port
        self.server = None
        self.api_key = api_key

        # 变量存储
        self.shared_variables = {}  # 存储共享变量

        # 注册内置关键字
        self._register_builtin_keywords()

    def _register_builtin_keywords(self):
        """注册所有内置关键字"""
        # 确保所有内置关键字都已注册到keyword_manager
        # 这里不需要显式导入，因为在启动时已经导入了所有关键字模块
        print(f"已加载内置关键字，可用关键字数量: {len(keyword_manager._keywords)}")

    def start(self):
        """启动远程关键字服务器"""
        self.server = xmlrpc.server.SimpleXMLRPCServer((self.host, self.port), allow_none=True)
        self.server.register_introspection_functions()

        # 注册核心方法
        self.server.register_function(self.get_keyword_names)
        self.server.register_function(self.run_keyword)
        self.server.register_function(self.get_keyword_arguments)
        self.server.register_function(self.get_keyword_documentation)
        self.server.register_function(self.authenticate)

        # 注册变量同步方法
        self.server.register_function(self.sync_variables_from_client)
        self.server.register_function(self.get_variables_for_client)
        self.server.register_function(self.set_shared_variable)
        self.server.register_function(self.get_shared_variable)
        self.server.register_function(self.list_shared_variables)

        print(f"远程关键字服务器已启动，监听地址: {self.host}:{self.port}")
        self.server.serve_forever()

    def authenticate(self, api_key):
        """验证API密钥"""
        if not self.api_key:
            return True
        return api_key == self.api_key

    def get_keyword_names(self):
        """获取所有可用的关键字名称"""
        return list(keyword_manager._keywords.keys())

    def run_keyword(self, name, args_dict, api_key=None):
        """执行关键字并返回结果

        Args:
            name: 关键字名称
            args_dict: 关键字参数字典
            api_key: API密钥(可选)

        Returns:
            dict: 包含执行结果的字典，格式为:
                {
                    'status': 'PASS' 或 'FAIL',
                    'return': 返回值 (如果成功),
                    'error': 错误信息 (如果失败),
                    'traceback': 错误堆栈 (如果失败)
                }
        """
        # 验证API密钥
        if self.api_key and not self.authenticate(api_key):
            return {
                'status': 'FAIL',
                'error': '认证失败：无效的API密钥',
                'traceback': []
            }

        try:
            # 确保参数是字典格式
            if not isinstance(args_dict, dict):
                args_dict = json.loads(args_dict) if isinstance(args_dict, str) else {}

            # 获取关键字信息
            keyword_info = keyword_manager.get_keyword_info(name)
            if not keyword_info:
                raise Exception(f"未注册的关键字: {name}")

            # 获取参数映射
            mapping = keyword_info.get('mapping', {})

            # 准备执行参数
            exec_kwargs = {}

            # 添加默认的步骤名称
            exec_kwargs['step_name'] = name

            # 创建测试上下文（所有关键字都需要）
            from pytest_dsl.core.context import TestContext
            test_context = TestContext()
            exec_kwargs['context'] = test_context

            # 映射参数（通用逻辑）
            for param_name, param_value in args_dict.items():
                if param_name in mapping:
                    exec_kwargs[mapping[param_name]] = param_value
                else:
                    exec_kwargs[param_name] = param_value

            # 执行关键字
            result = keyword_manager.execute(name, **exec_kwargs)

            # 处理返回结果
            return_data = self._process_keyword_result(result, test_context)

            return {
                'status': 'PASS',
                'return': return_data
            }
        except Exception as e:
            exc_type, exc_value, exc_tb = sys.exc_info()
            return {
                'status': 'FAIL',
                'error': str(e),
                'traceback': traceback.format_exception(exc_type, exc_value, exc_tb)
            }

    def get_keyword_arguments(self, name):
        """获取关键字的参数信息"""
        keyword_info = keyword_manager.get_keyword_info(name)
        if not keyword_info:
            return []

        return [param.name for param in keyword_info['parameters']]

    def get_keyword_documentation(self, name):
        """获取关键字的文档信息"""
        keyword_info = keyword_manager.get_keyword_info(name)
        if not keyword_info:
            return ""

        func = keyword_info['func']
        return inspect.getdoc(func) or ""

    def _process_keyword_result(self, result, test_context):
        """处理关键字执行结果，确保可序列化并提取上下文变量

        Args:
            result: 关键字执行结果
            test_context: 测试上下文

        Returns:
            处理后的结果
        """
        # 如果结果已经是新格式（包含captures等），直接返回
        if isinstance(result, dict) and ('captures' in result or 'session_state' in result):
            # 确保结果可序列化
            return self._ensure_serializable(result)

        # 对于传统格式的结果，包装成新格式
        processed_result = {
            "result": result,
            "captures": {},
            "session_state": {},
            "metadata": {}
        }

        # 从上下文中提取可能的变量（这是为了向后兼容）
        # 注意：这只是一个备用方案，新的关键字应该主动返回所需数据
        if hasattr(test_context, '_variables'):
            # 只提取在执行过程中新增的变量
            processed_result["captures"] = dict(test_context._variables)

        return self._ensure_serializable(processed_result)

    def _ensure_serializable(self, obj):
        """确保对象可以被序列化为JSON"""
        if self._is_serializable(obj):
            return obj

        # 如果不能序列化，尝试转换
        if isinstance(obj, dict):
            serializable_dict = {}
            for key, value in obj.items():
                serializable_dict[key] = self._ensure_serializable(value)
            return serializable_dict
        elif isinstance(obj, (list, tuple)):
            return [self._ensure_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            return self._ensure_serializable(obj.__dict__)
        else:
            return str(obj)

    def _is_serializable(self, obj):
        """检查对象是否可以被序列化为JSON"""
        try:
            json.dumps(obj)
            return True
        except (TypeError, OverflowError):
            return False

    def sync_variables_from_client(self, variables, api_key=None):
        """接收客户端同步的变量

        Args:
            variables: 客户端发送的变量字典
            api_key: API密钥(可选)

        Returns:
            dict: 同步结果
        """
        # 验证API密钥
        if self.api_key and not self.authenticate(api_key):
            return {
                'status': 'error',
                'error': '认证失败：无效的API密钥'
            }

        try:
            # 更新共享变量
            for name, value in variables.items():
                self.shared_variables[name] = value
                print(f"接收到客户端变量: {name}")

            return {
                'status': 'success',
                'message': f'成功同步 {len(variables)} 个变量'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': f'同步变量失败: {str(e)}'
            }

    def get_variables_for_client(self, api_key=None):
        """获取要发送给客户端的变量

        Args:
            api_key: API密钥(可选)

        Returns:
            dict: 变量数据
        """
        # 验证API密钥
        if self.api_key and not self.authenticate(api_key):
            return {
                'status': 'error',
                'error': '认证失败：无效的API密钥'
            }

        try:
            return {
                'status': 'success',
                'variables': self.shared_variables.copy()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': f'获取变量失败: {str(e)}'
            }

    def set_shared_variable(self, name, value, api_key=None):
        """设置共享变量

        Args:
            name: 变量名
            value: 变量值
            api_key: API密钥(可选)

        Returns:
            dict: 设置结果
        """
        # 验证API密钥
        if self.api_key and not self.authenticate(api_key):
            return {
                'status': 'error',
                'error': '认证失败：无效的API密钥'
            }

        try:
            self.shared_variables[name] = value
            print(f"设置共享变量: {name} = {value}")
            return {
                'status': 'success',
                'message': f'成功设置变量 {name}'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': f'设置变量失败: {str(e)}'
            }

    def get_shared_variable(self, name, api_key=None):
        """获取共享变量

        Args:
            name: 变量名
            api_key: API密钥(可选)

        Returns:
            dict: 变量值或错误信息
        """
        # 验证API密钥
        if self.api_key and not self.authenticate(api_key):
            return {
                'status': 'error',
                'error': '认证失败：无效的API密钥'
            }

        try:
            if name in self.shared_variables:
                return {
                    'status': 'success',
                    'value': self.shared_variables[name]
                }
            else:
                return {
                    'status': 'error',
                    'error': f'变量 {name} 不存在'
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': f'获取变量失败: {str(e)}'
            }

    def list_shared_variables(self, api_key=None):
        """列出所有共享变量

        Args:
            api_key: API密钥(可选)

        Returns:
            dict: 变量列表
        """
        # 验证API密钥
        if self.api_key and not self.authenticate(api_key):
            return {
                'status': 'error',
                'error': '认证失败：无效的API密钥'
            }

        try:
            return {
                'status': 'success',
                'variables': list(self.shared_variables.keys()),
                'count': len(self.shared_variables)
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': f'列出变量失败: {str(e)}'
            }

def main():
    """启动远程关键字服务器的主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='启动pytest-dsl远程关键字服务器')
    parser.add_argument('--host', default='localhost', help='服务器主机名')
    parser.add_argument('--port', type=int, default=8270, help='服务器端口')
    parser.add_argument('--api-key', help='API密钥，用于认证')

    args = parser.parse_args()

    server = RemoteKeywordServer(host=args.host, port=args.port, api_key=args.api_key)
    server.start()

if __name__ == '__main__':
    main()
