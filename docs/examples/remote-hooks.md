# 远程Hook机制示例

本示例展示如何使用pytest-dsl的远程服务器Hook机制来扩展服务器功能，包括自定义授权、性能监控和安全控制。

## 学习目标

通过这个示例，您将学会：

- 如何创建和注册Hook函数
- 如何实现自定义授权提供者
- 如何进行性能监控和日志记录
- 如何加载和使用扩展

## 示例结构

```
remote-hooks-example/
├── extensions/
│   ├── auth_extension.py      # 自定义授权扩展
│   ├── monitoring_extension.py # 性能监控扩展
│   └── security_extension.py   # 安全控制扩展
├── config/
│   └── server_config.yaml     # 服务器配置
├── tests/
│   ├── test_auth.dsl          # 授权测试
│   ├── test_monitoring.dsl    # 监控测试
│   └── test_security.dsl      # 安全测试
├── start_server.sh            # 启动脚本
└── run_tests.sh              # 测试脚本
```

## 自定义授权扩展

### 创建授权扩展

`extensions/auth_extension.py`：

```python
"""自定义授权扩展示例"""
import logging
from pytest_dsl.remote.hook_manager import (
    register_startup_hook,
    register_before_keyword_hook,
    register_after_keyword_hook
)
from pytest_dsl.core.auth_provider import AuthProvider, register_auth_provider

logger = logging.getLogger(__name__)

class CustomTestAuthProvider(AuthProvider):
    """自定义测试授权提供者"""
    
    def __init__(self, **config):
        self.token_var = config.get('token_var', 'test_token')
        self.auth_header = config.get('auth_header', 'Authorization')
        self.token_prefix = config.get('token_prefix', 'Bearer')
        self.shared_variables = {}
        logger.info(f"初始化自定义授权提供者: token_var={self.token_var}")

    def set_shared_variables(self, shared_variables):
        """设置共享变量引用"""
        self.shared_variables = shared_variables

    def apply_auth(self, base_url, request_kwargs):
        """应用授权到HTTP请求"""
        token = self.shared_variables.get(self.token_var)
        if token:
            if "headers" not in request_kwargs:
                request_kwargs["headers"] = {}
            auth_value = f"{self.token_prefix} {token}"
            request_kwargs["headers"][self.auth_header] = auth_value
            logger.info(f"应用自定义授权: {self.auth_header}={auth_value}")
        else:
            logger.warning(f"未找到授权token: {self.token_var}")
        return request_kwargs

@register_startup_hook
def setup_custom_auth(context):
    """注册自定义授权提供者"""
    register_auth_provider("custom_auth", CustomTestAuthProvider)
    logger.info("自定义授权提供者注册成功")
    
    # 设置默认授权类型
    shared_variables = context.get('shared_variables')
    if 'auth_type' not in shared_variables:
        shared_variables['auth_type'] = 'custom_auth'

@register_before_keyword_hook
def inject_custom_auth(context):
    """为HTTP请求注入自定义授权"""
    keyword_name = context.get('keyword_name')
    if keyword_name != 'HTTP请求':
        return
    
    shared_variables = context.get('shared_variables')
    auth_type = shared_variables.get('custom_auth_type')
    
    if auth_type == 'custom_auth':
        logger.info("为HTTP请求注入自定义授权")
        # 这里可以添加更复杂的授权逻辑
        # 比如token刷新、权限检查等

@register_after_keyword_hook
def log_auth_result(context):
    """记录授权结果"""
    keyword_name = context.get('keyword_name')
    if keyword_name == 'HTTP请求':
        keyword_result = context.get('keyword_result')
        if keyword_result and isinstance(keyword_result, dict):
            status_code = keyword_result.get('status_code')
            if status_code == 401:
                logger.warning("HTTP请求返回401，可能是授权失败")
            elif status_code == 403:
                logger.warning("HTTP请求返回403，可能是权限不足")
```

### 性能监控扩展

`extensions/monitoring_extension.py`：

