import os
import json
import time
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
import requests
from requests.exceptions import RequestException
from urllib.parse import urljoin
from pytest_dsl.core.yaml_vars import yaml_vars

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
                 proxies: Dict[str, str] = None):
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
        
        # 创建会话
        self._session = requests.Session() if self.use_session else None
        if self.use_session and self.default_headers:
            self._session.headers.update(self.default_headers)
    
    def make_request(self, 
                     method: str, 
                     url: str, 
                     params: Dict[str, Any] = None,
                     headers: Dict[str, str] = None,
                     json_data: Dict[str, Any] = None,
                     data: Dict[str, Any] = None,
                     files: Dict[str, Any] = None,
                     cookies: Dict[str, str] = None,
                     auth: Tuple[str, str] = None,
                     timeout: int = None,
                     allow_redirects: bool = True,
                     verify: bool = None,
                     cert: str = None,
                     proxies: Dict[str, str] = None,
                     retry_count: int = None,
                     retry_interval: int = None) -> requests.Response:
        """发送HTTP请求
        
        Args:
            method: HTTP方法 (GET, POST, PUT, DELETE等)
            url: 请求URL (相对或绝对URL)
            params: URL查询参数
            headers: 请求头
            json_data: JSON请求体
            data: 表单数据
            files: 文件上传
            cookies: Cookie
            auth: 基本认证 (username, password)
            timeout: 超时时间(秒)
            allow_redirects: 是否允许重定向
            verify: 是否验证SSL证书
            cert: 客户端证书
            proxies: 代理设置
            retry_count: 重试次数
            retry_interval: 重试间隔(秒)
            
        Returns:
            requests.Response对象
        """
        # 处理文件路径
        if files:
            processed_files = {}
            for key, file_path in files.items():
                if isinstance(file_path, str) and os.path.exists(file_path):
                    processed_files[key] = open(file_path, 'rb')
                else:
                    processed_files[key] = file_path
            files = processed_files
            
        # 合并请求头
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)
            
        # 构建完整URL
        if not url.startswith(('http://', 'https://')):
            url = urljoin(self.base_url, url)
            
        # 设置默认值
        timeout_value = timeout if timeout is not None else self.timeout
        verify_value = verify if verify is not None else self.verify_ssl
        proxies_value = proxies if proxies is not None else self.proxies
        
        # 设置重试参数
        max_retries = retry_count if retry_count is not None else self.retry_config.get("max_retries", 0)
        retry_interval_value = retry_interval if retry_interval is not None else self.retry_config.get("retry_interval", 1)
        retry_on_status = self.retry_config.get("retry_on_status", [500, 502, 503, 504])
        
        # 构建请求参数
        request_kwargs = {
            "params": params,
            "headers": request_headers,
            "cookies": cookies,
            "auth": auth,
            "timeout": timeout_value,
            "allow_redirects": allow_redirects,
            "verify": verify_value,
            "proxies": proxies_value
        }
        
        # 设置请求体
        if json_data is not None:
            request_kwargs["json"] = json_data
        if data is not None:
            request_kwargs["data"] = data
        if files is not None:
            request_kwargs["files"] = files
        if cert is not None:
            request_kwargs["cert"] = cert
            
        # 记录请求信息
        self._log_request(method, url, request_kwargs)
        
        # 发送请求并处理重试
        attempts = 0
        last_exception = None
        
        while attempts <= max_retries:
            try:
                start_time = time.time()
                
                # 使用会话或直接请求
                if self.use_session:
                    response = self._session.request(method, url, **request_kwargs)
                else:
                    response = requests.request(method, url, **request_kwargs)
                
                # 计算响应时间
                response_time = (time.time() - start_time) * 1000
                response.elapsed_ms = response_time  # 添加自定义属性
                
                # 记录响应信息
                self._log_response(response)
                
                # 检查是否需要重试
                if response.status_code in retry_on_status and attempts < max_retries:
                    logger.warning(f"请求返回状态码 {response.status_code}，将在 {retry_interval_value} 秒后重试 ({attempts+1}/{max_retries})")
                    time.sleep(retry_interval_value)
                    attempts += 1
                    continue
                    
                return response
                
            except RequestException as e:
                last_exception = e
                if attempts < max_retries:
                    logger.warning(f"请求失败: {str(e)}，将在 {retry_interval_value} 秒后重试 ({attempts+1}/{max_retries})")
                    time.sleep(retry_interval_value)
                    attempts += 1
                else:
                    logger.error(f"请求失败，已达到最大重试次数: {str(e)}")
                    raise
            finally:
                # 关闭文件句柄
                if files:
                    for file_obj in processed_files.values():
                        if hasattr(file_obj, 'close'):
                            file_obj.close()
        
        # 如果所有重试都失败，抛出最后一个异常
        if last_exception:
            raise last_exception
            
        # 这一行通常不会执行，因为上面会返回响应或引发异常
        raise RequestException("未知错误，无法完成请求")
    
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
            proxies=config.get("proxies", None)
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