import os
import json
import time
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
import requests
from requests.exceptions import RequestException
from urllib.parse import urljoin
from pytest_dsl.core.yaml_vars import yaml_vars
from pytest_dsl.core.auth_provider import AuthProvider, create_auth_provider

logger = logging.getLogger(__name__)


class HTTPClient:
    """HTTP客户端类
    
    负责管理HTTP请求会话和发送请求
    """
    
    def __init__(self, 
                 name: str = "default",
                 base_url: str = "",
                 headers: Dict[str, str] = None,
                 timeout: int = 30,
                 verify_ssl: bool = True,
                 session: bool = True,
                 retry: Dict[str, Any] = None,
                 proxies: Dict[str, str] = None,
                 auth_config: Dict[str, Any] = None):
        """初始化HTTP客户端
        
        Args:
            name: 客户端名称
            base_url: 基础URL
            headers: 默认请求头
            timeout: 默认超时时间(秒)
            verify_ssl: 是否验证SSL证书
            session: 是否启用会话
            retry: 重试配置
            proxies: 代理配置
            auth_config: 认证配置
        """
        self.name = name
        self.base_url = base_url
        self.default_headers = headers or {}
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.use_session = session
        self.retry_config = retry or {
            "max_retries": 0,
            "retry_interval": 1,
            "retry_on_status": [500, 502, 503, 504]
        }
        self.proxies = proxies or {}
        
        # 处理认证配置
        self.auth_provider = None
        if auth_config:
            self.auth_provider = create_auth_provider(auth_config)
            if not self.auth_provider:
                logger.warning(f"无法创建认证提供者: {auth_config}")
        
        # 创建会话
        self._session = requests.Session() if self.use_session else None
        if self.use_session and self.default_headers:
            self._session.headers.update(self.default_headers)
    
    def reset_session(self):
        """完全重置会话对象，创建一个新的会话实例
        
        当需要彻底清除所有会话状态（例如认证信息、cookies等）时使用
        """
        if self.use_session:
            # 关闭当前会话
            if self._session:
                self._session.close()
            
            # 创建新会话
            self._session = requests.Session()
            
            # 重新应用默认头
            if self.default_headers:
                self._session.headers.update(self.default_headers)
            
            logger.debug(f"会话已完全重置: {self.name}")
    
    def make_request(self, method: str, url: str, **request_kwargs) -> requests.Response:
        """发送HTTP请求

        Args:
            method: HTTP方法
            url: 请求URL
            **request_kwargs: 请求参数

        Returns:
            requests.Response: 响应对象
        """
        # 构建完整URL
        if not url.startswith(('http://', 'https://')):
            url = urljoin(self.base_url, url.lstrip('/'))

        # 处理认证
        disable_auth = request_kwargs.pop('disable_auth', False)
        if disable_auth:
            # 如果有认证提供者，使用其清理逻辑
            if self.auth_provider:
                request_kwargs = self.auth_provider.clean_auth_state(request_kwargs)
            else:
                # 默认清理逻辑：移除所有认证相关的头
                auth_headers = [
                    'Authorization', 'X-API-Key', 'X-Api-Key', 'api-key', 'Api-Key',
                    'X-Csrf-Token', 'X-CSRF-Token', 'csrf-token', 'CSRF-Token',  # CSRF相关头
                    'X-WX-OPENID', 'X-WX-SESSION-KEY'  # 微信相关认证头
                ]
                if 'headers' in request_kwargs:
                    for header in auth_headers:
                        request_kwargs['headers'].pop(header, None)
                # 移除认证参数
                request_kwargs.pop('auth', None)
            
            # 如果使用会话，并且认证提供者没有自己的会话管理，则使用默认的会话重置
            if self.use_session and not hasattr(self.auth_provider, 'manage_session'):
                self.reset_session()
                
        elif self.auth_provider and 'auth' not in request_kwargs:
            # 应用认证提供者
            request_kwargs = self.auth_provider.apply_auth(request_kwargs)
            # 如果使用会话，更新会话头
            if self.use_session and 'headers' in request_kwargs:
                self._session.headers.update(request_kwargs['headers'])

        # 记录请求详情
        logger.debug(f"=== HTTP请求详情 ===")
        logger.debug(f"方法: {method}")
        logger.debug(f"URL: {url}")
        if 'headers' in request_kwargs:
            safe_headers = {k: '***' if k.lower() in ['authorization', 'x-api-key', 'token'] else v 
                          for k, v in request_kwargs['headers'].items()}
            logger.debug(f"请求头: {json.dumps(safe_headers, indent=2, ensure_ascii=False)}")
        if 'params' in request_kwargs:
            logger.debug(f"查询参数: {json.dumps(request_kwargs['params'], indent=2, ensure_ascii=False)}")
        if 'json' in request_kwargs:
            logger.debug(f"JSON请求体: {json.dumps(request_kwargs['json'], indent=2, ensure_ascii=False)}")
        if 'data' in request_kwargs:
            logger.debug(f"表单数据: {request_kwargs['data']}")

        # 为超时设置默认值
        if 'timeout' not in request_kwargs:
            request_kwargs['timeout'] = self.timeout
            
        # 为SSL验证设置默认值
        if 'verify' not in request_kwargs:
            request_kwargs['verify'] = self.verify_ssl
            
        # 应用代理配置
        if self.proxies and 'proxies' not in request_kwargs:
            request_kwargs['proxies'] = self.proxies
            
        try:
            # 发送请求
            if self.use_session:
                if self._session is None:
                    logger.warning("会话对象为空，创建新会话")
                    self._session = requests.Session()
                    if self.default_headers:
                        self._session.headers.update(self.default_headers)
                response = self._session.request(method, url, **request_kwargs)
            else:
                response = requests.request(method, url, **request_kwargs)

            # 记录响应详情
            logger.debug(f"\n=== HTTP响应详情 ===")
            logger.debug(f"状态码: {response.status_code}")
            logger.debug(f"响应头: {json.dumps(dict(response.headers), indent=2, ensure_ascii=False)}")
            try:
                if 'application/json' in response.headers.get('Content-Type', ''):
                    logger.debug(f"响应体 (JSON): {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
                else:
                    logger.debug(f"响应体: {response.text}")
            except Exception as e:
                logger.debug(f"解析响应体失败: {str(e)}")
                logger.debug(f"原始响应体: {response.text}")

            # 添加响应时间
            if not hasattr(response, 'elapsed_ms'):
                response.elapsed_ms = response.elapsed.total_seconds() * 1000
                
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP请求异常: {type(e).__name__}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"未预期的异常: {type(e).__name__}: {str(e)}")
            # 将非请求异常包装为请求异常
            raised_exception = requests.exceptions.RequestException(f"HTTP请求过程中发生错误: {str(e)}")
            raised_exception.__cause__ = e
            raise raised_exception
    
    def _log_request(self, method: str, url: str, request_kwargs: Dict[str, Any]) -> None:
        """记录请求信息
        
        Args:
            method: HTTP方法
            url: 请求URL
            request_kwargs: 请求参数
        """
        logger.info(f"发送 {method} 请求到 {url}")
        
        # 打印请求头 (排除敏感信息)
        headers = request_kwargs.get("headers", {})
        safe_headers = headers.copy()
        
        for key in headers:
            if key.lower() in ["authorization", "x-api-key", "token", "api-key"]:
                safe_headers[key] = "***REDACTED***"
                
        logger.debug(f"请求头: {safe_headers}")
        
        # 打印查询参数
        if request_kwargs.get("params"):
            logger.debug(f"查询参数: {request_kwargs['params']}")
            
        # 打印请求体
        if request_kwargs.get("json"):
            logger.debug(f"JSON请求体: {json.dumps(request_kwargs['json'], ensure_ascii=False)}")
        elif request_kwargs.get("data"):
            logger.debug(f"表单数据: {request_kwargs['data']}")
            
        # 打印文件信息
        if request_kwargs.get("files"):
            file_info = {k: f"<文件: {getattr(v, 'name', '未知文件')}>" for k, v in request_kwargs["files"].items()}
            logger.debug(f"上传文件: {file_info}")
    
    def _log_response(self, response: requests.Response) -> None:
        """记录响应信息
        
        Args:
            response: 响应对象
        """
        logger.info(f"收到响应: {response.status_code} {response.reason} ({response.elapsed_ms:.2f}ms)")
        
        # 打印响应头
        logger.debug(f"响应头: {dict(response.headers)}")
        
        # 尝试打印响应体
        try:
            if 'application/json' in response.headers.get('Content-Type', ''):
                logger.debug(f"响应体 (JSON): {json.dumps(response.json(), ensure_ascii=False)}")
            elif len(response.content) < 1024:  # 只打印小响应
                logger.debug(f"响应体: {response.text}")
            else:
                logger.debug(f"响应体: <{len(response.content)} 字节>")
        except Exception as e:
            logger.debug(f"无法打印响应体: {str(e)}")
    
    def close(self) -> None:
        """关闭客户端会话"""
        if self._session:
            self._session.close()
            self._session = None


