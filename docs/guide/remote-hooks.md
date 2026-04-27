# 远程服务器Hook机制

pytest-dsl的远程服务器支持强大的Hook机制，允许您在服务器生命周期的关键点执行自定义逻辑，实现高度可扩展的分布式测试架构。

## 概述

Hook机制让您能够：

- 🔧 **服务器扩展** - 在启动/关闭时执行初始化和清理工作
- 🔐 **自定义授权** - 实现复杂的认证和授权逻辑
- 📊 **监控日志** - 记录关键字执行情况和性能数据
- 🔄 **数据处理** - 在关键字执行前后进行数据转换
- 🛡️ **安全控制** - 实现访问控制和安全策略

## Hook类型

### 服务器生命周期Hook

#### 启动Hook (SERVER_STARTUP)

在服务器启动时执行，用于初始化工作：

```python
from pytest_dsl.remote.hook_manager import register_startup_hook

@register_startup_hook
def setup_custom_providers(context):
    """服务器启动时的初始化"""
    server = context.get('server')
    shared_variables = context.get('shared_variables')
    
    print("服务器启动，执行初始化...")
    
    # 设置默认配置
    if 'auth_type' not in shared_variables:
        shared_variables['auth_type'] = 'default'
    
    # 初始化自定义组件
    setup_monitoring()
    setup_custom_auth_providers()
```

#### 关闭Hook (SERVER_SHUTDOWN)

在服务器关闭时执行，用于清理工作：

```python
from pytest_dsl.remote.hook_manager import register_shutdown_hook

@register_shutdown_hook
def cleanup_resources(context):
    """服务器关闭时的清理"""
    print("服务器关闭，执行清理...")
    
    # 清理资源
    cleanup_connections()
    save_logs()
```

### 关键字执行Hook

#### 执行前Hook (BEFORE_KEYWORD_EXECUTION)

在关键字执行前执行，可以修改参数或注入逻辑：

```python
from pytest_dsl.remote.hook_manager import register_before_keyword_hook

@register_before_keyword_hook
def preprocess_keyword(context):
    """关键字执行前的预处理"""
    keyword_name = context.get('keyword_name')
    keyword_args = context.get('keyword_args')
    
    # 记录执行日志
    logger.info(f"开始执行关键字: {keyword_name}")
    
    # 注入授权信息
    if keyword_name == 'HTTP请求':
        inject_authentication(context)
    
    # 参数验证和转换
    validate_and_transform_args(context)
```

#### 执行后Hook (AFTER_KEYWORD_EXECUTION)

在关键字执行后执行，可以处理结果或执行后续操作：

```python
from pytest_dsl.remote.hook_manager import register_after_keyword_hook

@register_after_keyword_hook
def postprocess_keyword(context):
    """关键字执行后的后处理"""
    keyword_name = context.get('keyword_name')
    keyword_result = context.get('keyword_result')
    
    # 记录执行结果
    logger.info(f"关键字执行完成: {keyword_name}, 结果: {keyword_result}")
    
    # 性能监控
    if keyword_name == 'HTTP请求':
        record_performance_metrics(context)
    
    # 结果后处理
    process_execution_result(context)
```

## Hook上下文

每个Hook函数接收一个`HookContext`对象，提供丰富的上下文信息：

```python
def my_hook(context):
    # 获取hook类型
    hook_type = context.hook_type
    
    # 获取服务器实例
    server = context.get('server')
    
    # 获取共享变量
    shared_variables = context.get('shared_variables')
    
    # 获取关键字信息（仅在关键字Hook中可用）
    keyword_name = context.get('keyword_name')
    keyword_args = context.get('keyword_args')
    keyword_result = context.get('keyword_result')
    
    # 设置数据（传递给后续处理）
    context.set('custom_data', 'value')
    
    # 操作共享变量
    token = context.get_shared_variable('auth_token')
    shared = context.get('shared_variables', {})
    shared['last_execution'] = datetime.now()
```

## 自定义授权实现

### 创建授权提供者

```python
from pytest_dsl.core.auth_provider import AuthProvider, register_auth_provider

class CustomTestAuthProvider(AuthProvider):
    """自定义测试授权提供者"""
    
    def __init__(self, **config):
        self.token_var = config.get('token_var', 'test_token')
        self.auth_header = config.get('auth_header', 'Authorization')
        self.shared_variables = {}
    
    def set_shared_variables(self, shared_variables):
        """设置共享变量引用"""
        self.shared_variables = shared_variables
    
    def apply_auth(self, base_url, request_kwargs):
        """应用授权到HTTP请求"""
        token = self.shared_variables.get(self.token_var)
        if token:
            if "headers" not in request_kwargs:
                request_kwargs["headers"] = {}
            request_kwargs["headers"][self.auth_header] = f"Bearer {token}"
        return request_kwargs
```

### 注册和使用授权提供者

