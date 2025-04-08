# HTTP请求关键字设计文档

基于之前的设计和改进建议，我重新设计了HTTP请求关键字，使其更加灵活、强大且易于使用。

## 概述

`[HTTP请求]`关键字用于执行HTTP请求并进行API接口测试，支持请求发送、响应捕获和断言验证，所有配置都在一个结构化的YAML配置中定义。

## 设计目标

1. 提供直观且强大的语法，适合pytest-dsl框架
2. 支持从YAML变量文件中读取配置初始化HTTP客户端
3. 在单个YAML配置中集成请求、捕获和断言功能
4. 支持变量引用和动态参数
5. 提供更清晰的语法结构和错误处理机制

## 关键字定义

### 基本语法

```
[HTTP请求],客户端: 'client_name',配置: '''
        method: POST
        url: /api/users
        request:
            headers:
                Content-Type: application/json
                Authorization: Bearer ${token}
            json:
                username: test_user
                email: test@example.com
        captures:
            user_id: ["jsonpath", "$.id"]
            status_code: ["status"]
            location: ["header", "Location"]
        asserts:
            - ["status", "eq", 201]
            - ["jsonpath", "$.message", "contains", "created"]
    '''
```

### 参数说明

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| 客户端 | 字符串 | 否 | YAML变量文件中定义的HTTP客户端配置名称，不提供则使用默认客户端 |
| 配置 | YAML字符串 | 是 | 包含请求、捕获和断言的YAML配置 |
| 保存响应 | 字符串 | 否 | 将完整响应保存到指定变量名中，便于后续使用 |
| 重试次数 | 整数 | 否 | 请求失败时的重试次数，默认为0 |
| 重试间隔 | 整数 | 否 | 重试间隔时间（秒），默认为1 |
| 禁用授权 | 布尔值 | 否 | 禁用客户端配置中的授权机制，默认为false |

## 请求配置详细说明

### 顶层结构

```yaml
method: HTTP方法(GET/POST/PUT/DELETE等)
url: 请求URL(可以是相对路径或完整URL)
request:
  # 请求相关配置
captures:
  # 响应捕获配置
asserts:
  # 断言配置
```

### request 部分

```yaml
request:
  params:  # URL查询参数
    param1: value1
    param2: value2
  headers:  # 请求头
    Content-Type: application/json
    X-Custom-Header: custom_value
  json:  # JSON请求体(自动设置Content-Type为application/json)
    key1: value1
    key2: value2
  data:  # 表单数据(自动设置Content-Type为application/x-www-form-urlencoded)
    field1: value1
    field2: value2
  files:  # 文件上传
    file_field: /path/to/file.txt
  cookies:  # Cookie
    cookie1: value1
  auth:  # 基本认证
    - username
    - password
  timeout: 30  # 超时时间(秒)
  allow_redirects: true  # 是否允许重定向
  verify: true  # 是否验证SSL证书
  cert: /path/to/cert.pem  # 客户端证书
  proxies:  # 代理设置
    http: http://proxy.example.com:8080
    https: https://proxy.example.com:8080
  disable_auth: false  # 是否禁用客户端配置中的授权机制
```

### captures 部分

捕获的变量会同时:
1. 自动注册到测试上下文(TestContext)中，可以在后续关键字中通过context对象访问
2. 设置为DSL变量，可以通过${变量名}语法直接引用

```yaml
captures:
  变量名1: ["提取器类型", "提取路径", "默认值(可选)"]
  变量名2: ["提取器类型", "提取路径"]
```

支持的提取器类型:

| 提取器类型 | 说明 | 示例 |
|-----------|------|------|
| jsonpath | 使用JSONPath从JSON响应中提取 | `["jsonpath", "$.data.id"]` |
| xpath | 使用XPath从HTML/XML响应中提取 | `["xpath", "//div[@class='user']/text()"]` |
| regex | 使用正则表达式从响应中提取 | `["regex", "id: ([0-9]+)"]` |
| header | 从响应头中提取 | `["header", "Location"]` |
| cookie | 从响应Cookie中提取 | `["cookie", "session_id"]` |
| status | 提取响应状态码 | `["status"]` |
| body | 提取整个响应体 | `["body"]` |
| response_time | 提取响应时间(毫秒) | `["response_time"]` |

### asserts 部分

```yaml
asserts:
  - ["提取位置", "断言类型", 参数1, 参数2, ...]
  - ["提取位置", "断言类型", 参数1, 参数2, ...]
```

支持的断言类型:

