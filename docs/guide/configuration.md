# 环境配置管理

pytest-dsl提供了强大的配置管理功能，支持多环境配置、动态配置切换、配置继承等特性，帮助您在不同环境间轻松切换测试配置。

## 配置文件概述

pytest-dsl支持YAML格式的配置文件，用于定义：

- HTTP客户端配置
- 数据库连接信息
- 环境特定的变量
- 测试执行参数
- 自定义设置

## 基本配置结构

### 基础配置文件示例

```yaml
# config.yaml - 基础配置文件
http_clients:
  default:
    base_url: "https://api.example.com"
    timeout: 30
    headers:
      Content-Type: "application/json"
      User-Agent: "pytest-dsl/1.0"
    
  admin:
    base_url: "https://admin-api.example.com"
    timeout: 60
    headers:
      Content-Type: "application/json"
      Authorization: "Bearer ${ADMIN_TOKEN}"

variables:
  api_version: "v1"
  max_retry_count: 3
  default_timeout: 30

test_settings:
  parallel_workers: 4
  report_format: "html"
  log_level: "INFO"
```

### 使用配置文件

```bash
# 在命令行中指定配置文件
pytest-dsl tests/ --config config.yaml

# 指定多个配置文件，后面的会覆盖前面的
pytest-dsl tests/ --config base.yaml --config env-specific.yaml

# 使用YAML变量文件
pytest-dsl tests/ --yaml-vars config.yaml
```

## 多环境配置

### 环境特定配置

为不同环境创建独立的配置文件：

```yaml
# config/dev.yaml - 开发环境配置
environment: development

http_clients:
  default:
    base_url: "https://dev-api.example.com"
    timeout: 15
    headers:
      Content-Type: "application/json"
      X-Environment: "dev"
    verify_ssl: false  # 开发环境可能使用自签名证书
    
  database:
    host: "dev-db.example.com"
    port: 5432
    name: "dev_database"
    user: "${DB_USER}"
    password: "${DB_PASSWORD}"

variables:
  debug_mode: true
  log_level: "DEBUG"
  test_data_prefix: "dev_test_"
  cleanup_after_test: false

features:
  enable_cache: false
  enable_rate_limiting: false
  mock_external_services: true
```

```yaml
# config/test.yaml - 测试环境配置
environment: test

http_clients:
  default:
    base_url: "https://test-api.example.com"
    timeout: 30
    headers:
      Content-Type: "application/json"
      X-Environment: "test"
    
  database:
    host: "test-db.example.com"
    port: 5432
    name: "test_database"
    user: "${DB_USER}"
    password: "${DB_PASSWORD}"

variables:
  debug_mode: false
  log_level: "INFO"
  test_data_prefix: "test_"
  cleanup_after_test: true

features:
  enable_cache: true
  enable_rate_limiting: true
  mock_external_services: false
```

```yaml
# config/prod.yaml - 生产环境配置
environment: production

http_clients:
  default:
    base_url: "https://api.example.com"
    timeout: 60
    headers:
      Content-Type: "application/json"
      X-Environment: "prod"
    retries: 3
    
  database:
    host: "prod-db.example.com"
    port: 5432
    name: "prod_database"
    user: "${DB_USER}"
    password: "${DB_PASSWORD}"
    ssl_mode: "require"

variables:
  debug_mode: false
  log_level: "WARNING"
  test_data_prefix: "prod_test_"
  cleanup_after_test: true
  
test_settings:
  max_test_duration: 300  # 生产环境测试时间限制
  allowed_failure_rate: 0.05  # 允许5%的失败率

features:
  enable_cache: true
  enable_rate_limiting: true
  mock_external_services: false
```

### 配置继承

使用配置继承减少重复配置：

```yaml
# config/base.yaml - 基础配置
http_clients:
  default:
    timeout: 30
    headers:
      Content-Type: "application/json"
      User-Agent: "pytest-dsl/1.0"
      Accept: "application/json"
    retries: 2
    
variables:
  api_version: "v1"
  max_retry_count: 3
  
test_settings:
  report_format: "html"
  parallel_workers: 2
```

```yaml
# config/dev.yaml - 继承基础配置
extends: base.yaml

http_clients:
  default:
    base_url: "https://dev-api.example.com"
    timeout: 15  # 覆盖基础配置
    headers:
      X-Environment: "development"  # 添加新的头部
    verify_ssl: false
    
variables:
  debug_mode: true  # 添加新变量
  log_level: "DEBUG"
  
test_settings:
  parallel_workers: 1  # 开发环境减少并发
```

## HTTP客户端配置

### 详细的HTTP客户端配置