```python
@register_startup_hook
def setup_auth_providers(context):
    """注册自定义授权提供者"""
    register_auth_provider("custom_auth", CustomTestAuthProvider)
    print("自定义授权提供者注册成功")

@register_before_keyword_hook
def inject_auth_for_http_requests(context):
    """为HTTP请求注入授权"""
    keyword_name = context.get('keyword_name')
    if keyword_name != 'HTTP请求':
        return
    
    shared_variables = context.get('shared_variables')
    auth_type = shared_variables.get('custom_auth_type')
    
    if auth_type == 'custom_auth':
        # 创建并配置授权提供者
        auth_provider = CustomTestAuthProvider()
        auth_provider.set_shared_variables(shared_variables)
        
        # 注入到关键字参数中
        keyword_args = context.get('keyword_args')
        # 修改config以应用授权
        context.set('keyword_args', keyword_args)
```

## 扩展加载

### 命令行加载扩展

```bash
# 加载单个扩展文件
pytest-dsl-server --extensions custom_auth.py

# 加载多个扩展
pytest-dsl-server --extensions "ext1.py,ext2.py,extensions/"

# 加载扩展目录
pytest-dsl-server --extensions extensions/
```

### 自动加载扩展

服务器会自动查找并加载以下位置的扩展：

```
project/
├── extensions/              # 自动加载此目录下的所有.py文件
│   ├── auth_extension.py
│   ├── logging_extension.py
│   └── monitoring_extension.py
├── remote_extensions.py     # 自动加载此文件
└── config/
    └── vars.yaml
```

### 扩展文件示例

创建 `extensions/auth_extension.py`：

```python
"""自定义授权扩展"""
import logging
from pytest_dsl.remote.hook_manager import (
    register_startup_hook,
    register_before_keyword_hook,
    register_after_keyword_hook
)
from pytest_dsl.core.auth_provider import AuthProvider, register_auth_provider

logger = logging.getLogger(__name__)

class CustomTestAuthProvider(AuthProvider):
    def __init__(self, **config):
        self.token_var = config.get('token_var', 'test_token')
        self.shared_variables = {}

    def set_shared_variables(self, shared_variables):
        self.shared_variables = shared_variables

    def apply_auth(self, base_url, request_kwargs):
        token = self.shared_variables.get(self.token_var)
        if token:
            if "headers" not in request_kwargs:
                request_kwargs["headers"] = {}
            request_kwargs["headers"]["Authorization"] = f"Bearer {token}"
        return request_kwargs

@register_startup_hook
def setup_custom_auth(context):
    """注册自定义授权提供者"""
    register_auth_provider("custom_auth", CustomTestAuthProvider)
    logger.info("自定义授权提供者注册成功")

@register_before_keyword_hook
def inject_custom_auth(context):
    """注入自定义授权"""
    keyword_name = context.get('keyword_name')
    if keyword_name != 'HTTP请求':
        return
    
    shared_variables = context.get('shared_variables')
    auth_type = shared_variables.get('custom_auth_type')
    
    if auth_type == 'custom_auth':
        logger.info("为HTTP请求注入自定义授权")
        # 授权注入逻辑
```

## 实际应用示例

### 监控和日志扩展

```python
"""监控和日志扩展"""
import time
import logging
from datetime import datetime
from pytest_dsl.remote.hook_manager import *

logger = logging.getLogger(__name__)

# 性能监控
performance_metrics = {}

@register_startup_hook
def setup_monitoring(context):
    """初始化监控"""
    logger.info("监控系统启动")
    performance_metrics['server_start_time'] = datetime.now()

@register_before_keyword_hook
def start_timing(context):
    """开始计时"""
    keyword_name = context.get('keyword_name')
    context.set('start_time', time.time())
    logger.info(f"开始执行关键字: {keyword_name}")

@register_after_keyword_hook
def end_timing(context):
    """结束计时并记录"""
    keyword_name = context.get('keyword_name')
    start_time = context.get('start_time')
    
    if start_time:
        duration = time.time() - start_time
        logger.info(f"关键字 {keyword_name} 执行耗时: {duration:.3f}秒")
        
        # 记录性能数据
        if keyword_name not in performance_metrics:
            performance_metrics[keyword_name] = []
        performance_metrics[keyword_name].append(duration)

@register_shutdown_hook
def save_metrics(context):
    """保存性能指标"""
    logger.info("保存性能指标")
    # 保存到文件或数据库
    with open('performance_metrics.json', 'w') as f:
        import json
        json.dump(performance_metrics, f, default=str, indent=2)
```

### 安全控制扩展

```python
"""安全控制扩展"""
import ipaddress
from pytest_dsl.remote.hook_manager import *

# 允许的IP地址范围
ALLOWED_IPS = ['127.0.0.1', '192.168.1.0/24']

@register_before_keyword_hook
def security_check(context):
    """安全检查"""
    # 获取客户端IP（需要服务器支持）
    client_ip = context.get('client_ip', '127.0.0.1')
    
    # IP白名单检查
    if not is_ip_allowed(client_ip):
        raise PermissionError(f"IP {client_ip} 不在允许列表中")
    
    # 关键字权限检查
    keyword_name = context.get('keyword_name')
    if keyword_name in ['系统命令', '文件操作'] and not is_admin_user(context):
        raise PermissionError(f"无权限执行关键字: {keyword_name}")

def is_ip_allowed(ip):
    """检查IP是否在允许列表中"""
    try:
        client_ip = ipaddress.ip_address(ip)
        for allowed in ALLOWED_IPS:
            if '/' in allowed:
                if client_ip in ipaddress.ip_network(allowed):
                    return True
            else:
                if client_ip == ipaddress.ip_address(allowed):
                    return True
        return False
    except:
        return False

def is_admin_user(context):
    """检查是否为管理员用户"""
    shared_variables = context.get('shared_variables', {})
    return shared_variables.get('user_role') == 'admin'
```