| 断言类型 | 参数 | 说明 | 示例 |
|---------|------|------|------|
| eq | 预期值 | 相等断言 | `["status", "eq", 200]` |
| neq | 预期值 | 不相等断言 | `["jsonpath", "$.error", "neq", null]` |
| contains | 子串 | 包含断言 | `["body", "contains", "success"]` |
| startswith | 前缀 | 前缀断言 | `["header", "Content-Type", "startswith", "application/json"]` |
| endswith | 后缀 | 后缀断言 | `["jsonpath", "$.message", "endswith", "completed"]` |
| matches | 正则表达式 | 正则匹配断言 | `["body", "matches", "id: [0-9]+"]` |
| lt | 上限值 | 小于断言 | `["jsonpath", "$.count", "lt", 100]` |
| lte | 上限值 | 小于等于断言 | `["jsonpath", "$.count", "lte", 100]` |
| gt | 下限值 | 大于断言 | `["jsonpath", "$.count", "gt", 0]` |
| gte | 下限值 | 大于等于断言 | `["jsonpath", "$.count", "gte", 0]` |
| exists | 无 | 存在性断言 | `["header", "Location", "exists"]` |
| not_exists | 无 | 不存在性断言 | `["jsonpath", "$.error", "not_exists"]` |
| length | 预期长度 | 长度断言 | `["jsonpath", "$.items", "length", 5]` |
| type | 预期类型 | 类型断言 | `["jsonpath", "$.id", "type", "string"]` |
| in | 列表 | 包含在列表中 | `["status", "in", [200, 201, 204]]` |
| not_in | 列表 | 不包含在列表中 | `["status", "not_in", [400, 401, 403, 404]]` |
| schema | JSON Schema | JSON Schema验证 | `["body", "schema", {"type": "object", "properties": {...}}]` |

## 客户端配置

在YAML变量文件中定义HTTP客户端配置:

```yaml
# 在变量文件中定义HTTP客户端配置
http_clients:
  default:  # 默认客户端配置
    base_url: https://api.example.com
    headers:
      User-Agent: pytest-dsl-client/1.0
      Accept: application/json
    timeout: 30
    verify_ssl: true
    session: true  # 是否保持会话
  
  staging:  # 测试环境客户端配置
    base_url: https://staging-api.example.com
    headers:
      User-Agent: pytest-dsl-client/1.0
      Accept: application/json
      X-API-Key: ${API_KEY}
    timeout: 60
    verify_ssl: false
    session: true
    retry:
      max_retries: 3
      retry_interval: 2
      retry_on_status: [500, 502, 503, 504]
    proxies:
      http: http://proxy.example.com:8080
      https: https://proxy.example.com:8080
    auth:  # 授权配置
      type: basic  # 授权类型: basic, token, api_key, oauth2, custom
      username: api_user
      password: api_password
  my_api:
    base_url: https://api.example.com
    auth:
      type: token
      token: ${MY_API_TOKEN}
```

### 授权配置说明

HTTP客户端支持多种授权方式，可以在客户端配置中设置:

#### 基本授权 (Basic Auth)

```yaml
auth:
  type: basic
  username: user
  password: password
```

#### 令牌授权 (Token Auth)

```yaml
auth:
  type: token
  token: your_token
  scheme: Bearer  # 可选，默认为"Bearer"
  header: Authorization  # 可选，默认为"Authorization"
```

#### API密钥授权 (API Key Auth)

```yaml
auth:
  type: api_key
  api_key: your_api_key
  key_name: X-API-Key  # 可选，默认为"X-API-Key"
  in_header: true  # 可选，默认为true
  in_query: false  # 可选，默认为false
  query_param_name: api_key  # 可选，如果与key_name不同
```

#### OAuth2授权

```yaml
auth:
  type: oauth2
  token_url: https://oauth.example.com/token
  client_id: your_client_id
  client_secret: your_client_secret
  scope: "read write"  # 可选
  grant_type: client_credentials  # 可选，默认为"client_credentials"
  username: user  # 可选，如果grant_type为"password"
  password: password  # 可选，如果grant_type为"password"
  token_refresh_window: 60  # 可选，默认为60秒
```

#### 自定义授权

```yaml
auth:
  type: custom
  provider_name: jwt_refresh_auth  # 已注册的自定义授权提供者名称
```

### 注册自定义授权提供者

可以通过代码注册自定义授权提供者:

```python
from pytest_dsl.core.auth_provider import register_auth_provider, CustomAuthProvider

class JWTAuthProvider(CustomAuthProvider):
    def apply_auth(self, request_kwargs):
        if "headers" not in request_kwargs:
            request_kwargs["headers"] = {}
        request_kwargs["headers"]["Authorization"] = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example_token"
        return request_kwargs


# 注册自定义授权提供者类
register_auth_provider("jwt_refresh_auth", JWTAuthProvider)
```

## 使用示例

### 基本GET请求

```
[HTTP请求],客户端: 'default',配置: '''
        method: GET
        url: /api/users
        request:
            params:
                page: 1
                limit: 10
        asserts:
            - ["status", "eq", 200]
            - ["jsonpath", "$.data", "exists"]
    '''
```

