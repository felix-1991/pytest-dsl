"""装饰器测试示例

该示例展示如何使用auto_dsl装饰器创建测试类
"""

from pytest_dsl.core.auto_decorator import auto_dsl
from pytest_dsl.core.auth_provider import register_auth_provider, CustomAuthProvider
import requests
import json
import logging
import sys

# 配置日志输出
logging.basicConfig(
    level=logging.DEBUG,  # 设置为DEBUG级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("CSRF_AUTH_DEBUG")


@auto_dsl("./http")
class TestHttp:
    """HTTP测试类
    
    该类使用auto_dsl装饰器，测试http目录下的.auto文件。
    """
    pass

# 定义自定义认证提供者
class HMACAuthProvider(CustomAuthProvider):
    def apply_auth(self, request_kwargs):
        if "headers" not in request_kwargs:
            request_kwargs["headers"] = {}
        request_kwargs["headers"]["Authorization"] = "HMAC-SHA256 test_signature"
        request_kwargs["headers"]["X-Amz-Date"] = "20240501T120000Z"
        return request_kwargs

class JWTAuthProvider(CustomAuthProvider):
    def apply_auth(self, request_kwargs):
        if "headers" not in request_kwargs:
            request_kwargs["headers"] = {}
        request_kwargs["headers"]["Authorization"] = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example_token"
        return request_kwargs

class WeChatAuthProvider(CustomAuthProvider):
    def apply_auth(self, request_kwargs):
        if "headers" not in request_kwargs:
            request_kwargs["headers"] = {}
        request_kwargs["headers"]["X-Wx-Openid"] = "test_openid"
        request_kwargs["headers"]["X-Wx-Session-Key"] = "test_session_key"
        return request_kwargs

class MultiStepAuthProvider(CustomAuthProvider):
    def apply_auth(self, request_kwargs):
        if "headers" not in request_kwargs:
            request_kwargs["headers"] = {}
        request_kwargs["headers"]["Authorization"] = "Bearer multi_step_token"
        return request_kwargs

class CSRFLoginAuthProvider(CustomAuthProvider):
    """CSRF登录认证提供者
    
    该提供者实现了一个需要先登录获取CSRF令牌，然后在后续请求中使用该令牌的认证流程。
    为了适应httpbin.org的测试，这里模拟了CSRF认证流程。
    """
    def __init__(self):
        self._csrf_token = None
        self._session = requests.Session()
        logger.setLevel(logging.DEBUG)  # 设置日志级别为DEBUG
        
    def apply_auth(self, request_kwargs):
        # 确保headers存在
        if "headers" not in request_kwargs:
            request_kwargs["headers"] = {}
            
        # 如果还没有CSRF令牌，先登录获取
        if not self._csrf_token:
            self._login()
            
        # 添加CSRF令牌到请求头
        request_kwargs["headers"]["X-Csrf-Token"] = self._csrf_token
        
        # 设置Content-Type头
        # 如果请求中有JSON数据
        if "json" in request_kwargs:
            request_kwargs["headers"]["Content-Type"] = "application/json"
            logger.debug(f"请求体 (JSON): {json.dumps(request_kwargs['json'])}")
        # 如果请求中有表单数据
        elif "data" in request_kwargs:
            # 如果data是字典，默认为表单数据
            if isinstance(request_kwargs["data"], dict):
                if "Content-Type" not in request_kwargs["headers"]:
                    request_kwargs["headers"]["Content-Type"] = "application/x-www-form-urlencoded"
            logger.debug(f"请求体 (form): {request_kwargs['data']}")
        
        # 调试信息：打印请求信息
        method = request_kwargs.get('method', 'GET')
        url = request_kwargs.get('url', '')
        logger.debug(f"发送请求: {method} {url}")
        logger.debug(f"请求头: {json.dumps(request_kwargs.get('headers', {}))}")
        
        return request_kwargs
    
    def clean_auth_state(self, request_kwargs=None):
        """清理CSRF认证状态
        
        清理CSRF认证相关的状态，包括令牌和会话。
        
        Args:
            request_kwargs: 请求参数
            
        Returns:
            更新后的请求参数
        """
        # 重置CSRF令牌
        logger.debug("清理CSRF认证状态")
        self._csrf_token = None
        
        # 如果有会话，清理会话
        if self._session:
            self._session.cookies.clear()
            logger.debug("已清理CSRF会话cookie")
            
        # 处理请求参数
        if request_kwargs:
            if "headers" not in request_kwargs:
                request_kwargs["headers"] = {}
                
            # 移除CSRF相关头
            csrf_headers = ['X-Csrf-Token', 'X-CSRF-Token', 'csrf-token', 'CSRF-Token']
            for header in csrf_headers:
                if header in request_kwargs["headers"]:
                    request_kwargs["headers"].pop(header)
                    logger.debug(f"已移除请求头: {header}")
                    
        # 标记会话已管理
        self.manage_session = True
                    
        return request_kwargs if request_kwargs else {}
        
    def _login(self):
        """执行登录流程获取CSRF令牌
        
        由于httpbin.org没有实际的登录系统，这里模拟一个登录流程
        """
        # 对于测试目的，生成一个模拟的CSRF令牌
        self._csrf_token = "csrf_token_12345678"
        logger.debug(f"生成CSRF令牌: {self._csrf_token}")

        # 如果使用真实API，可以使用类似下面的代码
        # 1. 获取登录页面，提取CSRF令牌
        # login_page = self._session.get("https://httpbin.org/headers")
        # login_page.raise_for_status()
        
        # 2. 执行登录请求
        # login_response = self._session.post(
        #     "https://httpbin.org/anything",
        #     json={"username": "test_user", "password": "test_password"}
        # )
        # login_response.raise_for_status()

# 注册自定义认证提供者
register_auth_provider("hmac_aws_auth", HMACAuthProvider)
register_auth_provider("jwt_refresh_auth", JWTAuthProvider)
register_auth_provider("wechat_miniapp_auth", WeChatAuthProvider)
register_auth_provider("multi_step_auth", MultiStepAuthProvider)
register_auth_provider("csrf_login_auth", CSRFLoginAuthProvider)