## 最佳实践

### 1. 错误处理

```python
@register_before_keyword_hook
def safe_hook(context):
    try:
        # hook逻辑
        process_keyword(context)
    except Exception as e:
        logger.error(f"Hook执行失败: {e}")
        # 不要抛出异常，避免影响其他hook和关键字执行
```

### 2. 性能优化

```python
@register_before_keyword_hook
def efficient_hook(context):
    # 只处理需要的关键字
    keyword_name = context.get('keyword_name')
    if keyword_name not in ['HTTP请求', '数据库查询']:
        return
    
    # 执行轻量级操作
    lightweight_processing(context)
```

### 3. 配置管理

```python
@register_startup_hook
def load_configuration(context):
    """加载扩展配置"""
    import os
    import yaml
    
    config_file = os.environ.get('EXTENSION_CONFIG', 'extension_config.yaml')
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        shared_variables = context.get('shared_variables')
        shared_variables.update(config)
```

### 4. 日志规范

```python
import logging

# 使用模块级别的logger
logger = logging.getLogger(__name__)

@register_before_keyword_hook
def log_keyword_execution(context):
    keyword_name = context.get('keyword_name')
    keyword_args = context.get('keyword_args')
    
    # 记录关键信息，避免敏感数据
    safe_args = {k: v for k, v in keyword_args.items() 
                 if k not in ['password', 'token', 'secret']}
    
    logger.info(f"执行关键字: {keyword_name}, 参数: {safe_args}")
```

## 验证和测试

### 启动带扩展的服务器

```bash
# 启动服务器并加载扩展
pytest-dsl-server --host 0.0.0.0 --port 8270 --extensions extensions/

# 或使用环境变量
export PYTEST_DSL_EXTENSIONS="extensions/"
pytest-dsl-server --host 0.0.0.0 --port 8270
```

### 测试扩展功能

创建测试文件 `test_extensions.dsl`：

```python
@name: "测试扩展功能"
@remote: "http://localhost:8270/" as test_server

# 设置自定义授权
custom_auth_type = "custom_auth"
test_token = "test_token_123"

# 测试自定义授权
test_server|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://httpbin.org/headers
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.headers.Authorization", "contains", "Bearer"]
''', 步骤名称: "测试自定义授权注入"

# 测试性能监控
for i in range(0, 3) do
    test_server|[HTTP请求], 客户端: "default", 配置: '''
        method: GET
        url: https://httpbin.org/delay/1
        asserts:
            - ["status", "eq", 200]
    ''', 步骤名称: "性能监控测试 ${i}"
end

[打印], 内容: "扩展功能测试完成"
```

运行测试：

```bash
pytest-dsl test_extensions.dsl
```

## 故障排除

### 常见问题

#### Q: 扩展加载失败

A: 检查以下几点：

1. 确认扩展文件路径正确
2. 检查Python语法错误
3. 验证导入的模块是否存在
4. 查看服务器启动日志

```bash
# 启动服务器并查看日志
pytest-dsl-server --extensions extensions/
```

#### Q: Hook不执行

A: 确认Hook注册正确：

```python
# 确保使用正确的装饰器
@register_startup_hook  # 不是 @startup_hook
def my_hook(context):
    pass
```

#### Q: 授权不生效

A: 检查授权提供者注册和配置：

```python
# 确保在startup hook中注册
@register_startup_hook
def setup_auth(context):
    register_auth_provider("my_auth", MyAuthProvider)

# 确保在before hook中正确应用
@register_before_keyword_hook
def apply_auth(context):
    # 检查关键字类型和配置
    pass
```

### 调试技巧

```python
@register_before_keyword_hook
def debug_hook(context):
    import json
    print("Hook上下文:")
    print(json.dumps({
        'hook_type': str(context.hook_type),
        'keyword_name': context.get('keyword_name'),
        'shared_variables': context.get('shared_variables')
    }, indent=2))
```

## 下一步

现在您已经掌握了远程服务器Hook机制，可以继续学习：

- **[远程关键字基础](./remote-keywords)** - 了解远程关键字的基本使用
- **[环境配置管理](./configuration)** - 管理复杂的远程服务器配置
- **[最佳实践](./best-practices)** - 学习分布式测试的最佳实践

## 相关资源

- [远程Hook机制示例](../examples/remote-hooks) - 完整的Hook扩展示例
- [示例库](../examples/) - 更多实际应用示例 