```python
"""性能监控扩展示例"""
import time
import json
import logging
from datetime import datetime
from pytest_dsl.remote.hook_manager import (
    register_startup_hook,
    register_shutdown_hook,
    register_before_keyword_hook,
    register_after_keyword_hook
)

logger = logging.getLogger(__name__)

# 全局性能数据
performance_data = {
    'server_start_time': None,
    'keyword_executions': [],
    'performance_metrics': {}
}

@register_startup_hook
def setup_monitoring(context):
    """初始化性能监控"""
    performance_data['server_start_time'] = datetime.now()
    logger.info("性能监控系统启动")

@register_before_keyword_hook
def start_performance_tracking(context):
    """开始性能跟踪"""
    keyword_name = context.get('keyword_name')
    start_time = time.time()
    
    # 保存开始时间到上下文
    context.set('perf_start_time', start_time)
    context.set('perf_start_datetime', datetime.now())
    
    logger.info(f"开始执行关键字: {keyword_name}")

@register_after_keyword_hook
def end_performance_tracking(context):
    """结束性能跟踪并记录数据"""
    keyword_name = context.get('keyword_name')
    start_time = context.get('perf_start_time')
    start_datetime = context.get('perf_start_datetime')
    
    if start_time:
        end_time = time.time()
        duration = end_time - start_time
        
        # 记录执行数据
        execution_data = {
            'keyword_name': keyword_name,
            'start_time': start_datetime.isoformat(),
            'end_time': datetime.now().isoformat(),
            'duration_seconds': duration,
            'success': True  # 可以根据实际结果判断
        }
        
        performance_data['keyword_executions'].append(execution_data)
        
        # 更新性能指标
        if keyword_name not in performance_data['performance_metrics']:
            performance_data['performance_metrics'][keyword_name] = {
                'count': 0,
                'total_duration': 0,
                'min_duration': float('inf'),
                'max_duration': 0,
                'avg_duration': 0
            }
        
        metrics = performance_data['performance_metrics'][keyword_name]
        metrics['count'] += 1
        metrics['total_duration'] += duration
        metrics['min_duration'] = min(metrics['min_duration'], duration)
        metrics['max_duration'] = max(metrics['max_duration'], duration)
        metrics['avg_duration'] = metrics['total_duration'] / metrics['count']
        
        logger.info(f"关键字 {keyword_name} 执行完成，耗时: {duration:.3f}秒")

@register_shutdown_hook
def save_performance_data(context):
    """保存性能数据"""
    try:
        # 计算服务器运行时间
        if performance_data['server_start_time']:
            server_uptime = datetime.now() - performance_data['server_start_time']
            performance_data['server_uptime_seconds'] = server_uptime.total_seconds()
        
        # 保存到文件
        with open('performance_report.json', 'w', encoding='utf-8') as f:
            json.dump(performance_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info("性能数据已保存到 performance_report.json")
        
        # 打印简要统计
        total_executions = len(performance_data['keyword_executions'])
        logger.info(f"总共执行了 {total_executions} 个关键字")
        
        for keyword, metrics in performance_data['performance_metrics'].items():
            logger.info(f"{keyword}: 执行{metrics['count']}次, "
                       f"平均耗时{metrics['avg_duration']:.3f}秒")
    
    except Exception as e:
        logger.error(f"保存性能数据失败: {e}")
```

### 安全控制扩展

`extensions/security_extension.py`：

```python
"""安全控制扩展示例"""
import logging
import ipaddress
from pytest_dsl.remote.hook_manager import (
    register_startup_hook,
    register_before_keyword_hook
)

logger = logging.getLogger(__name__)

# 安全配置
SECURITY_CONFIG = {
    'allowed_ips': ['127.0.0.1', '192.168.1.0/24'],
    'restricted_keywords': ['系统命令', '文件操作', '数据库操作'],
    'admin_tokens': ['admin_token_123', 'super_admin_456']
}

@register_startup_hook
def setup_security(context):
    """初始化安全控制"""
    logger.info("安全控制系统启动")
    logger.info(f"允许的IP范围: {SECURITY_CONFIG['allowed_ips']}")
    logger.info(f"受限关键字: {SECURITY_CONFIG['restricted_keywords']}")

@register_before_keyword_hook
def security_check(context):
    """执行安全检查"""
    keyword_name = context.get('keyword_name')
    shared_variables = context.get('shared_variables', {})
    
    # 模拟获取客户端IP（实际实现需要服务器支持）
    client_ip = shared_variables.get('client_ip', '127.0.0.1')
    
    # IP白名单检查
    if not is_ip_allowed(client_ip):
        error_msg = f"IP {client_ip} 不在允许列表中"
        logger.error(error_msg)
        raise PermissionError(error_msg)
    
    # 关键字权限检查
    if keyword_name in SECURITY_CONFIG['restricted_keywords']:
        user_token = shared_variables.get('admin_token')
        if not is_admin_user(user_token):
            error_msg = f"无权限执行受限关键字: {keyword_name}"
            logger.error(error_msg)
            raise PermissionError(error_msg)
        else:
            logger.info(f"管理员用户执行受限关键字: {keyword_name}")
    
    # 记录安全日志
    logger.info(f"安全检查通过 - IP: {client_ip}, 关键字: {keyword_name}")

def is_ip_allowed(ip_str):
    """检查IP是否在允许列表中"""
    try:
        client_ip = ipaddress.ip_address(ip_str)
        for allowed in SECURITY_CONFIG['allowed_ips']:
            if '/' in allowed:
                # 网络段
                if client_ip in ipaddress.ip_network(allowed):
                    return True
            else:
                # 单个IP
                if client_ip == ipaddress.ip_address(allowed):
                    return True
        return False
    except Exception as e:
        logger.error(f"IP检查失败: {e}")
        return False

def is_admin_user(token):
    """检查是否为管理员用户"""
    return token in SECURITY_CONFIG['admin_tokens']
```

