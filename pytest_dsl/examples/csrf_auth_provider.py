"""CSRF认证提供者示例

此模块提供了一个CSRF认证提供者的示例实现，展示如何使用AuthProvider的响应处理钩子。
"""

import logging
import json
import re
from typing import Dict, Any
import requests
from pytest_dsl.core.auth_provider import CustomAuthProvider, register_auth_provider

logger = logging.getLogger(__name__)


class CSRFAuthProvider(CustomAuthProvider):
    """CSRF令牌认证提供者
    
    此提供者从响应中提取CSRF令牌，并将其应用到后续请求中。
    支持从Cookie、响应头或响应体中提取令牌。
    """
    
    def __init__(self, 
                 token_source: str = "header",  # header, cookie, body
                 source_name: str = "X-CSRF-Token",  # 头名称、Cookie名称或JSON路径
                 header_name: str = "X-CSRF-Token",  # 请求头名称
                 regex_pattern: str = None):  # 从响应体提取的正则表达式
        """初始化CSRF令牌认证提供者
        
        Args:
            token_source: 令牌来源，可以是 "header"、"cookie" 或 "body"
            source_name: 源名称，取决于token_source:
                         - 当token_source为"header"时，表示头名称
                         - 当token_source为"cookie"时，表示Cookie名称
                         - 当token_source为"body"时，表示JSON路径或CSS选择器
            header_name: 请求头名称，用于发送令牌
            regex_pattern: 从响应体提取令牌的正则表达式（当token_source为"body"时）
        """
        super().__init__()
        self.token_source = token_source
        self.source_name = source_name
        self.header_name = header_name
        self.regex_pattern = regex_pattern
        self.csrf_token = None
        self._session = requests.Session()
        
        # 标识此提供者管理会话
        self.manage_session = True
        
        logger.info(f"初始化CSRF令牌认证提供者 (源: {token_source}, 名称: {source_name})")
    
    def apply_auth(self, request_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """应用CSRF令牌认证
        
        将CSRF令牌添加到请求头中。
        
        Args:
            request_kwargs: 请求参数
            
        Returns:
            更新后的请求参数
        """
        # 确保headers存在
        if "headers" not in request_kwargs:
            request_kwargs["headers"] = {}
        
        # 如果已有令牌，添加到请求头
        if self.csrf_token:
            request_kwargs["headers"][self.header_name] = self.csrf_token
            logger.debug(f"添加CSRF令牌到请求头: {self.header_name}={self.csrf_token}")
        else:
            logger.warning("尚未获取到CSRF令牌，无法添加到请求头")
        
        return request_kwargs
    
    def process_response(self, response: requests.Response) -> None:
        """处理响应以提取CSRF令牌
        
        从响应的头、Cookie或正文中提取CSRF令牌。
        
        Args:
            response: 响应对象
        """
        token = None
        
        # 从头中提取
        if self.token_source == "header":
            token = response.headers.get(self.source_name)
            if token:
                logger.debug(f"从响应头提取CSRF令牌: {self.source_name}={token}")
            else:
                logger.debug(f"响应头中未找到CSRF令牌: {self.source_name}")
                
        # 从Cookie中提取
        elif self.token_source == "cookie":
            token = response.cookies.get(self.source_name)
            if token:
                logger.debug(f"从Cookie提取CSRF令牌: {self.source_name}={token}")
            else:
                logger.debug(f"Cookie中未找到CSRF令牌: {self.source_name}")
                
        # 从响应体中提取
        elif self.token_source == "body":
            # 如果有正则表达式模式
            if self.regex_pattern:
                try:
                    match = re.search(self.regex_pattern, response.text)
                    if match and match.group(1):
                        token = match.group(1)
                        logger.debug(f"使用正则表达式从响应体提取CSRF令牌: {token}")
                    else:
                        logger.debug(f"正则表达式未匹配到CSRF令牌: {self.regex_pattern}")
                except Exception as e:
                    logger.error(f"使用正则表达式提取CSRF令牌失败: {str(e)}")
            # 如果是JSON响应，尝试使用JSON路径
            elif 'application/json' in response.headers.get('Content-Type', ''):
                try:
                    json_data = response.json()
                    
                    # 简单的点路径解析
                    parts = self.source_name.strip('$').strip('.').split('.')
                    data = json_data
                    for part in parts:
                        if part in data:
                            data = data[part]
                        else:
                            data = None
                            break
                    
                    if data and isinstance(data, str):
                        token = data
                        logger.debug(f"从JSON响应提取CSRF令牌: {self.source_name}={token}")
                    else:
                        logger.debug(f"JSON路径未找到CSRF令牌或值不是字符串: {self.source_name}")
                        
                except Exception as e:
                    logger.error(f"从JSON响应提取CSRF令牌失败: {str(e)}")
            # 如果是HTML响应，可以尝试使用CSS选择器或XPath
            else:
                logger.debug("响应不是JSON格式，无法使用JSON路径提取CSRF令牌")
                # 这里可以添加HTML解析逻辑，例如使用Beautiful Soup或lxml
        
        # 更新令牌
        if token:
            logger.info(f"成功提取CSRF令牌: {token}")
            self.csrf_token = token
        
    def clean_auth_state(self, request_kwargs: Dict[str, Any] = None) -> Dict[str, Any]:
        """清理认证状态
        
        清理CSRF认证状态，包括令牌和会话。
        
        Args:
            request_kwargs: 请求参数
            
        Returns:
            更新后的请求参数
        """
        logger.info("清理CSRF认证状态")
        
        # 重置CSRF令牌
        self.csrf_token = None
        
        # 清理会话Cookie
        self._session.cookies.clear()
        
        # 处理请求参数
        if request_kwargs:
            if "headers" in request_kwargs:
                # 移除CSRF相关头
                csrf_headers = [self.header_name, 'X-CSRF-Token', 'csrf-token', 'CSRF-Token']
                for header in csrf_headers:
                    if header in request_kwargs["headers"]:
                        request_kwargs["headers"].pop(header)
                        logger.debug(f"已移除请求头: {header}")
                        
        return request_kwargs if request_kwargs else {}


# 使用示例
def register_csrf_auth_providers():
    """注册CSRF认证提供者实例"""
    
    # 从头中提取CSRF令牌
    register_auth_provider(
        "csrf_header_auth", 
        CSRFAuthProvider,
        token_source="header",
        source_name="X-CSRF-Token",
        header_name="X-CSRF-Token"
    )
    
    # 从Cookie中提取CSRF令牌
    register_auth_provider(
        "csrf_cookie_auth", 
        CSRFAuthProvider,
        token_source="cookie",
        source_name="csrf_token",
        header_name="X-CSRF-Token"
    )
    
    # 从JSON响应体中提取CSRF令牌
    register_auth_provider(
        "csrf_json_auth", 
        CSRFAuthProvider,
        token_source="body",
        source_name="data.security.csrf_token",
        header_name="X-CSRF-Token"
    )
    
    # 使用正则表达式从HTML响应体中提取CSRF令牌
    register_auth_provider(
        "csrf_html_auth", 
        CSRFAuthProvider,
        token_source="body",
        header_name="X-CSRF-Token",
        regex_pattern=r'<meta name="csrf-token" content="([^"]+)">'
    )
    
    logger.info("已注册CSRF认证提供者")


# 如果此模块被直接运行，注册CSRF认证提供者
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 注册提供者
    register_csrf_auth_providers() 