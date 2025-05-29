# YAML变量无缝传递功能

## 概述

YAML变量无缝传递功能允许远程关键字客户端自动将本地的YAML配置变量传递到远程服务器，实现配置的统一管理和无缝共享。

## 功能特性

### 1. 自动变量传递
- 连接远程服务器时自动传递所有YAML变量
- 支持复杂嵌套结构的变量
- 自动添加 `yaml_` 前缀以区分变量来源

### 2. 安全过滤机制
- 自动过滤包含敏感信息的变量
- 默认排除包含 `password`, `secret`, `key`, `token`, `credential`, `auth`, `private` 等关键词的变量
- 防止远程服务器配置循环传递

### 3. 灵活配置选项
- 支持指定特定键列表进行传递
- 支持自定义排除模式
- 支持完全自定义同步策略

## 配置选项

### 同步配置参数

```python
sync_config = {
    'sync_global_vars': True,           # 是否同步全局变量
    'sync_yaml_vars': True,             # 是否同步YAML变量
    'yaml_sync_keys': None,             # 指定要同步的YAML键列表，None表示同步所有
    'yaml_exclude_patterns': [          # 排除包含这些模式的变量
        'password', 'secret', 'key', 'token',
        'credential', 'auth', 'private', 'remote_servers'
    ]
}
```

### 参数说明

- **yaml_sync_keys**:
  - `None`: 同步所有YAML变量（除了被排除的）
  - `['key1', 'key2']`: 只同步指定的键

- **yaml_exclude_patterns**:
  - 字符串列表，包含这些模式的变量名或值会被排除
  - 不区分大小写匹配
  - 默认排除敏感信息和远程服务器配置

## 使用方法

### 1. 默认配置（推荐）

```python
from pytest_dsl.remote.keyword_client import RemoteKeywordClient

# 使用默认配置，自动传递所有非敏感YAML变量
client = RemoteKeywordClient(url="http://localhost:8270/")
client.connect()
```

### 2. 指定特定键

```python
sync_config = {
    'sync_yaml_vars': True,
    'yaml_sync_keys': ['http_clients', 'api_endpoints', 'test_data']
}

client = RemoteKeywordClient(
    url="http://localhost:8270/",
    sync_config=sync_config
)
client.connect()
```

### 3. 自定义排除模式

```python
sync_config = {
    'sync_yaml_vars': True,
    'yaml_exclude_patterns': ['password', 'secret', 'internal', 'debug']
}

client = RemoteKeywordClient(
    url="http://localhost:8270/",
    sync_config=sync_config
)
client.connect()
```

### 4. YAML配置文件方式

```yaml
# config/vars.yaml
remote_servers:
  main_server:
    url: "http://localhost:8270/"
    alias: "main"
    sync_config:
      sync_yaml_vars: true
      yaml_sync_keys: ["http_clients", "api_endpoints"]

# 这些变量会被自动传递
http_clients:
  default:
    base_url: "https://api.example.com"
    timeout: 30

api_endpoints:
  login: "/auth/login"
  data: "/api/data"

# 这些敏感变量会被自动过滤
database_password: "secret123"
api_secret_key: "sk-1234567890"
```

## 变量命名规则

传递到远程服务器的YAML变量会自动添加 `yaml_` 前缀：

- 本地变量 `test_data` → 远程变量 `yaml_test_data`
- 本地变量 `http_clients` → 远程变量 `yaml_http_clients`
- 本地变量 `api_config` → 远程变量 `yaml_api_config`

## 安全考虑

### 默认排除的敏感信息模式
- `password` - 密码相关
- `secret` - 密钥相关
- `key` - 键值相关
- `token` - 令牌相关
- `credential` - 凭证相关
- `auth` - 认证相关
- `private` - 私有信息
- `remote_servers` - 远程服务器配置（防止循环）

### 安全建议
1. 不要在YAML文件中存储明文密码
2. 使用环境变量引用敏感信息
3. 定期审查传递的变量列表
4. 在生产环境中使用更严格的排除模式

## 示例

### 完整示例配置

```yaml
# config/test_vars.yaml

# 全局变量
g_environment: "test"
g_base_url: "https://api.example.com"

# HTTP客户端配置（会被传递）
http_clients:
  default:
    base_url: "${g_base_url}"
    headers:
      User-Agent: "pytest-dsl/1.0"
    timeout: 30

# 测试数据（会被传递）
test_data:
  username: "testuser"
  email: "test@example.com"

# 敏感信息（会被过滤）
database_password: "secret123"
api_key: "sk-1234567890"

# 远程服务器配置
remote_servers:
  test_server:
    url: "http://localhost:8270/"
    alias: "test"
    sync_config:
      sync_yaml_vars: true
```

### DSL使用示例

```dsl
# 远程关键字会自动获得传递的YAML变量，无需前缀
test|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: ${g_base_url}/api/data
    headers:
        X-Test-User: ${test_data.username}
'''
```

**注意**：从v2.0开始，客户端变量无缝传递到服务端，服务端使用变量时不需要添加任何前缀，就像在本地使用一样。

## 故障排除

### 常见问题

1. **变量未传递**
   - 检查 `sync_yaml_vars` 是否为 `true`
   - 检查变量名是否被排除模式匹配
   - 查看连接日志中的变量传递信息

2. **敏感信息泄露**
   - 检查排除模式配置
   - 添加更严格的过滤规则
   - 使用 `yaml_sync_keys` 明确指定允许的键

3. **性能问题**
   - 减少传递的变量数量
   - 使用 `yaml_sync_keys` 只传递必要的变量
   - 避免传递大型数据结构

### 调试方法

启用详细日志查看变量传递过程：

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 连接时会显示详细的变量传递信息
client.connect()
```

## 版本兼容性

- 支持 pytest-dsl 1.0+
- 向后兼容旧的特定键传递方式
- 新功能默认启用，不影响现有代码