## 配置文件

`config/server_config.yaml`：

```yaml
# 服务器基础配置
server:
  host: "0.0.0.0"
  port: 8270
  debug: true

# HTTP客户端配置
http_clients:
  default:
    base_url: "https://httpbin.org"
    timeout: 30
    headers:
      User-Agent: "pytest-dsl-remote-hooks-example/1.0"

# 扩展配置
extensions:
  auth:
    token_var: "test_token"
    auth_header: "Authorization"
    token_prefix: "Bearer"
  
  monitoring:
    enabled: true
    save_report: true
  
  security:
    ip_check_enabled: true
    keyword_restriction_enabled: true

# 测试变量
test_token: "example_token_123"
admin_token: "admin_token_123"
client_ip: "127.0.0.1"
```

## 测试用例

### 授权测试

`tests/test_auth.dsl`：

```python
@name: "自定义授权功能测试"
@description: "测试远程服务器的自定义授权扩展"
@remote: "http://localhost:8270/" as test_server

# 设置授权相关变量
custom_auth_type = "custom_auth"
test_token = "example_token_123"

[打印], 内容: "开始测试自定义授权功能"

# 测试带授权的HTTP请求
test_server|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /headers
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.headers.Authorization", "contains", "Bearer"]
        - ["jsonpath", "$.headers.Authorization", "contains", "example_token_123"]
''', 步骤名称: "测试授权头部注入"

# 测试无授权的请求
test_token = ""
test_server|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /headers
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "测试无授权请求"

[打印], 内容: "自定义授权功能测试完成"
```

### 性能监控测试

`tests/test_monitoring.dsl`：

```python
@name: "性能监控功能测试"
@description: "测试远程服务器的性能监控扩展"
@remote: "http://localhost:8270/" as test_server

[打印], 内容: "开始测试性能监控功能"

# 执行多个HTTP请求来生成性能数据
for i in range(1, 4) do
    test_server|[HTTP请求], 客户端: "default", 配置: '''
        method: GET
        url: /delay/1
        asserts:
            - ["status", "eq", 200]
    ''', 步骤名称: "性能测试请求 ${i}"
    
    # 短暂等待
    test_server|[等待], 秒数: 0.5
end

# 执行一些快速请求
for j in range(1, 6) do
    test_server|[HTTP请求], 客户端: "default", 配置: '''
        method: GET
        url: /get
        asserts:
            - ["status", "eq", 200]
    ''', 步骤名称: "快速请求 ${j}"
end

[打印], 内容: "性能监控功能测试完成"
```

### 安全控制测试

`tests/test_security.dsl`：

```python
@name: "安全控制功能测试"
@description: "测试远程服务器的安全控制扩展"
@remote: "http://localhost:8270/" as test_server

# 设置客户端IP（模拟）
client_ip = "127.0.0.1"

[打印], 内容: "开始测试安全控制功能"

# 测试正常请求（应该通过）
test_server|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /get
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "测试正常请求"

# 测试管理员权限（需要admin_token）
admin_token = "admin_token_123"
test_server|[打印], 内容: "模拟管理员操作"

[打印], 内容: "安全控制功能测试完成"
```

