"""远程服务器自定义授权扩展示例

该模块演示如何使用hook机制实现HTTP请求关键字的自定义授权。
通过在服务器启动时注册自定义授权提供者，并在关键字执行前应用授权逻辑。
"""

import logging
from typing import Dict, Any

from pytest_dsl.core.auth_provider import register_auth_provider, AuthProvider
from pytest_dsl.remote.hook_manager import register_startup_hook, register_before_keyword_hook, register_after_keyword_hook, register_shutdown_hook

logger = logging.getLogger(__name__)


class CustomTestAuthProvider(AuthProvider):
    """自定义test授权提供者

    该授权提供者从远程服务器的共享变量中获取授权信息，
    实现了复用中心端变量的自定义授权机制。
    """

    def __init__(self, **config):
        """初始化自定义授权提供者

        Args:
            **config: 配置参数，可以包含：
                - token_var: 存储token的变量名，默认为'test_token'
                - username_var: 存储用户名的变量名，默认为'test_username'
                - password_var: 存储密码的变量名，默认为'test_password'
        """
        self.username_var = config.get('username_var', 'admin')
        self.password_var = config.get('password_var', 'admin')

    def apply_auth(self, base_url: str, request_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """应用自定义授权

        Args:
            base_url: 请求的基础URL
            request_kwargs: 请求参数

        Returns:
            更新后的请求参数
        """

        # 确保headers存在
        if "headers" not in request_kwargs:
            request_kwargs["headers"] = {}

        # 使用基本认证
        import base64

        credentials = base64.b64encode(f"{self.username_var}:{self.password_var}".encode()).decode()
        request_kwargs["headers"]["X-Auth-Source"] = credentials
        request_kwargs["headers"]["X-Custom-Auth"] = "custom_auth"
        print("dddddddddddddddddddd")
        logger.info(f"应用自定义授权: {self.username_var}:{self.password_var}")
        return request_kwargs


@register_startup_hook
def setup_custom_auth_providers(context):
    """服务器启动时注册自定义授权提供者"""
    logger.info("正在注册自定义授权提供者...")

    # 注册自定义test授权提供者
    register_auth_provider("custom_auth", CustomTestAuthProvider)
    logger.info("已注册自定义test授权提供者: custom_auth")

    print("✅ 自定义授权提供者注册完成")


@register_before_keyword_hook
def before_execute_keyword(context):
    """在HTTP请求关键字执行前注入授权逻辑"""
    keyword_name = context.get('keyword_name')
    print(f"开始执行关键字: {keyword_name}")


@register_after_keyword_hook
def after_execute_keyword(context):
    """在HTTP请求关键字执行后记录结果"""
    keyword_name = context.get('keyword_name')
    keyword_result = context.get('keyword_result')
    print(f"关键字执行结果: {keyword_result}")


@register_shutdown_hook
def shutdown_server(context):
    """服务器关闭时的清理工作"""
    print("服务器关闭，执行清理...")