```yaml
http_clients:
  # 默认API客户端
  default:
    base_url: "https://api.example.com"
    timeout: 30
    headers:
      Content-Type: "application/json"
      Accept: "application/json"
      User-Agent: "pytest-dsl-client/1.0"
    auth:
      type: "bearer"
      token: "${API_TOKEN}"
    retries: 3
    retry_delay: 1
    verify_ssl: true
    
  # 管理员API客户端
  admin:
    base_url: "https://admin-api.example.com"
    timeout: 60
    headers:
      Content-Type: "application/json"
      X-Admin-Client: "true"
    auth:
      type: "basic"
      username: "${ADMIN_USER}"
      password: "${ADMIN_PASSWORD}"
    
  # 文件上传客户端
  upload:
    base_url: "https://upload.example.com"
    timeout: 300  # 上传可能需要更长时间
    headers:
      User-Agent: "pytest-dsl-upload/1.0"
    max_file_size: "100MB"
    
  # 外部服务客户端
  external:
    base_url: "https://external-service.com"
    timeout: 45
    headers:
      X-API-Key: "${EXTERNAL_API_KEY}"
      X-Client-ID: "${CLIENT_ID}"
    rate_limit:
      requests_per_minute: 60
```

### 认证配置

```yaml
http_clients:
  # Bearer Token认证
  api_with_token:
    base_url: "https://api.example.com"
    auth:
      type: "bearer"
      token: "${ACCESS_TOKEN}"
      
  # Basic认证
  api_with_basic:
    base_url: "https://api.example.com"
    auth:
      type: "basic"
      username: "${API_USER}"
      password: "${API_PASSWORD}"
      
  # OAuth2认证
  api_with_oauth:
    base_url: "https://api.example.com"
    auth:
      type: "oauth2"
      client_id: "${OAUTH_CLIENT_ID}"
      client_secret: "${OAUTH_CLIENT_SECRET}"
      token_url: "https://auth.example.com/oauth/token"
      scope: "read write"
      
  # 自定义头部认证
  api_with_custom:
    base_url: "https://api.example.com"
    headers:
      X-API-Key: "${CUSTOM_API_KEY}"
      X-Client-Secret: "${CLIENT_SECRET}"
```

## 环境变量和密钥管理

### 环境变量配置

```yaml
# 在配置文件中引用环境变量
http_clients:
  default:
    base_url: "${API_BASE_URL}"
    auth:
      type: "bearer"
      token: "${API_TOKEN}"
      
database:
  host: "${DB_HOST}"
  port: "${DB_PORT}"
  user: "${DB_USER}"
  password: "${DB_PASSWORD}"
  
variables:
  environment_name: "${ENVIRONMENT}"
  debug_enabled: "${DEBUG:-false}"  # 带默认值
```

### 密钥文件管理

```bash
# .env.dev - 开发环境变量
API_BASE_URL=https://dev-api.example.com
API_TOKEN=dev_token_123456
DB_HOST=dev-db.example.com
DB_USER=dev_user
DB_PASSWORD=dev_password
ENVIRONMENT=development
DEBUG=true

# .env.test - 测试环境变量  
API_BASE_URL=https://test-api.example.com
API_TOKEN=test_token_789012
DB_HOST=test-db.example.com
DB_USER=test_user
DB_PASSWORD=test_password
ENVIRONMENT=test
DEBUG=false

# .env.prod - 生产环境变量
API_BASE_URL=https://api.example.com
API_TOKEN=prod_token_345678
DB_HOST=prod-db.example.com
DB_USER=prod_user
DB_PASSWORD=prod_secure_password
ENVIRONMENT=production
DEBUG=false
```

### 使用环境变量文件

```bash
# 加载特定环境的变量文件
source .env.dev && pytest-dsl tests/ --config config/dev.yaml

# 或者使用工具自动加载
export ENVIRONMENT=dev
pytest-dsl tests/ --config config/${ENVIRONMENT}.yaml --env-file .env.${ENVIRONMENT}
```

## 配置文件在DSL中的使用

### 访问配置变量

```python
@name: "使用配置变量的测试"

# 在DSL中访问配置的变量
当前环境 = ${environment}
API版本 = ${api_version}
调试模式 = ${debug_mode}

[打印], 内容: "当前环境: ${当前环境}"
[打印], 内容: "API版本: ${API版本}"

# 根据配置调整测试行为
if ${调试模式} do
    [打印], 内容: "调试模式已启用，将输出详细信息"
end

# 使用配置中的HTTP客户端
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /api/${API版本}/status
    asserts:
        - ["status", "eq", 200]
'''
```

### 条件配置

