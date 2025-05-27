# YAML远程服务器配置使用指南

## 概述

这个指南展示如何使用YAML配置文件自动加载远程关键字服务器，实现全局配置管理。

## 目录结构

```
project/
├── config/
│   ├── vars.yaml                    # 主配置文件
│   ├── remote_servers.yaml          # 远程服务器专用配置
│   └── test_environment.yaml        # 测试环境配置
├── tests/
│   ├── test_api.dsl                 # API测试
│   ├── test_ui.dsl                  # UI测试
│   └── test_integration.dsl         # 集成测试
└── README.md
```

## 配置文件示例

### 1. 主配置文件 (config/vars.yaml)

```yaml
# 全局变量
g_environment: "staging"
g_base_url: "https://api.staging.example.com"
g_timeout: 30
g_retry_count: 3

# 远程服务器配置
remote_servers:
  api_server:
    url: "http://api-test-server:8270/"
    alias: "api"
    api_key: "${API_SERVER_KEY}"  # 从环境变量获取
    sync_config:
      sync_global_vars: true
      sync_yaml_vars: true
  
  ui_server:
    url: "http://ui-test-server:8270/"
    alias: "ui"
    sync_config:
      sync_global_vars: true
      sync_yaml_vars: false

# HTTP客户端配置
http_clients:
  default:
    base_url: "${g_base_url}"
    headers:
      User-Agent: "pytest-dsl-test/1.0"
      Accept: "application/json"
    timeout: "${g_timeout}"
    verify_ssl: true
    session: true

# 测试数据
test_data:
  admin_user:
    username: "admin"
    password: "admin123"
  normal_user:
    username: "user"
    password: "user123"
```

### 2. 专用远程服务器配置 (config/remote_servers.yaml)

```yaml
# 专门的远程服务器配置文件
remote_servers:
  # 生产环境API服务器
  prod_api:
    url: "http://prod-api-server:8270/"
    alias: "prod_api"
    api_key: "prod_api_key_secure"
    sync_config:
      sync_global_vars: true
      sync_yaml_vars: true
  
  # 开发环境服务器
  dev_server:
    url: "http://dev-server:8270/"
    alias: "dev"
    sync_config:
      sync_global_vars: false  # 开发环境不同步全局变量
      sync_yaml_vars: true
  
  # 性能测试服务器
  perf_server:
    url: "http://perf-server:8270/"
    alias: "perf"
    api_key: "perf_test_key"

# 性能测试相关配置
performance_config:
  concurrent_users: 100
  test_duration: 300
  ramp_up_time: 60
```

### 3. 环境特定配置 (config/test_environment.yaml)

```yaml
# 测试环境特定配置
remote_servers:
  test_main:
    url: "http://localhost:8270/"
    alias: "main"
    sync_config:
      sync_global_vars: true
      sync_yaml_vars: true
  
  test_backup:
    url: "http://localhost:8271/"
    alias: "backup"

# 测试环境变量
g_test_mode: true
g_debug_level: "DEBUG"
g_log_requests: true

# 测试数据库配置
test_database:
  host: "localhost"
  port: 5432
  database: "test_db"
  username: "test_user"
  password: "test_pass"
```

## 使用方式

### 1. 使用默认配置

```bash
# 使用默认config目录下的所有YAML文件
pytest tests/test_api.dsl
```

### 2. 指定特定配置文件

```bash
# 使用特定的配置文件
pytest --yaml-vars config/remote_servers.yaml tests/test_api.dsl

# 使用多个配置文件
pytest --yaml-vars config/vars.yaml --yaml-vars config/remote_servers.yaml tests/
```

### 3. 指定配置目录

```bash
# 使用特定目录下的所有YAML文件
pytest --yaml-vars-dir config tests/
```

## DSL测试文件示例

### API测试 (tests/test_api.dsl)