## 启动和运行脚本

### 启动脚本

`start_server.sh`：

```bash
#!/bin/bash

echo "启动带扩展的pytest-dsl远程服务器..."

# 设置环境变量
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 启动服务器并加载所有扩展
pytest-dsl-server \
    --host 0.0.0.0 \
    --port 8270 \
    --extensions extensions/ \
    --yaml-vars config/server_config.yaml \
    --debug

echo "服务器已停止"
```

### 测试脚本

`run_tests.sh`：

```bash
#!/bin/bash

echo "运行远程Hook机制测试..."

# 等待服务器启动
sleep 2

# 运行所有测试
echo "1. 运行授权测试..."
pytest-dsl tests/test_auth.dsl --yaml-vars config/server_config.yaml

echo "2. 运行性能监控测试..."
pytest-dsl tests/test_monitoring.dsl --yaml-vars config/server_config.yaml

echo "3. 运行安全控制测试..."
pytest-dsl tests/test_security.dsl --yaml-vars config/server_config.yaml

echo "所有测试完成！"

# 检查性能报告
if [ -f "performance_report.json" ]; then
    echo "性能报告已生成: performance_report.json"
    echo "性能数据摘要:"
    python3 -c "
import json
with open('performance_report.json', 'r') as f:
    data = json.load(f)
print(f'服务器运行时间: {data.get(\"server_uptime_seconds\", 0):.2f}秒')
print(f'总执行次数: {len(data.get(\"keyword_executions\", []))}')
for keyword, metrics in data.get('performance_metrics', {}).items():
    print(f'{keyword}: {metrics[\"count\"]}次, 平均{metrics[\"avg_duration\"]:.3f}秒')
"
fi
```

## 运行示例

### 1. 启动服务器

```bash
# 给脚本执行权限
chmod +x start_server.sh run_tests.sh

# 启动服务器（在一个终端中）
./start_server.sh
```

### 2. 运行测试

```bash
# 在另一个终端中运行测试
./run_tests.sh
```

### 3. 查看结果

测试完成后，您会看到：

- 服务器日志显示Hook的执行情况
- 性能报告文件 `performance_report.json`
- 测试执行结果

## 预期输出

### 服务器日志

```
INFO - 自定义授权提供者注册成功
INFO - 性能监控系统启动
INFO - 安全控制系统启动
INFO - 开始执行关键字: HTTP请求
INFO - 应用自定义授权: Authorization=Bearer example_token_123
INFO - 关键字 HTTP请求 执行完成，耗时: 1.234秒
```

### 性能报告

```json
{
  "server_start_time": "2024-01-15T10:30:00",
  "server_uptime_seconds": 45.67,
  "keyword_executions": [
    {
      "keyword_name": "HTTP请求",
      "start_time": "2024-01-15T10:30:05",
      "end_time": "2024-01-15T10:30:06",
      "duration_seconds": 1.234,
      "success": true
    }
  ],
  "performance_metrics": {
    "HTTP请求": {
      "count": 8,
      "total_duration": 12.345,
      "min_duration": 0.567,
      "max_duration": 2.345,
      "avg_duration": 1.543
    }
  }
}
```

## 扩展要点

### 1. Hook注册

- 使用正确的装饰器注册Hook
- 确保在startup hook中进行初始化
- 在shutdown hook中进行清理

### 2. 错误处理

- Hook中的异常不应影响关键字执行
- 使用适当的日志级别记录错误
- 提供降级处理机制

### 3. 性能考虑

- Hook应该轻量级，避免阻塞
- 只在必要时进行复杂处理
- 考虑异步处理长时间操作

### 4. 安全性

- 验证输入参数
- 避免在日志中记录敏感信息
- 实现适当的访问控制

## 下一步

现在您已经掌握了远程Hook机制的完整用法，可以：

1. **自定义扩展** - 根据实际需求开发专用扩展
2. **集成监控** - 与现有监控系统集成
3. **安全加固** - 实现更复杂的安全策略
4. **性能优化** - 基于监控数据优化测试性能

## 相关资源

- [远程服务器Hook机制指南](../guide/remote-hooks) - 详细的Hook机制文档
- [远程关键字基础](../guide/remote-keywords) - 远程关键字基础用法
- [自定义关键字开发](../guide/custom-keywords) - 开发自定义关键字 