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

            # 为HTTP请求关键字创建测试上下文
            from pytest_dsl.core.context import TestContext
            test_context = TestContext()

            # 添加context参数，这对于HTTP请求关键字是必需的
            exec_kwargs['context'] = test_context

            # 映射参数
            for param_name, param_value in args_dict.items():
                # 如果参数名在映射中，使用映射后的名称
                if param_name in mapping:
                    exec_kwargs[mapping[param_name]] = param_value
                else:
                    # 否则直接使用原始参数名
                    exec_kwargs[param_name] = param_value

                # 如果有保存响应参数，确保在上下文中创建该变量
                if param_name == '保存响应' and param_value:
                    test_context.set(param_value, {})

            # 执行关键字
            result = keyword_manager.execute(name, **exec_kwargs)

            # 如果有保存响应参数，从上下文中获取响应并返回
            if 'save_response' in exec_kwargs and exec_kwargs['save_response']:
                response_var = exec_kwargs['save_response']
                response_data = test_context.get(response_var)
                # 确保响应数据是可序列化的
                if response_data and not self._is_serializable(response_data):
                    # 尝试转换为可序列化的格式
                    if hasattr(response_data, '__dict__'):
                        response_data = response_data.__dict__
                    else:
                        response_data = str(response_data)
                # 更新结果中的响应数据
                if isinstance(result, dict):
                    result[response_var] = response_data
                else:
                    result = {response_var: response_data}

            # 处理不可序列化的结果
            if not self._is_serializable(result):
                result = str(result)

            return {
                'status': 'PASS',
                'return': result
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

    def _is_serializable(self, obj):
        """检查对象是否可以被序列化为JSON"""
        try:
            json.dumps(obj)
            return True
        except (TypeError, OverflowError):
            return False

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