```python
@name: "环境相关测试"

# 根据环境执行不同的测试逻辑
if "${environment}" == "development" do
    # 开发环境特定的测试
    [打印], 内容: "执行开发环境测试"
    
    # 可能包含更详细的日志
    调试输出 = True
    
elif "${environment}" == "production" do
    # 生产环境的测试更加谨慎
    [打印], 内容: "执行生产环境测试"
    
    # 生产环境可能需要额外的确认
    [断言], 条件: "${test_data_prefix} == 'prod_test_'", 消息: "生产环境测试数据前缀不正确"
    
else
    # 测试环境的标准测试
    [打印], 内容: "执行标准测试"
end

# 使用配置中的功能开关
if ${enable_cache} do
    [测试缓存功能]
else
    [跳过缓存测试]
end
```

## 高级配置功能

### 配置模板和替换

```yaml
# config/template.yaml - 配置模板
http_clients:
  default:
    base_url: "https://{{ENVIRONMENT}}-api.example.com"
    timeout: "{{TIMEOUT}}"
    headers:
      X-Environment: "{{ENVIRONMENT}}"
      X-Version: "{{API_VERSION}}"
      
variables:
  data_prefix: "{{ENVIRONMENT}}_test_"
  log_level: "{{LOG_LEVEL}}"
```

```bash
# 使用模板替换生成实际配置
export ENVIRONMENT=staging
export TIMEOUT=45
export API_VERSION=v2
export LOG_LEVEL=INFO

# 替换模板变量生成最终配置
envsubst < config/template.yaml > config/staging.yaml
```

### 动态配置加载

```python
# resources/common/config_manager.resource
@name: "配置管理器"

function 加载环境配置 (环境名称) do
    [打印], 内容: "加载环境配置: ${环境名称}"
    
    # 根据环境名称确定配置文件
    配置文件路径 = "config/${环境名称}.yaml"
    
    # 验证配置文件是否存在
    [执行命令], 命令: "test -f ${配置文件路径}"
    
    # 设置配置相关的全局变量
    [设置全局变量], 变量名: "current_config", 值: ${配置文件路径}
    [设置全局变量], 变量名: "current_environment", 值: ${环境名称}
    
    [打印], 内容: "配置加载完成: ${配置文件路径}"
    
    return {"config_file": ${配置文件路径}, "environment": ${环境名称}}
end

function 获取配置值 (配置路径, 默认值=null) do
    # 从当前配置中获取指定路径的值
    # 这里需要实现配置值的读取逻辑
    
    [打印], 内容: "获取配置值: ${配置路径}"
    
    # 示例：假设配置已加载到全局变量中
    配置值 = [获取全局变量], 变量名: ${配置路径}
    
    if ${配置值} == null and ${默认值} != null do
        return ${默认值}
    end
    
    return ${配置值}
end

function 切换环境 (目标环境) do
    [打印], 内容: "切换环境: ${目标环境}"
    
    # 保存当前环境
    当前环境 = [获取全局变量], 变量名: "current_environment"
    [设置全局变量], 变量名: "previous_environment", 值: ${当前环境}
    
    # 加载新环境配置
    新配置 = [加载环境配置], 环境名称: ${目标环境}
    
    [打印], 内容: "环境切换完成: ${当前环境} -> ${目标环境}"
    
    return ${新配置}
end
```

### 配置验证

```python
# resources/common/config_validator.resource
@name: "配置验证器"

function 验证HTTP客户端配置 (客户端名称) do
    [打印], 内容: "验证HTTP客户端配置: ${客户端名称}"
    
    # 检查基本配置项
    必需配置项 = ["base_url", "timeout"]
    
    for 配置项 in ${必需配置项} do
        配置值 = [获取配置值], 配置路径: "http_clients.${客户端名称}.${配置项}"
        
        [断言], 条件: "${配置值} != null", 消息: "客户端${客户端名称}缺少必需配置: ${配置项}"
    end
    
    # 验证URL格式
    基础URL = [获取配置值], 配置路径: "http_clients.${客户端名称}.base_url"
    [断言], 条件: "'http' in '${基础URL}'", 消息: "基础URL格式无效: ${基础URL}"
    
    # 验证超时值
    超时值 = [获取配置值], 配置路径: "http_clients.${客户端名称}.timeout"
    [断言], 条件: "${超时值} > 0", 消息: "超时值必须大于0: ${超时值}"
    
    [打印], 内容: "✓ 客户端${客户端名称}配置验证通过"
    
    return True
end

function 验证环境配置 () do
    [打印], 内容: "验证当前环境配置"
    
    # 验证环境变量
    当前环境 = [获取配置值], 配置路径: "environment"
    支持的环境 = ["development", "test", "staging", "production"]
    
    [断言], 条件: "'${当前环境}' in ${支持的环境}", 消息: "不支持的环境: ${当前环境}"
    
    # 验证所有HTTP客户端配置
    客户端列表 = ["default", "admin"]  # 根据实际配置调整
    
    for 客户端 in ${客户端列表} do
        [验证HTTP客户端配置], 客户端名称: ${客户端}
    end
    
    [打印], 内容: "✓ 环境配置验证完成"
    
    return True
end
```