### 带认证的POST请求与变量捕获

```
[HTTP请求],客户端: 'default',配置: '''
        method: POST
        url: /api/auth/login
        request:
            json:
                username: ${username}
                password: ${password}
        captures:
            token: ["jsonpath", "$.token"]
            user_id: ["jsonpath", "$.user.id"]
        asserts:
            - ["status", "eq", 200]
            - ["jsonpath", "$.token", "exists"]
    '''
```

### 文件上传示例

```
[HTTP请求],客户端: 'default',配置: '''
        method: POST
        url: /api/upload
        request:
            files:
                file: ${file_path}
            data:
                description: "测试文件上传"
        captures:
            file_id: ["jsonpath", "$.file_id"]
        asserts:
            - ["status", "eq", 201]
            - ["jsonpath", "$.message", "contains", "上传成功"]
    '''
```

### 复杂断言示例

```
[HTTP请求],客户端: 'staging',配置: '''
        method: GET
        url: /api/products/${product_id}
        request:
            headers:
                Authorization: Bearer ${token}
        captures:
            price: ["jsonpath", "$.price"]
            stock: ["jsonpath", "$.stock"]
        asserts:
            - ["status", "eq", 200]
            - ["jsonpath", "$.price", "gt", 0]
            - ["jsonpath", "$.stock", "gte", 1]
            - ["jsonpath", "$.categories", "type", "array"]
            - ["jsonpath", "$.images", "length", 3]
            - ["response_time", "lt", 1000]  # 响应时间小于1000ms
    '''
```

### 条件断言示例

```
[HTTP请求],客户端: 'default',配置: '''
        method: GET
        url: /api/products/${product_id}
        request:
            headers:
                Authorization: Bearer ${token}
        captures:
            status_code: ["status"]
            product_data: ["body"]
        asserts:
            - ["status", "in", [200, 404]]  # 状态码可能是200或404
    '''

# 根据状态码进行条件断言
[断言],条件:'${status_code} == 200',消息:'产品不存在'
'''
```

### 请求模板示例

在YAML变量文件中定义请求模板:

```yaml
# 在变量文件中定义请求模板
http_templates:
  auth_request:
    method: POST
    url: /api/auth/login
    request:
      headers:
        Content-Type: application/json
      json:
        username: ""  # 将在使用时填充
        password: ""  # 将在使用时填充
    asserts:
      - ["status", "eq", 200]
      - ["jsonpath", "$.token", "exists"]
```

使用模板:

```
[HTTP请求],客户端: 'default',模板: 'auth_request',配置: '''
        request:
            json:
                username: ${username}
                password: ${password}
        captures:
            token: ["jsonpath", "$.token"]
    '''
```

## 高级功能
### 1. 会话管理

```
# 创建并使用命名会话
[HTTP请求],客户端: 'default',会话: 'my_session',配置: '''
        method: POST
        url: /api/auth/login
        request:
            json:
                username: ${username}
                password: ${password}
        captures:
            token: ["jsonpath", "$.token"]
        asserts:
            - ["status", "eq", 200]
    '''

# 在后续请求中使用同一会话
[HTTP请求],客户端: 'default',会话: 'my_session',  # 使用之前创建的会话
    配置: '''
        method: GET
        url: /api/user/profile
        asserts:
            - ["status", "eq", 200]
    '''
```

### 2. 性能测试

```
[HTTP请求],客户端: 'default',配置: '''
        method: GET
        url: /api/products
        captures:
            response_time: ["response_time"]
        asserts:
            - ["status", "eq", 200]
            - ["response_time", "lt", 500]  # 响应时间小于500ms
    '''
```

## 实现注意事项

1. **变量替换**：在执行请求前，处理配置中的变量引用（`${var}`格式）
2. **客户端管理**：维护HTTP客户端实例池，根据配置名称复用客户端
3. **错误处理**：提供详细的错误信息，包括请求失败、断言失败等
4. **会话管理**：支持在测试用例间保持会话状态
5. **超时控制**：支持连接超时和读取超时配置
6. **重试机制**：支持请求失败后的重试策略
7. **日志记录**：记录请求和响应详情，便于调试
8. **代理支持**：支持配置HTTP代理
9. **模板机制**：支持定义和使用请求模板
10. **条件断言**：支持基于条件的断言
11. **性能指标**：捕获和断言响应时间等性能指标


## 实现路径

1. 创建HTTP客户端管理模块
2. 实现HTTP请求关键字
3. 实现变量捕获和断言功能
4. 集成到测试上下文和YAML变量管理器
5. 添加Allure报告支持
6. 实现高级功能（会话管理、模板、批量请求等）