```dsl
@name: "API自动化测试"
@description: "使用YAML配置的远程服务器进行API测试"
@tags: ["api", "remote", "yaml"]

# 直接使用YAML中配置的远程服务器，无需@remote导入
api|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: /api/users
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.data", "exists"]
'''

# 使用全局变量（已自动同步到远程服务器）
api|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: ${g_base_url}/api/health
    asserts:
        - ["status", "eq", 200]
'''

# 测试用户登录
login_result = api|[HTTP请求],客户端: "default",配置: '''
    method: POST
    url: /api/login
    request:
        json:
            username: "${test_data.admin_user.username}"
            password: "${test_data.admin_user.password}"
    captures:
        token: ["jsonpath", "$.token"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.token", "exists"]
'''

[打印],内容: "登录成功，token: ${login_result}"
```

### UI测试 (tests/test_ui.dsl)

```dsl
@name: "UI自动化测试"
@description: "使用远程UI服务器进行界面测试"
@tags: ["ui", "remote"]

# 使用UI服务器执行界面操作
ui|[打印],内容: "开始UI测试"

# 模拟UI操作（实际应该是UI关键字）
ui|[生成随机数],最小值: 1,最大值: 1000
ui|[拼接字符串],前缀: "UI测试-",后缀: "-完成"
```

### 集成测试 (tests/test_integration.dsl)

```dsl
@name: "集成测试"
@description: "跨多个远程服务器的集成测试"
@tags: ["integration", "multi-server"]

# 在API服务器上创建数据
api_result = api|[HTTP请求],客户端: "default",配置: '''
    method: POST
    url: /api/data
    request:
        json:
            name: "integration_test"
            value: "test_data"
    captures:
        data_id: ["jsonpath", "$.id"]
    asserts:
        - ["status", "eq", 201]
'''

# 在UI服务器上验证数据
ui|[打印],内容: "验证数据ID: ${api_result.captures.data_id}"

# 如果需要临时服务器，仍可使用@remote语法
@remote: "http://temp-server:8270/" as temp

temp|[打印],内容: "临时服务器操作"
```

## 环境管理

### 开发环境

```bash
# 使用开发环境配置
export ENVIRONMENT=development
pytest --yaml-vars config/dev_config.yaml tests/
```

### 测试环境

```bash
# 使用测试环境配置
export ENVIRONMENT=testing
pytest --yaml-vars config/test_config.yaml tests/
```

### 生产环境

```bash
# 使用生产环境配置
export ENVIRONMENT=production
export API_SERVER_KEY=your_production_key
pytest --yaml-vars config/prod_config.yaml tests/
```

## 最佳实践

### 1. 配置分离

- **基础配置**: 放在主配置文件中
- **环境特定**: 使用不同的配置文件
- **敏感信息**: 通过环境变量传递

### 2. 别名规范

```yaml
remote_servers:
  api_server:
    alias: "api"        # 简短明确
  ui_server:
    alias: "ui"         # 功能导向
  db_server:
    alias: "db"         # 易于识别
```

### 3. 变量同步策略

```yaml
# 生产环境：谨慎同步
sync_config:
  sync_global_vars: true   # 同步必要的全局变量
  sync_yaml_vars: false    # 不同步敏感配置

# 测试环境：完全同步
sync_config:
  sync_global_vars: true
  sync_yaml_vars: true
```

### 4. 错误处理

- 配置验证：确保必要的配置项存在
- 连接重试：处理网络不稳定情况
- 降级策略：远程服务不可用时的备选方案

## 故障排除

### 常见问题

1. **服务器连接失败**
   - 检查URL是否正确
   - 确认服务器是否启动
   - 验证网络连接

2. **配置未生效**
   - 确认YAML文件语法正确
   - 检查文件路径是否正确
   - 验证配置加载顺序

3. **变量同步问题**
   - 检查sync_config配置
   - 确认变量名称正确
   - 验证API密钥权限

### 调试技巧

```bash
# 启用详细日志
pytest -v --yaml-vars config/debug.yaml tests/

# 检查配置加载情况
pytest --yaml-vars config/vars.yaml --collect-only
```

## 总结

通过YAML配置自动加载远程服务器，可以：

- ✅ 简化DSL文件，减少重复配置
- ✅ 实现全局配置管理
- ✅ 支持环境特定配置
- ✅ 提高配置的可维护性
- ✅ 保持向后兼容性

这种方式特别适合大型项目和多环境部署场景。
