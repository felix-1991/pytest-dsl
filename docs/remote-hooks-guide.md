# 远程服务器Hook机制使用指南

本文档介绍如何使用pytest-dsl远程服务器的hook机制来扩展服务器功能，特别是实现自定义授权。

## 目录

- [概述](#概述)
- [Hook类型](#hook类型)
- [Hook开发](#hook开发)
- [自定义授权实现](#自定义授权实现)
- [扩展加载](#扩展加载)
- [最佳实践](#最佳实践)

## 概述

远程服务器的hook机制允许你在服务器生命周期的关键点执行自定义逻辑，包括：

- 服务器启动和关闭时的初始化/清理工作
- 关键字执行前后的预处理/后处理
- 自定义授权注入
- 变量处理和转换
- 日志记录和监控

## Hook类型

### 1. 服务器启动Hook (SERVER_STARTUP)

在服务器启动时执行，用于初始化工作。

```python
from pytest_dsl.remote.hook_manager import register_startup_hook

@register_startup_hook
def setup_custom_providers(context):
    """服务器启动时的初始化"""
    server = context.get('server')
    shared_variables = context.get('shared_variables')

    # 执行初始化逻辑
    print("服务器启动，执行初始化...")
```

### 2. 服务器关闭Hook (SERVER_SHUTDOWN)

在服务器关闭时执行，用于清理工作。

```python
from pytest_dsl.remote.hook_manager import register_shutdown_hook

@register_shutdown_hook
def cleanup_resources(context):
    """服务器关闭时的清理"""
    print("服务器关闭，执行清理...")
```

### 3. 关键字执行前Hook (BEFORE_KEYWORD_EXECUTION)

在关键字执行前执行，可以修改参数或注入逻辑。

```python
from pytest_dsl.remote.hook_manager import register_before_keyword_hook

@register_before_keyword_hook
def preprocess_keyword(context):
    """关键字执行前的预处理"""
    keyword_name = context.get('keyword_name')
    keyword_args = context.get('keyword_args')

    # 修改参数
    if keyword_name == 'HTTP请求':
        # 注入自定义逻辑
        pass
```

### 4. 关键字执行后Hook (AFTER_KEYWORD_EXECUTION)

在关键字执行后执行，可以处理结果或执行后续操作。

```python
from pytest_dsl.remote.hook_manager import register_after_keyword_hook

@register_after_keyword_hook
def postprocess_keyword(context):
    """关键字执行后的后处理"""
    keyword_name = context.get('keyword_name')
    keyword_result = context.get('keyword_result')

    # 处理结果
    if keyword_name == 'HTTP请求':
        # 记录日志或处理响应
        pass
```

## Hook开发

### Hook上下文

每个hook函数接收一个`HookContext`对象，包含以下信息：

```python
def my_hook(context):
    # 获取hook类型
    hook_type = context.hook_type

    # 获取上下文数据
    server = context.get('server')
    shared_variables = context.get('shared_variables')
    keyword_name = context.get('keyword_name')
    keyword_args = context.get('keyword_args')

    # 设置数据（会传递给后续处理）
    context.set('custom_data', 'value')

    # 获取共享变量
    token = context.get_shared_variable('auth_token')
```

### 手动注册Hook

除了使用装饰器，也可以手动注册hook：

```python
from pytest_dsl.remote.hook_manager import hook_manager, HookType

def my_custom_hook(context):
    print("执行自定义hook")

# 手动注册
hook_manager.register_hook(HookType.SERVER_STARTUP, my_custom_hook)
```

## 自定义授权实现

### 1. 创建自定义授权提供者

```python
from pytest_dsl.core.auth_provider import AuthProvider, register_auth_provider

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
```

### 2. 注册授权提供者

```python
@register_startup_hook
def setup_auth_providers(context):
    register_auth_provider("custom_auth", CustomTestAuthProvider)
```

### 3. 注入授权逻辑

```python
@register_before_keyword_hook
def inject_auth_for_http_requests(context):
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
        # ... 修改config以应用授权
        context.set('keyword_args', keyword_args)
```

## 扩展加载

### 1. 命令行指定扩展

```bash
# 加载单个扩展文件
python -m pytest_dsl.remote.keyword_server --extensions custom_auth.py

# 加载多个扩展
python -m pytest_dsl.remote.keyword_server --extensions "ext1.py,ext2.py,extensions/"

# 加载扩展目录
python -m pytest_dsl.remote.keyword_server --extensions extensions/
```

### 2. 自动加载扩展

服务器会自动查找并加载以下位置的扩展：

- 当前目录下的`extensions/`目录中的所有`.py`文件
- 当前目录下的`remote_extensions.py`文件

### 3. 扩展文件结构

```
project/
├── extensions/
│   ├── auth_extension.py
│   ├── logging_extension.py
│   └── monitoring_extension.py
├── remote_extensions.py
└── config/
    └── vars.yaml
```

## 最佳实践

### 1. 错误处理

```python
@register_before_keyword_hook
def safe_hook(context):
    try:
        # hook逻辑
        pass
    except Exception as e:
        logger.error(f"Hook执行失败: {e}")
        # 不要抛出异常，避免影响其他hook
```

### 2. 性能考虑

```python
@register_before_keyword_hook
def efficient_hook(context):
    # 只处理需要的关键字
    keyword_name = context.get('keyword_name')
    if keyword_name not in ['HTTP请求', '数据库查询']:
        return

    # 执行轻量级操作
    pass
```

### 3. 变量管理

```python
@register_startup_hook
def setup_variables(context):
    shared_variables = context.get('shared_variables')

    # 设置默认值
    if 'auth_type' not in shared_variables:
        shared_variables['auth_type'] = 'default'
```

### 4. 日志记录

```python
import logging

logger = logging.getLogger(__name__)

@register_before_keyword_hook
def log_keyword_execution(context):
    keyword_name = context.get('keyword_name')
    logger.info(f"执行关键字: {keyword_name}")
```

## 示例和验证

### 扩展示例文件

完整的自定义授权扩展示例请参考：
- `examples/remote/custom_auth_extension.py` - 自定义授权扩展实现
- `examples/remote/custom_auth_test.dsl` - 完整的扩展验证测试
- `examples/remote/auth_mechanism_test.dsl` - 专门验证授权机制的简化测试

### 启动和测试

启动带扩展的服务器：
```bash
./examples/remote/start_server_with_auth.sh
```

运行验证测试：
```bash
# 运行完整的自定义授权验证测试
./examples/remote/run_custom_auth_test.sh

# 运行快速验证测试
./examples/remote/quick_auth_test.sh

# 手动运行单个测试
pytest-dsl examples/remote/custom_auth_test.dsl
pytest-dsl examples/remote/auth_mechanism_test.dsl
```

### 验证内容

自定义授权扩展验证测试包括：

1. **Hook机制验证**
   - 服务器启动Hook触发
   - 关键字执行前后Hook触发
   - 服务器关闭Hook触发

2. **自定义授权提供者验证**
   - 授权提供者注册成功
   - 授权头部正确注入
   - 授权配置参数处理

3. **远程授权机制验证**
   - 本地和远程授权对比
   - POST/GET请求授权处理
   - 会话管理与授权结合

4. **错误处理验证**
   - 无效授权提供者处理
   - 网络错误时的授权行为
   - 异常情况下的稳定性

5. **性能验证**
   - 连续请求的授权稳定性
   - 授权机制的性能影响
