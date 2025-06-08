#!/usr/bin/env python3
"""
Mock HTTP服务器，用于测试重试逻辑

提供各种模拟场景：
1. 延迟响应
2. 失败后成功
3. 状态变化
4. 随机失败
"""

import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockHTTPRequestHandler(BaseHTTPRequestHandler):
    """Mock HTTP请求处理器"""
    
    # 全局状态存储
    _state = {
        'task_status': 'pending',  # 任务状态
        'request_count': {},       # 请求计数
        'user_data': {},          # 用户数据
        'order_status': 'processing'  # 订单状态
    }
    
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
                        'Content-Type, Authorization')
        
        # 设置自定义头
        if headers:
            for key, value in headers.items():
                self.send_header(key, value)
        
        self.end_headers()
        
        # 发送数据
        if data:
            response_data = json.dumps(data, ensure_ascii=False)
            self.wfile.write(response_data.encode('utf-8'))
    
    def _get_request_key(self, path):
        """获取请求的唯一键"""
        return f"{self.command}:{path}"
    
    def _increment_request_count(self, path):
        """增加请求计数"""
        key = self._get_request_key(path)
        count = self._state['request_count'].get(key, 0) + 1
        self._state['request_count'][key] = count
        return count
    
    def do_OPTIONS(self):
        """处理OPTIONS请求（CORS预检）"""
        self._send_response(200)
    
    def do_GET(self):
        """处理GET请求"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        
        logger.info(f"GET {path} - Query: {query_params}")
        
        if path == '/api/task/status':
            self._handle_task_status()
        elif path == '/api/retry/fail-then-success':
            self._handle_fail_then_success()
        elif path == '/api/retry/random-fail':
            self._handle_random_fail()
        elif path == '/api/delay':
            self._handle_delay(query_params)
        elif path == '/api/order/status':
            self._handle_order_status()
        elif path == '/api/user/profile':
            self._handle_user_profile()
        elif path == '/api/health':
            self._handle_health_check()
        elif path == '/api/reset':
            self._handle_reset()
        else:
            self._send_response(404, {'error': 'Not Found', 'path': path})
    
    def do_POST(self):
        """处理POST请求"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # 读取请求体
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            request_data = (json.loads(post_data.decode('utf-8')) 
                          if post_data else {})
        except json.JSONDecodeError:
            request_data = {}
        
        logger.info(f"POST {path} - Data: {request_data}")
        
        if path == '/api/task/start':
            self._handle_start_task(request_data)
        elif path == '/api/user/create':
            self._handle_create_user(request_data)
        elif path == '/api/order/create':
            self._handle_create_order(request_data)
        else:
            self._send_response(404, {'error': 'Not Found', 'path': path})
    
    def _handle_task_status(self):
        """处理任务状态查询 - 模拟状态变化"""
        count = self._increment_request_count('/api/task/status')
        
        # 前3次返回pending，第4次开始返回completed
        if count <= 3:
            status = 'pending'
            progress = min(count * 30, 90)
        else:
            status = 'completed'
            progress = 100
        
        response_data = {
            'task_id': 'task-123',
            'status': status,
            'progress': progress,
            'request_count': count,
            'message': f'任务状态: {status}'
        }
        
        self._send_response(200, response_data)
    
    def _handle_fail_then_success(self):
        """处理失败后成功的场景"""
        count = self._increment_request_count('/api/retry/fail-then-success')
        
        # 前2次返回500错误，第3次开始返回成功
        if count <= 2:
            self._send_response(500, {
                'error': 'Internal Server Error',
                'message': f'模拟失败 (尝试 {count}/3)',
                'retry_after': 1
            })
        else:
            self._send_response(200, {
                'success': True,
                'message': f'成功！(第 {count} 次尝试)',
                'data': {'result': 'success', 'attempts': count}
            })
    
    def _handle_random_fail(self):
        """处理随机失败的场景"""
        import random
        count = self._increment_request_count('/api/retry/random-fail')
        
        # 30%的概率失败
        if random.random() < 0.3:
            self._send_response(503, {
                'error': 'Service Temporarily Unavailable',
                'message': f'随机失败 (尝试 {count})',
                'retry_after': 1
            })
        else:
            self._send_response(200, {
                'success': True,
                'message': f'随机成功！(第 {count} 次尝试)',
                'data': {'result': 'success', 'attempts': count}
            })
    
    def _handle_delay(self, query_params):
        """处理延迟响应"""
        delay = float(query_params.get('seconds', ['1'])[0])
        
        logger.info(f"延迟 {delay} 秒...")
        time.sleep(delay)
        
        self._send_response(200, {
            'message': f'延迟 {delay} 秒后响应',
            'timestamp': time.time(),
            'delay_seconds': delay
        })
    
    def _handle_order_status(self):
        """处理订单状态查询 - 模拟订单状态变化"""
        count = self._increment_request_count('/api/order/status')
        
        # 订单状态变化：processing -> shipped -> delivered
        if count <= 2:
            status = 'processing'
        elif count <= 4:
            status = 'shipped'
        else:
            status = 'delivered'
        
        response_data = {
            'order_id': 'ORDER-2024-001',
            'status': status,
            'request_count': count,
            'tracking_number': ('TN123456789' if status != 'processing' 
                              else None),
            'estimated_delivery': ('2024-01-15' if status == 'shipped' 
                                 else None)
        }
        
        self._send_response(200, response_data)
    
    def _handle_user_profile(self):
        """处理用户资料查询 - 模拟数据逐步完善"""
        count = self._increment_request_count('/api/user/profile')
        
        # 用户数据逐步完善
        profile = {
            'user_id': 'user-123',
            'username': 'testuser',
            'request_count': count
        }
        
        if count >= 2:
            profile['email'] = 'testuser@example.com'
        if count >= 3:
            profile['phone'] = '138-1234-5678'
        if count >= 4:
            profile['address'] = '北京市朝阳区'
        
        self._send_response(200, profile)
    
    def _handle_start_task(self, request_data):
        """处理启动任务"""
        task_name = request_data.get('task_name', 'default_task')
        
        # 重置任务状态
        self._state['task_status'] = 'pending'
        
        response_data = {
            'task_id': 'task-123',
            'task_name': task_name,
            'status': 'started',
            'message': '任务已启动'
        }
        
        self._send_response(201, response_data)
    
    def _handle_create_user(self, request_data):
        """处理创建用户"""
        count = self._increment_request_count('/api/user/create')
        
        # 模拟创建用户可能失败的情况
        if count == 1 and not request_data.get('force_success'):
            self._send_response(400, {
                'error': 'Validation Error',
                'message': '用户名已存在',
                'code': 'USER_EXISTS'
            })
        else:
            user_data = {
                'user_id': f'user-{count}',
                'username': request_data.get('username', 'default_user'),
                'email': request_data.get('email', 'user@example.com'),
                'created_at': time.time(),
                'attempt': count
            }
            
            self._send_response(201, user_data)
    
    def _handle_create_order(self, request_data):
        """处理创建订单"""
        count = self._increment_request_count('/api/order/create')
        
        # 重置订单状态
        self._state['order_status'] = 'processing'
        
        order_data = {
            'order_id': f'ORDER-2024-{count:03d}',
            'status': 'created',
            'items': request_data.get('items', []),
            'total_amount': request_data.get('total_amount', 100.0),
            'created_at': time.time(),
            'attempt': count
        }
        
        self._send_response(201, order_data)
    
    def _handle_health_check(self):
        """处理健康检查"""
        self._send_response(200, {
            'status': 'healthy',
            'timestamp': time.time(),
            'server': 'mock-server',
            'version': '1.0.0'
        })
    
    def _handle_reset(self):
        """重置服务器状态"""
        self._state['request_count'].clear()
        self._state['task_status'] = 'pending'
        self._state['order_status'] = 'processing'
        self._state['user_data'].clear()
        
        self._send_response(200, {
            'message': '服务器状态已重置',
            'timestamp': time.time()
        })


