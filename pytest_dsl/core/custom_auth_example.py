"""自定义授权示例模块

该模块提供了几个复杂授权流程的实现示例，展示如何开发和注册自定义授权提供者。
"""

import time
import json
import logging
import hashlib
import hmac
import base64
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

import requests

from pytest_dsl.core.auth_provider import (
    AuthProvider, register_auth_provider, CustomAuthProvider
)

logger = logging.getLogger(__name__)


class HmacAuthProvider(AuthProvider):
    """HMAC签名认证提供者
    
    使用HMAC算法对请求参数进行签名，常用于AWS, 阿里云等API认证。
    """
    
    def __init__(self, access_key: str, secret_key: str, 
                 region: str = None, service: str = None,
                 algorithm: str = 'sha256'):
        """初始化HMAC签名认证
        
        Args:
            access_key: 访问密钥ID
            secret_key: 秘密访问密钥
            region: 区域 (用于某些云服务API)
            service: 服务名称 (用于某些云服务API)
            algorithm: 哈希算法 ('sha256', 'sha1', 等)
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.service = service
        self.algorithm = algorithm
        
    def apply_auth(self, request_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """应用HMAC签名认证
        
        Args:
            request_kwargs: 请求参数
            
        Returns:
            更新后的请求参数
        """
        # 确保headers存在
        if "headers" not in request_kwargs:
            request_kwargs["headers"] = {}
        
        # 获取当前时间
        now = datetime.utcnow()
        amz_date = now.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = now.strftime('%Y%m%d')
        
        # 添加必要的头部
        request_kwargs["headers"]["X-Amz-Date"] = amz_date
        
        # 准备签名参数
        method = request_kwargs.get("method", "GET")
        url_path = "/"  # 简化示例
        
        # 创建规范请求
        canonical_uri = url_path
        canonical_querystring = ""
        
        # 创建规范头部
        canonical_headers = '\n'.join([
            f"{header.lower()}:{value}" 
            for header, value in sorted(request_kwargs["headers"].items())
        ]) + '\n'
        
        signed_headers = ';'.join([
            header.lower() for header in sorted(request_kwargs["headers"].keys())
        ])
        
        # 获取请求体的哈希值
        payload_hash = hashlib.sha256(b'').hexdigest()  # 简化示例
        
        # 创建规范请求
        canonical_request = f"{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        
        # 创建签名字符串
        algorithm = f"HMAC-{self.algorithm.upper()}"
        credential_scope = f"{date_stamp}/{self.region}/{self.service}/aws4_request"
        string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        
        # 计算签名
        k_date = hmac.new(f"AWS4{self.secret_key}".encode('utf-8'), date_stamp.encode('utf-8'), hashlib.sha256).digest()
        k_region = hmac.new(k_date, self.region.encode('utf-8'), hashlib.sha256).digest()
        k_service = hmac.new(k_region, self.service.encode('utf-8'), hashlib.sha256).digest()
        k_signing = hmac.new(k_service, b"aws4_request", hashlib.sha256).digest()
        signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # 添加授权头
        authorization_header = (
            f"{algorithm} "
            f"Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )
        request_kwargs["headers"]["Authorization"] = authorization_header
        
        return request_kwargs


class JwtRefreshAuthProvider(AuthProvider):
    """JWT刷新令牌授权提供者
    
    使用刷新令牌自动获取和刷新JWT访问令牌。
    """
    
    def __init__(self, token_url: str, refresh_token: str, client_id: str = None, 
                 client_secret: str = None, token_refresh_window: int = 60):
        """初始化JWT刷新令牌授权
        
        Args:
            token_url: 获取/刷新令牌的URL
            refresh_token: 刷新令牌
            client_id: 客户端ID (可选)
            client_secret: 客户端密钥 (可选)
            token_refresh_window: 令牌刷新窗口 (秒)
        """
        self.token_url = token_url
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_refresh_window = token_refresh_window
        
        # 令牌缓存
        self._access_token = None
        self._token_expires_at = 0
        
    def apply_auth(self, request_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """应用JWT授权
        
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
        """使用刷新令牌获取新的访问令牌"""
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        
        # 添加客户端凭据（如果提供）
        headers = {}
        if self.client_id and self.client_secret:
            auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode('utf-8')).decode('utf-8')
            headers["Authorization"] = f"Basic {auth_header}"
            
        try:
            response = requests.post(self.token_url, data=data, headers=headers)
            response.raise_for_status()
            
            token_data = response.json()
            self._access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)  # 默认1小时
            
            # 如果有新的刷新令牌，更新它
            if "refresh_token" in token_data:
                self.refresh_token = token_data["refresh_token"]
                
            if not self._access_token:
                raise ValueError("响应中缺少access_token字段")
                
            # 计算过期时间
            self._token_expires_at = time.time() + expires_in
            logger.info(f"成功刷新JWT令牌，有效期{expires_in}秒")
            
        except Exception as e:
            logger.error(f"刷新JWT令牌失败: {str(e)}")
            raise


