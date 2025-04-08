"""装饰器测试示例

该示例展示如何使用auto_dsl装饰器创建测试类
"""

from pytest_dsl.core.auto_decorator import auto_dsl
from pytest_dsl.core.auth_provider import register_auth_provider, CustomAuthProvider

# # 自定义认证测试
# @auto_dsl("./http/custom_auth_test.auto", is_file=True)
# class TestCustomAuth:
#     """自定义HTTP认证测试类
    
#     该类使用auto_dsl装饰器，测试自定义认证提供者。
#     """
#     pass

# # 内置认证测试
# @auto_dsl("./http/builtin_auth_test.auto", is_file=True)
# class TestBuiltinAuth:
#     """内置HTTP认证测试类
    
#     该类使用auto_dsl装饰器，测试内置认证提供者。
#     """
#     pass

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

# 注册自定义认证提供者
register_auth_provider("hmac_aws_auth", HMACAuthProvider)
register_auth_provider("jwt_refresh_auth", JWTAuthProvider)
register_auth_provider("wechat_miniapp_auth", WeChatAuthProvider)
register_auth_provider("multi_step_auth", MultiStepAuthProvider)
