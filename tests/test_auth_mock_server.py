#!/usr/bin/env python3
"""
授权测试专用Mock HTTP服务器

提供各种标准授权方式的模拟实现：
1. Basic Authentication (RFC 7617)
2. Bearer Token Authentication (RFC 6750)
3. API Key Authentication (常见实现)
4. OAuth2 Client Credentials (RFC 6749)
5. Digest Authentication (RFC 7616)
6. Custom Authentication
"""

import json
import time
import base64
import hashlib
import hmac
import secrets
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuthMockHTTPRequestHandler(BaseHTTPRequestHandler):
    """授权测试Mock HTTP请求处理器"""
    
    # 模拟用户数据库
    _users = {
        'admin': {'password': 'admin123', 'role': 'admin'},
        'user1': {'password': 'password1', 'role': 'user'},
        'test': {'password': 'test123', 'role': 'user'},
    }
    
    # 模拟API Key数据库
    _api_keys = {
        'test_api_key_123': {'user': 'admin', 'scope': ['read', 'write']},
        'readonly_key_456': {'user': 'user1', 'scope': ['read']},
        'dev_key_789': {'user': 'test', 'scope': ['read', 'write', 'admin']},
    }
    
    # Bearer Token数据库
    _bearer_tokens = {
        'valid_bearer_token_123': {'user': 'admin', 'expires': time.time() + 3600},
        'expired_token_456': {'user': 'user1', 'expires': time.time() - 3600},
        'test_token_789': {'user': 'test', 'expires': time.time() + 3600},
    }
    
    # OAuth2 客户端数据库
    _oauth_clients = {
        'test_client_id': {
            'secret': 'test_client_secret',
            'scope': ['read', 'write'],
            'grant_types': ['client_credentials', 'password']
        },
        'readonly_client': {
            'secret': 'readonly_secret',
            'scope': ['read'],
            'grant_types': ['client_credentials']
        }
    }
    
    # OAuth2 生成的token存储
    _oauth_tokens = {}
    
    # Digest认证相关
    _digest_realm = "TestRealm"
    _digest_nonces = {}
    
    def log_message(self, format, *args):
        """重写日志方法，使用标准日志"""
        logger.info(f"{self.address_string()} - {format % args}")
    
    def _send_response(self, status_code, data=None, headers=None):
        """发送响应的辅助方法"""
        self.send_response(status_code)
        
        # 设置默认头
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 
                        'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 
                        'Content-Type, Authorization, X-API-Key, X-Custom-Auth')
        
        # 设置自定义头
        if headers:
            for key, value in headers.items():
                self.send_header(key, value)
        
        self.end_headers()
        
        # 发送数据
        if data:
            response_data = json.dumps(data, ensure_ascii=False)
            self.wfile.write(response_data.encode('utf-8'))
    
    def _send_auth_challenge(self, auth_type='basic'):
        """发送授权质询"""
        if auth_type == 'basic':
            self._send_response(401, 
                {'error': 'Unauthorized', 'message': 'Basic authentication required'},
                {'WWW-Authenticate': 'Basic realm="TestRealm"'})
        elif auth_type == 'bearer':
            self._send_response(401,
                {'error': 'Unauthorized', 'message': 'Bearer token required'},
                {'WWW-Authenticate': 'Bearer realm="TestRealm"'})
        elif auth_type == 'digest':
            nonce = secrets.token_hex(16)
            self._digest_nonces[nonce] = time.time()
            challenge = f'Digest realm="{self._digest_realm}", nonce="{nonce}", algorithm="MD5", qop="auth"'
            self._send_response(401,
                {'error': 'Unauthorized', 'message': 'Digest authentication required'},
                {'WWW-Authenticate': challenge})
        else:
            self._send_response(401, {'error': 'Unauthorized'})
    
    def _parse_basic_auth(self, auth_header):
        """解析Basic认证头"""
        try:
            scheme, credentials = auth_header.split(' ', 1)
            if scheme.lower() != 'basic':
                return None, None
            
            decoded = base64.b64decode(credentials).decode('utf-8')
            username, password = decoded.split(':', 1)
            return username, password
        except Exception as e:
            logger.warning(f"Basic认证解析失败: {e}")
            return None, None
    
    def _parse_bearer_token(self, auth_header):
        """解析Bearer Token"""
        try:
            scheme, token = auth_header.split(' ', 1)
            if scheme.lower() != 'bearer':
                return None
            return token
        except Exception as e:
            logger.warning(f"Bearer Token解析失败: {e}")
            return None
    
    def _parse_digest_auth(self, auth_header):
        """解析Digest认证头"""
        try:
            scheme, credentials = auth_header.split(' ', 1)
            if scheme.lower() != 'digest':
                return None
            
            # 解析Digest参数
            params = {}
            for item in credentials.split(','):
                key, value = item.strip().split('=', 1)
                params[key] = value.strip('"')
            
            return params
        except Exception as e:
            logger.warning(f"Digest认证解析失败: {e}")
            return None
    
    def _validate_basic_auth(self, username, password):
        """验证Basic认证"""
        if username in self._users:
            return self._users[username]['password'] == password
        return False
    
    def _validate_bearer_token(self, token):
        """验证Bearer Token"""
        if token in self._bearer_tokens:
            token_info = self._bearer_tokens[token]
            return time.time() < token_info['expires']
        return False
    
    def _validate_api_key(self, api_key):
        """验证API Key"""
        return api_key in self._api_keys
    
    def _validate_digest_auth(self, params, method, uri):
        """验证Digest认证"""
        try:
            username = params.get('username')
            nonce = params.get('nonce')
            response = params.get('response')
            
            if not all([username, nonce, response]):
                return False
            
            # 检查nonce是否有效
            if nonce not in self._digest_nonces:
                return False
            
            # 检查用户是否存在
            if username not in self._users:
                return False
            
            password = self._users[username]['password']
            
            # 计算期望的响应
            ha1 = hashlib.md5(f"{username}:{self._digest_realm}:{password}".encode()).hexdigest()
            ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
            expected_response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
            
            return response.lower() == expected_response.lower()
        except Exception as e:
            logger.warning(f"Digest认证验证失败: {e}")
            return False
    
    def _get_user_from_auth(self):
        """从授权头或查询参数获取用户信息"""
        auth_header = self.headers.get('Authorization')
        api_key = self.headers.get('X-API-Key')
        custom_auth = self.headers.get('X-Custom-Auth')
        
        # 解析查询参数中的API Key
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        query_api_key = query_params.get('api_key', [None])[0]
        
        if auth_header:
            if auth_header.lower().startswith('basic '):
                username, password = self._parse_basic_auth(auth_header)
                if username and self._validate_basic_auth(username, password):
                    return {'username': username, 'auth_type': 'basic'}
            
            elif auth_header.lower().startswith('bearer '):
                token = self._parse_bearer_token(auth_header)
                if token and self._validate_bearer_token(token):
                    token_info = self._bearer_tokens[token]
                    return {'username': token_info['user'], 'auth_type': 'bearer'}
            
            elif auth_header.lower().startswith('digest '):
                params = self._parse_digest_auth(auth_header)
                if params and self._validate_digest_auth(params, self.command, self.path):
                    return {'username': params['username'], 'auth_type': 'digest'}
        
        elif api_key and self._validate_api_key(api_key):
            api_info = self._api_keys[api_key]
            return {'username': api_info['user'], 'auth_type': 'api_key'}
        
        elif query_api_key and self._validate_api_key(query_api_key):
            # 从查询参数中获取API Key
            api_info = self._api_keys[query_api_key]
            return {'username': api_info['user'], 'auth_type': 'api_key'}
        
        elif custom_auth:
            # 自定义认证逻辑
            if custom_auth == 'custom_auth':
                # 检查X-Auth-Source头
                auth_source = self.headers.get('X-Auth-Source')
                if auth_source:
                    try:
                        decoded = base64.b64decode(auth_source).decode('utf-8')
                        username, password = decoded.split(':', 1)
                        if self._validate_basic_auth(username, password):
                            return {'username': username, 'auth_type': 'custom'}
                    except Exception:
                        pass
        
        return None
    
    def do_OPTIONS(self):
        """处理OPTIONS请求（CORS预检）"""
        self._send_response(200)
    
    def do_POST(self):
        """处理POST请求"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        if path == '/oauth/token':
            self._handle_oauth_token()
        elif path.startswith('/auth/'):
            self._handle_auth_endpoints(path)
        else:
            self._handle_protected_resource(path)
    
    def do_GET(self):
        """处理GET请求"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        
        logger.info(f"GET {path} - Query: {query_params}")
        
        if path == '/health':
            self._handle_health_check()
        elif path == '/public':
            self._handle_public_endpoint()
        elif path.startswith('/auth/'):
            self._handle_auth_endpoints(path)
        else:
            self._handle_protected_resource(path)
    
    def _handle_oauth_token(self):
        """处理OAuth2 token端点"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            # 解析表单数据
            if self.headers.get('Content-Type', '').startswith('application/x-www-form-urlencoded'):
                from urllib.parse import parse_qs
                form_data = parse_qs(post_data.decode('utf-8'))
                # 转换为单值字典
                params = {k: v[0] if v else '' for k, v in form_data.items()}
            else:
                params = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception as e:
            self._send_response(400, {'error': 'invalid_request', 'error_description': f'Invalid request format: {e}'})
            return
        
        grant_type = params.get('grant_type')
        client_id = params.get('client_id')
        client_secret = params.get('client_secret')
        
        # 验证客户端
        if client_id not in self._oauth_clients:
            self._send_response(401, {'error': 'invalid_client', 'error_description': 'Unknown client'})
            return
        
        client = self._oauth_clients[client_id]
        if client['secret'] != client_secret:
            self._send_response(401, {'error': 'invalid_client', 'error_description': 'Invalid client secret'})
            return
        
        if grant_type not in client['grant_types']:
            self._send_response(400, {'error': 'unsupported_grant_type'})
            return
        
        # 生成访问令牌
        access_token = f"oauth_{secrets.token_hex(16)}"
        expires_in = 3600  # 1小时
        
        # 存储令牌
        self._oauth_tokens[access_token] = {
            'client_id': client_id,
            'scope': client['scope'],
            'expires': time.time() + expires_in
        }
        
        response_data = {
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': expires_in,
            'scope': ' '.join(client['scope'])
        }
        
        self._send_response(200, response_data)
    
    def _handle_auth_endpoints(self, path):
        """处理认证相关端点"""
        if path == '/auth/basic':
            self._handle_basic_auth_test()
        elif path == '/auth/bearer':
            self._handle_bearer_auth_test()
        elif path == '/auth/apikey':
            self._handle_apikey_auth_test()
        elif path == '/auth/digest':
            self._handle_digest_auth_test()
        elif path == '/auth/oauth':
            self._handle_oauth_auth_test()
        elif path == '/auth/custom':
            self._handle_custom_auth_test()
        elif path == '/auth/mixed':
            self._handle_mixed_auth_test()
        else:
            self._send_response(404, {'error': 'Not Found'})
    
    def _handle_basic_auth_test(self):
        """测试Basic认证"""
        user_info = self._get_user_from_auth()
        if not user_info or user_info['auth_type'] != 'basic':
            self._send_auth_challenge('basic')
            return
        
        self._send_response(200, {
            'message': 'Basic authentication successful',
            'user': user_info['username'],
            'auth_type': 'basic',
            'timestamp': time.time()
        })
    
    def _handle_bearer_auth_test(self):
        """测试Bearer Token认证"""
        user_info = self._get_user_from_auth()
        if not user_info or user_info['auth_type'] != 'bearer':
            self._send_auth_challenge('bearer')
            return
        
        self._send_response(200, {
            'message': 'Bearer token authentication successful',
            'user': user_info['username'],
            'auth_type': 'bearer',
            'timestamp': time.time()
        })
    
    def _handle_apikey_auth_test(self):
        """测试API Key认证"""
        user_info = self._get_user_from_auth()
        if not user_info or user_info['auth_type'] != 'api_key':
            self._send_response(401, {
                'error': 'Unauthorized',
                'message': 'Valid API key required in X-API-Key header or api_key query parameter'
            })
            return
        
        # 获取API Key（可能来自Header或查询参数）
        api_key = self.headers.get('X-API-Key')
        if not api_key:
            # 从查询参数获取
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            api_key = query_params.get('api_key', [None])[0]
        
        api_info = self._api_keys[api_key]
        
        self._send_response(200, {
            'message': 'API key authentication successful',
            'user': user_info['username'],
            'auth_type': 'api_key',
            'scope': api_info['scope'],
            'timestamp': time.time()
        })
    
    def _handle_digest_auth_test(self):
        """测试Digest认证"""
        user_info = self._get_user_from_auth()
        if not user_info or user_info['auth_type'] != 'digest':
            self._send_auth_challenge('digest')
            return
        
        self._send_response(200, {
            'message': 'Digest authentication successful',
            'user': user_info['username'],
            'auth_type': 'digest',
            'timestamp': time.time()
        })
    
    def _handle_oauth_auth_test(self):
        """测试OAuth2认证"""
        auth_header = self.headers.get('Authorization')
        if not auth_header or not auth_header.lower().startswith('bearer '):
            self._send_response(401, {
                'error': 'invalid_token',
                'error_description': 'Bearer token required'
            })
            return
        
        token = self._parse_bearer_token(auth_header)
        if token not in self._oauth_tokens:
            self._send_response(401, {
                'error': 'invalid_token',
                'error_description': 'Invalid or expired token'
            })
            return
        
        token_info = self._oauth_tokens[token]
        if time.time() > token_info['expires']:
            self._send_response(401, {
                'error': 'invalid_token',
                'error_description': 'Token expired'
            })
            return
        
        self._send_response(200, {
            'message': 'OAuth2 authentication successful',
            'client_id': token_info['client_id'],
            'scope': token_info['scope'],
            'auth_type': 'oauth2',
            'timestamp': time.time()
        })
    
    def _handle_custom_auth_test(self):
        """测试自定义认证"""
        user_info = self._get_user_from_auth()
        if not user_info or user_info['auth_type'] != 'custom':
            self._send_response(401, {
                'error': 'Unauthorized',
                'message': 'Custom authentication required (X-Custom-Auth: custom_auth and X-Auth-Source headers)'
            })
            return
        
        self._send_response(200, {
            'message': 'Custom authentication successful',
            'user': user_info['username'],
            'auth_type': 'custom',
            'timestamp': time.time()
        })
    
    def _handle_mixed_auth_test(self):
        """测试混合认证（支持多种认证方式）"""
        user_info = self._get_user_from_auth()
        if not user_info:
            self._send_response(401, {
                'error': 'Unauthorized',
                'message': 'Authentication required (Basic, Bearer, API Key, or Custom)'
            }, {
                'WWW-Authenticate': 'Basic realm="TestRealm", Bearer realm="TestRealm"'
            })
            return
        
        self._send_response(200, {
            'message': f'{user_info["auth_type"].title()} authentication successful',
            'user': user_info['username'],
            'auth_type': user_info['auth_type'],
            'timestamp': time.time()
        })
    
    def _handle_protected_resource(self, path):
        """处理受保护的资源"""
        user_info = self._get_user_from_auth()
        if not user_info:
            self._send_response(401, {
                'error': 'Unauthorized',
                'message': 'Authentication required'
            }, {
                'WWW-Authenticate': 'Basic realm="TestRealm", Bearer realm="TestRealm"'
            })
            return
        
        # 模拟资源数据
        resource_data = {
            'path': path,
            'user': user_info['username'],
            'auth_type': user_info['auth_type'],
            'timestamp': time.time(),
            'data': {
                'message': f'Protected resource accessed by {user_info["username"]}',
                'resource_id': path.split('/')[-1] if '/' in path else 'default'
            }
        }
        
        self._send_response(200, resource_data)
    
    def _handle_public_endpoint(self):
        """处理公共端点（无需认证）"""
        self._send_response(200, {
            'message': 'Public endpoint - no authentication required',
            'timestamp': time.time()
        })
    
    def _handle_health_check(self):
        """处理健康检查"""
        self._send_response(200, {
            'status': 'healthy',
            'timestamp': time.time(),
            'server': 'auth-mock-server',
            'version': '1.0.0',
            'supported_auth': ['basic', 'bearer', 'api_key', 'oauth2', 'digest', 'custom']
        })


class AuthMockServer:
    """授权测试Mock服务器管理类"""
    
    def __init__(self, host='localhost', port=8889):
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
    
    def start(self):
        """启动服务器"""
        self.server = HTTPServer((self.host, self.port), 
                                AuthMockHTTPRequestHandler)
        self.server_thread = threading.Thread(
            target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        logger.info(f"授权测试Mock服务器已启动: http://{self.host}:{self.port}")
        logger.info("支持的授权方式和端点:")
        logger.info("  GET  /health - 健康检查")
        logger.info("  GET  /public - 公共端点（无需认证）")
        logger.info("  GET  /auth/basic - Basic认证测试")
        logger.info("  GET  /auth/bearer - Bearer Token认证测试")
        logger.info("  GET  /auth/apikey - API Key认证测试")
        logger.info("  GET  /auth/digest - Digest认证测试")
        logger.info("  GET  /auth/oauth - OAuth2认证测试")
        logger.info("  GET  /auth/custom - 自定义认证测试")
        logger.info("  GET  /auth/mixed - 混合认证测试")
        logger.info("  POST /oauth/token - OAuth2 Token端点")
        logger.info("  ANY  /api/* - 受保护资源")
        logger.info("")
        logger.info("测试凭据:")
        logger.info("  Basic Auth: admin/admin123, user1/password1, test/test123")
        logger.info("  Bearer Token: valid_bearer_token_123, test_token_789")
        logger.info("  API Key: test_api_key_123, readonly_key_456, dev_key_789")
        logger.info("  OAuth2 Client: test_client_id/test_client_secret")
    
    def stop(self):
        """停止服务器"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.info("授权测试Mock服务器已停止")


def main():
    """主函数 - 启动授权测试mock服务器"""
    server = AuthMockServer()
    
    try:
        server.start()
        
        # 保持服务器运行
        print("授权测试Mock服务器正在运行...")
        print("按 Ctrl+C 停止服务器")
        
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n正在停止服务器...")
        server.stop()
        print("服务器已停止")


if __name__ == "__main__":
    main() 