class WechatMiniAppAuthProvider(AuthProvider):
    """微信小程序认证提供者
    
    使用code获取微信小程序的session_key和openid，适用于微信小程序API调用。
    """
    
    def __init__(self, appid: str, secret: str, code: str = None):
        """初始化微信小程序认证
        
        Args:
            appid: 小程序的AppID
            secret: 小程序的AppSecret
            code: 登录时获取的临时code
        """
        self.appid = appid
        self.secret = secret
        self.code = code
        
        # 微信登录凭据
        self.session_key = None
        self.openid = None
        
    def apply_auth(self, request_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """应用微信小程序认证
        
        Args:
            request_kwargs: 请求参数
            
        Returns:
            更新后的请求参数
        """
        # 如果未获取过登录凭据且有code，则先获取凭据
        if (not self.session_key or not self.openid) and self.code:
            self._login_with_code()
            
        # 确保已获取登录凭据
        if not self.session_key or not self.openid:
            raise ValueError("未获取到微信登录凭据，无法完成认证")
            
        # 确保headers存在
        if "headers" not in request_kwargs:
            request_kwargs["headers"] = {}
            
        # 添加认证头
        request_kwargs["headers"]["X-WX-OPENID"] = self.openid
        request_kwargs["headers"]["X-WX-SESSION-KEY"] = self.session_key
        
        return request_kwargs
        
    def _login_with_code(self) -> None:
        """使用code获取登录凭据"""
        url = f"https://api.weixin.qq.com/sns/jscode2session"
        params = {
            "appid": self.appid,
            "secret": self.secret,
            "js_code": self.code,
            "grant_type": "authorization_code"
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if "errcode" in data and data["errcode"] != 0:
                raise ValueError(f"微信登录失败: {data.get('errmsg', '未知错误')}")
                
            self.session_key = data.get("session_key")
            self.openid = data.get("openid")
            
            if not self.session_key or not self.openid:
                raise ValueError("微信登录响应缺少session_key或openid")
                
            logger.info(f"成功获取微信小程序登录凭据，openid: {self.openid}")
            
            # 清除code，因为它是一次性的
            self.code = None
            
        except Exception as e:
            logger.error(f"获取微信小程序登录凭据失败: {str(e)}")
            raise


class MultiStepAuthProvider(CustomAuthProvider):
    """多步骤认证提供者
    
    实现一个需要多个步骤的认证流程，包括获取临时令牌、换取访问令牌等。
    """
    
    def __init__(self):
        """初始化多步骤认证提供者"""
        self._cached_token = None
        self._token_expires_at = 0
        
    def apply_auth(self, request_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """应用多步骤认证
        
        Args:
            request_kwargs: 请求参数
            
        Returns:
            更新后的请求参数
        """
        # 检查缓存令牌是否有效
        current_time = time.time()
        cached_token = self._cached_token
        
        if cached_token and current_time < self._token_expires_at:
            # 令牌有效，直接使用
            if "headers" not in request_kwargs:
                request_kwargs["headers"] = {}
            request_kwargs["headers"]["Authorization"] = f"Bearer {cached_token}"
            return request_kwargs
            
        # 令牌无效，开始多步骤认证流程
        try:
            # 步骤1: 获取临时令牌
            temp_token_response = requests.post(
                "https://api.example.com/auth/temp-token",
                json={
                    "app_id": "your_app_id",
                    "app_secret": "your_app_secret",
                    "device_id": str(uuid.uuid4())  # 示例设备ID
                }
            )
            temp_token_response.raise_for_status()
            temp_token_data = temp_token_response.json()
            temp_token = temp_token_data.get("temp_token")
            
            if not temp_token:
                raise ValueError("无法获取临时令牌")
                
            # 步骤2: 用临时令牌换取访问令牌
            access_token_response = requests.post(
                "https://api.example.com/auth/access-token",
                json={
                    "temp_token": temp_token,
                    "client_id": "your_client_id",
                    "signature": hashlib.sha256(f"your_client_id:{temp_token}:your_client_secret".encode()).hexdigest()
                }
            )
            access_token_response.raise_for_status()
            token_data = access_token_response.json()
            
            # 提取数据
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)
            
            if not access_token:
                raise ValueError("无法获取访问令牌")
                
            # 缓存令牌
            self._cached_token = access_token
            self._token_expires_at = time.time() + expires_in - 60  # 提前60秒刷新
            
            # 步骤3: 应用访问令牌到请求
            if "headers" not in request_kwargs:
                request_kwargs["headers"] = {}
            request_kwargs["headers"]["Authorization"] = f"Bearer {access_token}"
            
            return request_kwargs
            
        except Exception as e:
            logger.error(f"多步骤认证失败: {str(e)}")
            # 出错时，尝试使用之前的令牌（即使已过期）
            if cached_token:
                if "headers" not in request_kwargs:
                    request_kwargs["headers"] = {}
                request_kwargs["headers"]["Authorization"] = f"Bearer {cached_token}"
                logger.warning("使用过期的缓存令牌")
            
            return request_kwargs


def register_complex_auth_example():
    """注册复杂授权示例"""
    # 注册HMAC签名认证提供者
    register_auth_provider(
        "hmac_aws_auth",
        HmacAuthProvider,
        access_key="AKIAIOSFODNN7EXAMPLE",
        secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="us-west-2",
        service="s3",
        algorithm="sha256"
    )
    
    # 注册JWT刷新令牌认证提供者
    register_auth_provider(
        "jwt_refresh_auth",
        JwtRefreshAuthProvider,
        token_url="https://api.example.com/oauth/token",
        refresh_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        client_id="client_id_example",
        client_secret="client_secret_example"
    )
    
    # 注册微信小程序认证提供者
    register_auth_provider(
        "wechat_miniapp_auth",
        WechatMiniAppAuthProvider,
        appid="wx1234567890abcdef",
        secret="abcdef1234567890abcdef1234567890",
        code="023Bj3ll2EE81B0TrTnl2kQSll2Bj3lY"
    )
    
    # 注册多步骤认证提供者
    register_auth_provider(
        "multi_step_auth",
        MultiStepAuthProvider
    )
    
    logger.info("已注册复杂授权示例")

# 自动注册示例（取消注释以启用）
# register_complex_auth_example() 