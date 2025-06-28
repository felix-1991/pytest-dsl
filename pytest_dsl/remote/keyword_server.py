import xmlrpc.server
import inspect
import json
import sys
import traceback
import signal
import atexit
import threading
import time

from pytest_dsl.core.keyword_manager import keyword_manager
from pytest_dsl.remote.hook_manager import hook_manager, HookType


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

        # 注册关闭信号处理
        self._register_shutdown_handlers()

    def _register_builtin_keywords(self):
        """注册所有内置关键字，复用本地模式的加载逻辑"""
        from pytest_dsl.core.plugin_discovery import (
            load_all_plugins, scan_local_keywords
        )

        # 0. 首先加载内置关键字模块（确保内置关键字被注册）
        print("正在加载内置关键字...")
        try:
            import pytest_dsl.keywords
            print("内置关键字模块加载完成")
        except ImportError as e:
            print(f"加载内置关键字模块失败: {e}")

        # 1. 加载所有已安装的关键字插件（与本地模式一致）
        print("正在加载第三方关键字插件...")
        load_all_plugins()

        # 2. 扫描本地keywords目录中的关键字（与本地模式一致）
        print("正在扫描本地关键字...")
        scan_local_keywords()

        print(f"关键字加载完成，可用关键字数量: {len(keyword_manager._keywords)}")

    def _register_shutdown_handlers(self):
        """注册关闭信号处理器"""
        def shutdown_handler(signum, frame):
            if hasattr(self, '_shutdown_called') and self._shutdown_called:
                return  # 避免重复处理信号
            print(f"接收到信号 {signum}，正在关闭服务器...")

            # 在新线程中执行关闭逻辑，避免阻塞信号处理器
            shutdown_thread = threading.Thread(
                target=self._shutdown_in_thread, daemon=True)
            shutdown_thread.start()

        # 保存信号处理器引用
        self._shutdown_handler = shutdown_handler

        # 只在主线程中注册信号处理器
        try:
            signal.signal(signal.SIGINT, shutdown_handler)
            signal.signal(signal.SIGTERM, shutdown_handler)
        except ValueError:
            # 如果不在主线程中，跳过信号处理器注册
            print("警告: 无法在非主线程中注册信号处理器")

        # 注册atexit处理器
        atexit.register(self.shutdown)

    def _shutdown_in_thread(self):
        """在独立线程中执行关闭逻辑"""
        if hasattr(self, '_shutdown_called') and self._shutdown_called:
            return  # 避免重复调用
        self._shutdown_called = True

        print("正在执行服务器关闭流程...")

        # 执行关闭hook
        try:
            hook_manager.execute_hooks(
                HookType.SERVER_SHUTDOWN,
                server=self,
                shared_variables=self.shared_variables
            )
        except Exception as e:
            print(f"执行关闭hook时出错: {e}")

        # 关闭XML-RPC服务器
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
                print("服务器已关闭")
            except Exception as e:
                print(f"关闭服务器时出错: {e}")

        print("服务器关闭完成")

        # 给主线程一点时间完成清理
        time.sleep(0.1)

        # 强制退出
        import os
        os._exit(0)

    def start(self):
        """启动远程关键字服务器"""
        try:
            self.server = xmlrpc.server.SimpleXMLRPCServer(
                (self.host, self.port), allow_none=True)
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"端口 {self.port} 已被占用，请使用其他端口或关闭占用该端口的进程")
                return
            else:
                raise

        # 执行启动前的hook
        hook_manager.execute_hooks(
            HookType.SERVER_STARTUP,
            server=self,
            shared_variables=self.shared_variables,
            host=self.host,
            port=self.port
        )
        self.server.register_introspection_functions()

        # 注册核心方法
        self.server.register_function(self.get_keyword_names)
        self.server.register_function(self.run_keyword)
        self.server.register_function(self.get_keyword_arguments)
        self.server.register_function(self.get_keyword_parameter_details)
        self.server.register_function(self.get_keyword_documentation)
        self.server.register_function(self.authenticate)

        # 注册变量同步方法
        self.server.register_function(self.sync_variables_from_client)
        self.server.register_function(self.get_variables_for_client)
        self.server.register_function(self.set_shared_variable)
        self.server.register_function(self.get_shared_variable)
        self.server.register_function(self.list_shared_variables)

        print(f"远程关键字服务器已启动，监听地址: {self.host}:{self.port}")

        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("接收到中断信号，正在关闭服务器...")
        finally:
            self.shutdown()

    def shutdown(self):
        """关闭服务器（用于atexit处理器）"""
        if hasattr(self, '_shutdown_called') and self._shutdown_called:
            return  # 避免重复调用

        # 调用线程化的关闭逻辑
        self._shutdown_in_thread()

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
                args_dict = json.loads(args_dict) if isinstance(
                    args_dict, str) else {}

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

            # 设置变量提供者，确保可以访问YAML变量和全局变量
            try:
                from pytest_dsl.core.variable_providers import setup_context_with_default_providers
                setup_context_with_default_providers(test_context)
            except ImportError:
                # 如果导入失败，记录警告但继续执行
                print("警告：无法设置变量提供者")

            exec_kwargs['context'] = test_context

            # 映射参数（通用逻辑）
            for param_name, param_value in args_dict.items():
                if param_name in mapping:
                    exec_kwargs[mapping[param_name]] = param_value
                else:
                    exec_kwargs[param_name] = param_value

            # 执行关键字执行前的hook
            before_context = hook_manager.execute_hooks(
                HookType.BEFORE_KEYWORD_EXECUTION,
                server=self,
                shared_variables=self.shared_variables,
                keyword_name=name,
                keyword_args=exec_kwargs,
                test_context=test_context
            )

            # 从hook上下文中更新执行参数（hook可能修改了参数）
            if 'keyword_args' in before_context.data:
                exec_kwargs.update(before_context.data['keyword_args'])

            # 执行关键字
            result = keyword_manager.execute(name, **exec_kwargs)

            # 执行关键字执行后的hook
            after_context = hook_manager.execute_hooks(
                HookType.AFTER_KEYWORD_EXECUTION,
                server=self,
                shared_variables=self.shared_variables,
                keyword_name=name,
                keyword_args=exec_kwargs,
                keyword_result=result,
                test_context=test_context
            )

            # 从hook上下文中获取可能修改的结果
            if 'keyword_result' in after_context.data:
                result = after_context.data['keyword_result']

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

    def get_keyword_parameter_details(self, name):
        """获取关键字的参数详细信息，包括默认值

        Args:
            name: 关键字名称

        Returns:
            list: 参数详细信息列表，每个元素包含name, mapping, description, default
        """
        keyword_info = keyword_manager.get_keyword_info(name)
        if not keyword_info:
            return []

        param_details = []
        for param in keyword_info['parameters']:
            param_details.append({
                'name': param.name,
                'mapping': param.mapping,
                'description': param.description,
                'default': param.default
            })

        return param_details

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

            # 将所有同步的变量直接注入到yaml_vars中，实现无缝访问
            from pytest_dsl.core.yaml_vars import yaml_vars

            for name, value in variables.items():
                # 直接设置到yaml_vars中，确保所有关键字都能无缝访问
                yaml_vars._variables[name] = value
                print(f"✓ 变量 {name} 已注入到yaml_vars，实现无缝访问")

            # 同时处理全局变量到global_context
            from pytest_dsl.core.global_context import global_context
            for name, value in variables.items():
                if name.startswith('g_'):
                    global_context.set_variable(name, value)
                    print(f"✓ 全局变量 {name} 已注入到global_context")

            print(f"✅ 总共同步了 {len(variables)} 个变量，全部实现无缝访问")

            return {
                'status': 'success',
                'message': f'成功同步 {len(variables)} 个变量，全部实现无缝访问'
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
    parser.add_argument('--extensions', help='扩展模块路径，多个路径用逗号分隔')

    args = parser.parse_args()

    # 在创建服务器之前加载额外的扩展模块（如果指定）
    if args.extensions:
        print("正在加载额外的扩展模块...")
        _load_extensions(args.extensions)

    # 自动加载当前目录下的扩展
    print("正在自动加载当前目录下的扩展...")
    _auto_load_extensions()

    # 创建并启动服务器（服务器初始化时会自动加载标准关键字）
    server = RemoteKeywordServer(
        host=args.host, port=args.port, api_key=args.api_key)
    server.start()


def _load_extensions(extensions_arg):
    """加载指定的扩展模块"""
    import importlib.util
    import os

    extension_paths = [path.strip() for path in extensions_arg.split(',')]

    for ext_path in extension_paths:
        if not ext_path:
            continue

        try:
            if os.path.isfile(ext_path) and ext_path.endswith('.py'):
                # 加载单个Python文件
                module_name = os.path.splitext(os.path.basename(ext_path))[0]
                spec = importlib.util.spec_from_file_location(
                    module_name, ext_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                print(f"已加载扩展模块: {ext_path}")
            elif os.path.isdir(ext_path):
                # 加载目录下的所有Python文件
                for filename in os.listdir(ext_path):
                    if filename.endswith('.py') and not filename.startswith('_'):
                        file_path = os.path.join(ext_path, filename)
                        module_name = os.path.splitext(filename)[0]
                        spec = importlib.util.spec_from_file_location(
                            module_name, file_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        print(f"已加载扩展模块: {file_path}")
            else:
                # 尝试作为模块名导入
                importlib.import_module(ext_path)
                print(f"已导入扩展模块: {ext_path}")

        except Exception as e:
            print(f"加载扩展模块失败 {ext_path}: {str(e)}")


def _auto_load_extensions():
    """自动加载当前目录下的扩展"""
    import os
    import importlib.util

    # 查找当前目录下的extensions目录
    extensions_dir = os.path.join(os.getcwd(), 'extensions')
    if os.path.isdir(extensions_dir):
        print(f"发现扩展目录: {extensions_dir}")
        _load_extensions(extensions_dir)

    # 查找当前目录下的remote_extensions.py文件
    remote_ext_file = os.path.join(os.getcwd(), 'remote_extensions.py')
    if os.path.isfile(remote_ext_file):
        print(f"发现扩展文件: {remote_ext_file}")
        _load_extensions(remote_ext_file)


if __name__ == '__main__':
    main()