class HTTPClientManager:
    """HTTP客户端管理器
    
    负责管理多个HTTP客户端实例和会话
    """
    
    def __init__(self):
        """初始化客户端管理器"""
        self._clients: Dict[str, HTTPClient] = {}
        self._sessions: Dict[str, HTTPClient] = {}
    
    def create_client(self, config: Dict[str, Any]) -> HTTPClient:
        """从配置创建客户端
        
        Args:
            config: 客户端配置
            
        Returns:
            HTTPClient实例
        """
        name = config.get("name", "default")
        client = HTTPClient(
            name=name,
            base_url=config.get("base_url", ""),
            headers=config.get("headers", {}),
            timeout=config.get("timeout", 30),
            verify_ssl=config.get("verify_ssl", True),
            session=config.get("session", True),
            retry=config.get("retry", None),
            proxies=config.get("proxies", None),
            auth_config=config.get("auth", None)  # 获取认证配置
        )
        return client
    
    def get_client(self, name: str = "default") -> HTTPClient:
        """获取或创建客户端
        
        Args:
            name: 客户端名称
            
        Returns:
            HTTPClient实例
        """
        # 如果客户端已存在，直接返回
        if name in self._clients:
            return self._clients[name]
        
        # 从YAML变量中读取客户端配置
        http_clients = yaml_vars.get_variable("http_clients") or {}
        client_config = http_clients.get(name)
        
        if not client_config:
            # 如果请求的是default但配置中没有，创建一个默认客户端
            if name == "default":
                logger.warning("使用默认HTTP客户端配置")
                client = HTTPClient(name="default")
                self._clients[name] = client
                return client
            else:
                raise ValueError(f"未找到名为 '{name}' 的HTTP客户端配置")
        
        # 创建新客户端
        client_config["name"] = name
        client = self.create_client(client_config)
        self._clients[name] = client
        return client
    
    def get_session(self, name: str = "default", client_name: str = None) -> HTTPClient:
        """获取或创建命名会话
        
        Args:
            name: 会话名称
            client_name: 用于创建会话的客户端名称
            
        Returns:
            HTTPClient实例
        """
        session_key = name
        
        # 如果会话已存在，直接返回
        if session_key in self._sessions:
            return self._sessions[session_key]
        
        # 使用指定的客户端配置创建新会话
        client_name = client_name or name
        client_config = self._get_client_config(client_name)
        
        if not client_config:
            raise ValueError(f"未找到名为 '{client_name}' 的HTTP客户端配置，无法创建会话")
        
        # 创建新会话
        client_config["name"] = f"session_{name}"
        client_config["session"] = True  # 确保启用会话
        session = self.create_client(client_config)
        self._sessions[session_key] = session
        return session
    
    def _get_client_config(self, name: str) -> Dict[str, Any]:
        """从YAML变量获取客户端配置
        
        Args:
            name: 客户端名称
            
        Returns:
            客户端配置
        """
        http_clients = yaml_vars.get_variable("http_clients") or {}
        client_config = http_clients.get(name)
        
        if not client_config and name == "default":
            # 如果没有默认配置，返回空配置
            return {"name": "default"}
            
        return client_config
    
    def close_client(self, name: str) -> None:
        """关闭指定的客户端
        
        Args:
            name: 客户端名称
        """
        if name in self._clients:
            self._clients[name].close()
            del self._clients[name]
    
    def close_session(self, name: str) -> None:
        """关闭指定的会话
        
        Args:
            name: 会话名称
        """
        if name in self._sessions:
            self._sessions[name].close()
            del self._sessions[name]
    
    def close_all(self) -> None:
        """关闭所有客户端和会话"""
        for client in self._clients.values():
            client.close()
        self._clients.clear()
        
        for session in self._sessions.values():
            session.close()
        self._sessions.clear()


# 创建全局HTTP客户端管理器实例
http_client_manager = HTTPClientManager() 