## 配置文件示例集合

### 微服务架构配置

```yaml
# config/microservices.yaml
http_clients:
  # 用户服务
  user_service:
    base_url: "https://user-service.example.com"
    timeout: 30
    headers:
      Content-Type: "application/json"
      X-Service-Name: "user-service"
    
  # 订单服务
  order_service:
    base_url: "https://order-service.example.com"
    timeout: 45
    headers:
      Content-Type: "application/json"
      X-Service-Name: "order-service"
    
  # 支付服务
  payment_service:
    base_url: "https://payment-service.example.com"
    timeout: 60
    headers:
      Content-Type: "application/json"
      X-Service-Name: "payment-service"
    auth:
      type: "bearer"
      token: "${PAYMENT_SERVICE_TOKEN}"
    
  # 通知服务
  notification_service:
    base_url: "https://notification-service.example.com"
    timeout: 20
    headers:
      Content-Type: "application/json"
      X-Service-Name: "notification-service"

service_discovery:
  consul:
    host: "consul.example.com"
    port: 8500
  eureka:
    url: "http://eureka.example.com:8761"

variables:
  service_mesh_enabled: true
  tracing_enabled: true
  circuit_breaker_enabled: true
```

### 数据库配置

```yaml
# config/database.yaml
databases:
  # 主数据库
  primary:
    host: "${PRIMARY_DB_HOST}"
    port: 5432
    name: "${PRIMARY_DB_NAME}"
    user: "${PRIMARY_DB_USER}"
    password: "${PRIMARY_DB_PASSWORD}"
    ssl_mode: "require"
    pool_size: 10
    
  # 只读副本
  readonly:
    host: "${READONLY_DB_HOST}"
    port: 5432
    name: "${PRIMARY_DB_NAME}"
    user: "${READONLY_DB_USER}"
    password: "${READONLY_DB_PASSWORD}"
    ssl_mode: "require"
    pool_size: 5
    
  # Redis缓存
  cache:
    host: "${REDIS_HOST}"
    port: 6379
    password: "${REDIS_PASSWORD}"
    db: 0
    
  # MongoDB文档数据库
  document:
    host: "${MONGO_HOST}"
    port: 27017
    name: "${MONGO_DB_NAME}"
    user: "${MONGO_USER}"
    password: "${MONGO_PASSWORD}"

connection_pools:
  max_connections: 20
  min_connections: 5
  idle_timeout: 300
```

## 配置最佳实践

### 1. 安全性考虑

```yaml
# 不要在配置文件中硬编码敏感信息
# ❌ 错误做法
http_clients:
  default:
    auth:
      token: "hardcoded_secret_token"  # 不安全

# ✅ 正确做法
http_clients:
  default:
    auth:
      token: "${API_TOKEN}"  # 使用环境变量
```

### 2. 配置分层

```
config/
├── base.yaml              # 基础配置
├── environments/          # 环境特定配置
│   ├── dev.yaml
│   ├── test.yaml
│   └── prod.yaml
├── services/              # 服务特定配置
│   ├── api_clients.yaml
│   └── databases.yaml
└── features/              # 功能开关配置
    ├── feature_flags.yaml
    └── experiments.yaml
```

### 3. 配置验证脚本

```bash
#!/bin/bash
# scripts/validate_config.sh

echo "验证配置文件..."

for env in dev test staging prod; do
    echo "验证环境: $env"
    
    # 检查配置文件是否存在
    if [ ! -f "config/$env.yaml" ]; then
        echo "错误: 配置文件 config/$env.yaml 不存在"
        exit 1
    fi
    
    # 验证YAML语法
    python -c "import yaml; yaml.safe_load(open('config/$env.yaml'))" || {
        echo "错误: config/$env.yaml YAML语法错误"
        exit 1
    }
    
    echo "✓ $env 配置验证通过"
done

echo "所有配置文件验证完成"
```

### 4. 配置文档化

```yaml
# config/schema.yaml - 配置架构文档
# 用于说明配置文件的结构和用途

http_clients:
  description: "HTTP客户端配置"
  required: true
  properties:
    default:
      description: "默认API客户端"
      required: true
      properties:
        base_url:
          type: "string"
          description: "API基础URL"
          required: true
        timeout:
          type: "integer"
          description: "请求超时时间（秒）"
          default: 30
        headers:
          type: "object"
          description: "默认请求头"

variables:
  description: "全局变量配置"
  properties:
    debug_mode:
      type: "boolean"
      description: "是否启用调试模式"
      default: false
```

通过合理的配置管理，您可以在不同环境间灵活切换，保持配置的一致性和安全性，提高测试的可维护性和可靠性。 