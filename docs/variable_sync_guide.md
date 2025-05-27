# 变量同步功能指南

## 概述

变量同步功能允许远程关键字和本地关键字之间进行变量同步，实现类似开关的能力，方便在中心端控制变量。这个功能支持双向同步、精细化控制和中心化管理。

## 功能特性

### 1. 双向变量同步
- **本地到远程** (`to_remote`): 将本地变量同步到远程服务器
- **远程到本地** (`from_remote`): 将远程变量同步到本地
- **双向同步** (`bidirectional`): 同时进行双向同步

### 2. 变量类型支持
- **全局变量**: 以 `g_` 开头的变量，跨进程共享
- **YAML配置变量**: 从配置文件加载的变量
- **会话变量**: HTTP会话、认证信息等

### 3. 开关控制
- **总开关**: `enabled` - 控制是否启用变量同步
- **类型开关**: 分别控制不同类型变量的同步
- **方向开关**: 控制同步方向
- **时机开关**: 控制何时触发同步

## 配置选项

### 同步配置结构

```python
sync_config = {
    'enabled': True,                    # 总开关
    'sync_global_vars': True,           # 同步全局变量（g_开头）
    'sync_yaml_vars': True,             # 同步YAML配置变量
    'sync_session_vars': True,          # 同步会话变量
    'sync_direction': 'bidirectional',  # 同步方向
    'auto_sync_interval': 0,            # 自动同步间隔（秒）
    'sync_on_connect': True,            # 连接时是否同步
    'sync_on_execute': False,           # 执行关键字时是否同步
}
```

### 同步方向选项
- `to_remote`: 只同步本地变量到远程
- `from_remote`: 只同步远程变量到本地
- `bidirectional`: 双向同步

## 使用方法

### 1. YAML配置自动同步（推荐）

通过YAML配置文件可以实现远程服务器的自动连接和变量同步：

```yaml
# config/vars.yaml
remote_servers:
  main_server:
    url: "http://localhost:8270/"
    alias: "main"
    sync_config:
      sync_global_vars: true      # 自动同步全局变量
      sync_yaml_vars: true        # 自动同步YAML配置变量

  backup_server:
    url: "http://backup:8270/"
    alias: "backup"
    sync_config:
      sync_global_vars: true
      sync_yaml_vars: false       # 不同步YAML变量

# 全局变量（会自动同步到远程服务器）
g_environment: "production"
g_base_url: "https://api.example.com"
g_timeout: 30

# HTTP客户端配置（会被同步）
http_clients:
  default:
    base_url: "${g_base_url}"
    timeout: "${g_timeout}"
```

使用时无需手动同步，系统会在连接时自动传递变量：

```dsl
# 直接使用YAML配置的远程服务器，变量已自动同步
main|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: ${g_base_url}/api/status
'''
```

### 2. 基本同步操作

```dsl
# 同步本地变量到远程
同步变量到远程 服务器别名 remote_server

# 从远程同步变量到本地
从远程同步变量 服务器别名 remote_server

# 双向同步
双向同步变量 服务器别名 remote_server

# 同步所有远程服务器
同步所有远程变量 同步方向 bidirectional
```

### 2. 配置管理

```dsl
# 启用变量同步
启用变量同步 服务器别名 remote_server

# 禁用变量同步
禁用变量同步 服务器别名 remote_server

# 设置同步方向
设置同步方向 服务器别名 remote_server 方向 bidirectional

# 更新同步配置
更新同步配置 服务器别名 remote_server 配置 """
enabled: true
sync_global_vars: true
sync_yaml_vars: false
sync_direction: to_remote
"""
```

### 3. 状态查询

```dsl
# 获取同步状态
sync_status = 获取同步状态
```

## 编程接口

### 客户端接口

```python
from pytest_dsl.remote.keyword_client import remote_keyword_manager

# 手动同步变量
remote_keyword_manager.sync_variables_for_client('server_alias', 'bidirectional')

# 更新同步配置
remote_keyword_manager.update_sync_config_for_client('server_alias', enabled=True)

# 获取同步状态
status = remote_keyword_manager.get_sync_status()
```

### 服务器端接口

```python
from pytest_dsl.remote.keyword_server import RemoteKeywordServer

# 创建带变量同步的服务器
server = RemoteKeywordServer(host='localhost', port=8270)

# 设置共享变量
server.set_shared_variable('g_test_var', 'test_value')

# 获取共享变量
result = server.get_shared_variable('g_test_var')
```

## 实际应用场景

### 1. 中心化配置管理

在中心服务器上维护配置变量，各个客户端自动同步：

```dsl
# 在中心服务器设置配置
远程导入 http://config-server:8270/ 别名 config_center

# 从中心服务器同步配置
从远程同步变量 服务器别名 config_center

# 使用同步的配置
HTTP请求 客户端 default 配置 """
method: GET
url: ${g_base_url}/api/status
"""
```

### 2. 测试环境切换

通过变量同步实现测试环境的快速切换：

```dsl
# 设置环境变量
g_environment = "staging"
g_base_url = "https://staging-api.example.com"

# 同步到所有远程服务器
同步所有远程变量 同步方向 to_remote

# 所有远程关键字现在使用新的环境配置
```

### 3. 会话状态共享

在分布式测试中共享认证状态：

```dsl
# 在一个客户端登录
login_result = HTTP请求 客户端 default 配置 """
method: POST
url: ${g_base_url}/api/auth/login
json:
  username: ${g_test_user}
  password: ${g_test_password}
capture:
  access_token: $.access_token
"""

# 同步认证状态到远程
同步变量到远程 服务器别名 remote_server

# 其他客户端可以使用共享的认证状态
```

## 最佳实践

### 1. 变量命名规范
- 全局变量使用 `g_` 前缀
- 环境相关变量使用 `g_env_` 前缀
- 配置变量使用 `g_config_` 前缀

### 2. 同步策略
- 配置变量：连接时同步 (`sync_on_connect: true`)
- 会话变量：按需手动同步
- 测试数据：双向同步以保持一致性

### 3. 安全考虑
- 使用API密钥保护远程接口
- 避免同步敏感信息（密码、密钥等）
- 定期清理过期的共享变量

### 4. 性能优化
- 合理设置自动同步间隔
- 只同步必要的变量类型
- 使用批量同步而非频繁的单个同步

## 故障排除

### 常见问题

1. **同步失败**
   - 检查网络连接
   - 验证API密钥
   - 确认服务器状态

2. **变量未同步**
   - 检查同步配置
   - 确认变量命名规范
   - 验证同步方向设置

3. **性能问题**
   - 减少自动同步频率
   - 限制同步的变量数量
   - 使用异步同步模式

### 调试方法

```dsl
# 获取详细的同步状态
sync_status = 获取同步状态
打印 ${sync_status}

# 测试单个变量同步
设置全局变量 变量名 g_test_sync 变量值 "test_value"
同步变量到远程 服务器别名 remote_server
从远程同步变量 服务器别名 remote_server
断言相等 实际值 ${g_test_sync} 期望值 "test_value"
```
