"""认证提供者模块

该模块提供了用于HTTP请求认证的接口和实现。
"""

import abc
import base64
import json
import logging
import time
from typing import Dict, Any, Optional, Callable, Union, Tuple, Type
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class AuthProvider(abc.ABC):
    """认证提供者基类"""
    
    @abc.abstractmethod
    def apply_auth(self, request_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """将认证信息应用到请求参数
        
        Args:
            request_kwargs: 请求参数字典
            
        Returns:
            更新后的请求参数字典
        """
        pass
    
    def clean_auth_state(self, request_kwargs: Dict[str, Any] = None) -> Dict[str, Any]:
        """清理认证状态
        
        此方法用于清理认证状态，例如移除认证头、清空会话Cookie等。
        子类可以覆盖此方法以提供自定义的清理逻辑。
        
        Args:
            request_kwargs: 请求参数字典
            
        Returns:
            更新后的请求参数字典
        """
        # 默认实现：移除基本的认证头
        if request_kwargs is None:
            return {}
            
        if "headers" in request_kwargs:
            auth_headers = [
                'Authorization', 'X-API-Key', 'X-Api-Key', 'api-key', 'Api-Key',
            ]
            for header in auth_headers:
                request_kwargs["headers"].pop(header, None)
                
        # 移除认证参数
        request_kwargs.pop('auth', None)
            
        return request_kwargs
    
    @property
    def name(self) -> str:
        """返回认证提供者名称"""
        return self.__class__.__name__


class BasicAuthProvider(AuthProvider):
    """基本认证提供者"""
    
    def __init__(self, username: str, password: str):
        """初始化基本认证
        
        Args:
            username: 用户名
            password: 密码
        """
        self.username = username
        self.password = password
        
    def apply_auth(self, request_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """应用基本认证
        
        Args:
            request_kwargs: 请求参数
            
        Returns:
            更新后的请求参数
        """
        # 使用requests的基本认证
        request_kwargs["auth"] = HTTPBasicAuth(self.username, self.password)
        return request_kwargs


class TokenAuthProvider(AuthProvider):
    """令牌认证提供者"""
    
    def __init__(self, token: str, scheme: str = "Bearer", header: str = "Authorization"):
        """初始化令牌认证
        
        Args:
            token: 认证令牌
            scheme: 认证方案 (例如 "Bearer")
            header: 认证头名称 (默认为 "Authorization")
        """
        self.token = token
        self.scheme = scheme
        self.header = header
        
    def apply_auth(self, request_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """应用令牌认证
        
        Args:
            request_kwargs: 请求参数
            
        Returns:
            更新后的请求参数
        """
        # 确保headers存在
        if "headers" not in request_kwargs:
            request_kwargs["headers"] = {}
            
        # 添加认证头
        if self.scheme:
            request_kwargs["headers"][self.header] = f"{self.scheme} {self.token}"
        else:
            request_kwargs["headers"][self.header] = self.token
            
        return request_kwargs


class ApiKeyAuthProvider(AuthProvider):
    """API Key认证提供者"""
    
    def __init__(self, api_key: str, key_name: str = "X-API-Key", in_header: bool = True, 
                 in_query: bool = False, query_param_name: str = None):
        """初始化API Key认证
        
        Args:
            api_key: API密钥
            key_name: 密钥名称 (默认为 "X-API-Key")
            in_header: 是否在请求头中添加密钥
            in_query: 是否在查询参数中添加密钥
            query_param_name: 查询参数名称 (如果与header名称不同)
        """
        self.api_key = api_key
        self.key_name = key_name
        self.in_header = in_header
        self.in_query = in_query
        self.query_param_name = query_param_name or key_name
        
    def apply_auth(self, request_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """应用API Key认证
        
        Args:
            request_kwargs: 请求参数
            
        Returns:
            更新后的请求参数
        """
        # 添加到请求头
        if self.in_header:
            if "headers" not in request_kwargs:
                request_kwargs["headers"] = {}
            request_kwargs["headers"][self.key_name] = self.api_key
            
        # 添加到查询参数
        if self.in_query:
            if "params" not in request_kwargs:
                request_kwargs["params"] = {}
            request_kwargs["params"][self.query_param_name] = self.api_key
            
        return request_kwargs


class OAuth2Provider(AuthProvider):
    """OAuth2认证提供者"""
    
    def __init__(self, token_url: str, client_id: str, client_secret: str, 
                 scope: str = None, grant_type: str = "client_credentials",
                 username: str = None, password: str = None,
                 token_refresh_window: int = 60):
        """初始化OAuth2认证
        
        Args:
            token_url: 获取令牌的URL
            client_id: 客户端ID
            client_secret: 客户端密钥
            scope: 权限范围
            grant_type: 授权类型 (默认为 "client_credentials")
            username: 用户名 (如果grant_type为"password")
            password: 密码 (如果grant_type为"password")
            token_refresh_window: 令牌刷新窗口 (秒)，在令牌过期前多少秒刷新
        """
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.grant_type = grant_type
        self.username = username
        self.password = password
        self.token_refresh_window = token_refresh_window
        
        # 令牌缓存
        self._access_token = None
        self._token_expires_at = 0
        
    def apply_auth(self, request_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """应用OAuth2认证
        
        Args:
            request_kwargs: 请求参数
            
        Returns:
            更新后的请求参数
        """
        # 确保有有效的令牌
        self._ensure_valid_token()
        
        # 确保headers存在
        if "headers" not in request_kwargs:
            request_kwargs["headers"] = {}
            
        # 添加认证头
        request_kwargs["headers"]["Authorization"] = f"Bearer {self._access_token}"
        return request_kwargs
        
    def _ensure_valid_token(self) -> None:
        """确保有有效的访问令牌"""
        current_time = time.time()
        
        # 如果令牌不存在或即将过期，刷新令牌
        if not self._access_token or current_time + self.token_refresh_window >= self._token_expires_at:
            self._refresh_token()
            
    def _refresh_token(self) -> None:
        """刷新OAuth2令牌"""
        data = {
            "grant_type": self.grant_type,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        if self.scope:
            data["scope"] = self.scope
            
        # 对于密码模式
        if self.grant_type == "password" and self.username and self.password:
            data["username"] = self.username
            data["password"] = self.password
            
        try:
            response = requests.post(self.token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self._access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)  # 默认1小时
            
            if not self._access_token:
                raise ValueError("响应中缺少access_token字段")
                
            # 计算过期时间
            self._token_expires_at = time.time() + expires_in
            logger.info(f"成功获取OAuth2令牌，有效期{expires_in}秒")
            
        except Exception as e:
            logger.error(f"获取OAuth2令牌失败: {str(e)}")
            raise


class CustomAuthProvider(AuthProvider):
    """自定义认证提供者基类
    
    用户可以通过继承此类并实现apply_auth方法来创建自定义认证提供者。
    """
    def __init__(self):
        """初始化自定义认证提供者"""
        pass

    @abc.abstractmethod
    def apply_auth(self, request_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """应用自定义认证
        
        Args:
            request_kwargs: 请求参数
            
        Returns:
            更新后的请求参数
        """
        pass


# 认证提供者注册表
auth_provider_registry = {}


def register_auth_provider(name: str, provider_class: Type[AuthProvider], *args, **kwargs) -> None:
    """注册认证提供者
    
    Args:
        name: 提供者名称
        provider_class: 提供者类，必须是 AuthProvider 的子类
        *args: 传递给提供者类的初始化参数
        **kwargs: 传递给提供者类的初始化关键字参数
    """
    if not issubclass(provider_class, AuthProvider):
        raise ValueError(f"Provider class must be a subclass of AuthProvider, got {provider_class.__name__}")
    
    provider = provider_class(*args, **kwargs)
    auth_provider_registry[name] = provider
    logger.info(f"Registered auth provider '{name}' with class {provider_class.__name__}")


def get_auth_provider(name: str) -> Optional[AuthProvider]:
    """获取认证提供者
    
    Args:
        name: 提供者名称
        
    Returns:
        认证提供者实例
    """
    return auth_provider_registry.get(name)


def create_auth_provider(auth_config: Dict[str, Any]) -> Optional[AuthProvider]:
    """根据配置创建认证提供者
    
    Args:
        auth_config: 认证配置
        
    Returns:
        认证提供者实例
    """
    auth_type = auth_config.get("type", "").lower()
    
    if not auth_type:
        return None
        
    if auth_type == "basic":
        username = auth_config.get("username")
        password = auth_config.get("password")
        
        if not username or not password:
            logger.error("基本认证配置缺少username或password参数")
            return None
            
        return BasicAuthProvider(username, password)
        
    elif auth_type == "token":
        token = auth_config.get("token")
        scheme = auth_config.get("scheme", "Bearer")
        header = auth_config.get("header", "Authorization")
        
        if not token:
            logger.error("令牌认证配置缺少token参数")
            return None
            
        return TokenAuthProvider(token, scheme, header)
        
    elif auth_type == "api_key":
        api_key = auth_config.get("api_key")
        key_name = auth_config.get("key_name", "X-API-Key")
        in_header = auth_config.get("in_header", True)
        in_query = auth_config.get("in_query", False)
        query_param_name = auth_config.get("query_param_name")
        
        if not api_key:
            logger.error("API Key认证配置缺少api_key参数")
            return None
            
        return ApiKeyAuthProvider(
            api_key=api_key,
            key_name=key_name,
            in_header=in_header,
            in_query=in_query,
            query_param_name=query_param_name
        )
        
    elif auth_type == "oauth2":
        token_url = auth_config.get("token_url")
        client_id = auth_config.get("client_id")
        client_secret = auth_config.get("client_secret")
        scope = auth_config.get("scope")
        grant_type = auth_config.get("grant_type", "client_credentials")
        username = auth_config.get("username")
        password = auth_config.get("password")
        token_refresh_window = auth_config.get("token_refresh_window", 60)
        
        if not token_url or not client_id or not client_secret:
            logger.error("OAuth2认证配置缺少必要参数")
            return None
            
        return OAuth2Provider(
            token_url, client_id, client_secret, scope, grant_type,
            username, password, token_refresh_window
        )
        
    elif auth_type == "custom":
        provider_name = auth_config.get("provider_name")
        if provider_name and provider_name in auth_provider_registry:
            return auth_provider_registry[provider_name]
        else:
            logger.error(f"未找到名为'{provider_name}'的自定义认证提供者")
            return None
        
    else:
        logger.error(f"不支持的认证类型: {auth_type}")
        return None 