class MockServer:
    """Mock服务器管理类"""
    
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
    
    def start(self):
        """启动服务器"""
        self.server = HTTPServer((self.host, self.port), 
                                MockHTTPRequestHandler)
        self.server_thread = threading.Thread(
            target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        logger.info(f"Mock服务器已启动: http://{self.host}:{self.port}")
        logger.info("可用的API端点:")
        logger.info("  GET  /api/health - 健康检查")
        logger.info("  GET  /api/task/status - 任务状态查询（模拟状态变化）")
        logger.info("  POST /api/task/start - 启动任务")
        logger.info("  GET  /api/retry/fail-then-success - 失败后成功")
        logger.info("  GET  /api/retry/random-fail - 随机失败")
        logger.info("  GET  /api/delay?seconds=N - 延迟响应")
        logger.info("  GET  /api/order/status - 订单状态查询")
        logger.info("  POST /api/order/create - 创建订单")
        logger.info("  GET  /api/user/profile - 用户资料查询")
        logger.info("  POST /api/user/create - 创建用户")
        logger.info("  GET  /api/reset - 重置服务器状态")
    
    def stop(self):
        """停止服务器"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.info("Mock服务器已停止")
    
    def reset(self):
        """重置服务器状态"""
        import requests
        try:
            url = f"http://{self.host}:{self.port}/api/reset"
            requests.get(url, timeout=5)
            logger.info("服务器状态已重置")
        except Exception as e:
            logger.warning(f"重置服务器状态失败: {e}")


def main():
    """主函数 - 启动mock服务器"""
    server = MockServer()
    
    try:
        server.start()
        
        # 保持服务器运行
        print("Mock服务器正在运行...")
        print("按 Ctrl+C 停止服务器")
        
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n正在停止服务器...")
        server.stop()
        print("服务器已停止")


if __name__ == "__main__":
    main() 