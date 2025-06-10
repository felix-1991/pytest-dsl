# HTTP API测试

pytest-dsl提供了强大的HTTP测试功能，让API测试变得简单直观。本章将详细介绍如何使用HTTP关键字进行API测试。

## 基本概念

### HTTP请求关键字

`[HTTP请求]`是pytest-dsl的核心关键字，用于执行HTTP请求并进行API接口测试。它支持：

- 请求发送（GET、POST、PUT、DELETE等）
- 响应捕获（状态码、响应体、头部等）
- 断言验证（状态码、JSON路径、响应内容等）
- 断言重试（异步API、状态变化等场景的自动重试）
- 会话管理（Cookie、认证状态保持）

### 基本语法

```python
[HTTP请求], 客户端: "client_name", 配置: '''
    method: GET
    url: /api/endpoint
    request:
        # 请求配置
    captures:
        # 响应捕获
    asserts:
        # 断言验证
'''
```

## 快速开始

### 最简单的GET请求

```python
@name: "简单GET请求"

[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
    asserts:
        - ["status", "eq", 200]
'''
```

### 带参数的GET请求

```python
@name: "带参数的GET请求"

[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts
    request:
        params:
            userId: 1
            _limit: 5
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$", "length", "eq", 5]
'''
```

## HTTP客户端配置

### YAML配置文件

在YAML配置文件中定义HTTP客户端：

```yaml
# config.yaml
http_clients:
  default:
    base_url: "https://jsonplaceholder.typicode.com"
    timeout: 30
    headers:
      User-Agent: "pytest-dsl/1.0"
      Accept: "application/json"
    
  api_server:
    base_url: "https://api.example.com"
    timeout: 60
    headers:
      Content-Type: "application/json"
      X-API-Key: "${API_KEY}"
    auth:
      type: "token"
      token: "${AUTH_TOKEN}"
```

## 默认授权配置

pytest-dsl支持在HTTP客户端配置中设置默认授权，一旦配置后，所有使用该客户端的请求都会自动携带授权信息，无需在每个请求中单独设置。

### 支持的授权类型

#### 1. Bearer Token认证

最常用的API认证方式，适用于JWT、OAuth2等场景：

```yaml
# config.yaml
http_clients:
  api_with_token:
    base_url: "https://api.example.com"
    auth:
      type: "token"
      token: "${AUTH_TOKEN}"        # 使用变量引用
      scheme: "Bearer"              # 认证方案，默认为Bearer
      header: "Authorization"       # 认证头名称，默认为Authorization
```

使用示例：

```python
# 请求会自动携带 Authorization: Bearer <token>
[HTTP请求], 客户端: "api_with_token", 配置: '''
    method: GET
    url: /protected/users
    asserts:
        - ["status", "eq", 200]
'''
```

#### 2. Basic认证

HTTP基本认证，使用用户名密码：

```yaml
# config.yaml
http_clients:
  basic_auth_api:
    base_url: "https://api.example.com"
    auth:
      type: "basic"
      username: "${API_USERNAME}"
      password: "${API_PASSWORD}"
```

使用示例：

```python
# 请求会自动携带 Authorization: Basic <base64(username:password)>
[HTTP请求], 客户端: "basic_auth_api", 配置: '''
    method: GET
    url: /admin/users
    asserts:
        - ["status", "eq", 200]
'''
```

#### 3. API Key认证

支持Header或查询参数方式的API Key认证：

```yaml
# config.yaml
http_clients:
  # Header方式API Key
  apikey_header:
    base_url: "https://api.example.com"
    auth:
      type: "api_key"
      api_key: "${API_KEY}"
      key_name: "X-API-Key"         # API Key头名称，默认为X-API-Key
      in_header: true               # 是否在请求头中添加，默认为true
      in_query: false               # 是否在查询参数中添加，默认为false

  # 查询参数方式API Key
  apikey_query:
    base_url: "https://api.example.com"
    auth:
      type: "api_key"
      api_key: "${API_KEY}"
      in_header: false
      in_query: true
      query_param_name: "api_key"   # 查询参数名称

  # 同时支持Header和查询参数
  apikey_both:
    base_url: "https://api.example.com"
    auth:
      type: "api_key"
      api_key: "${API_KEY}"
      key_name: "X-API-Key"
      in_header: true
      in_query: true
      query_param_name: "key"
```

使用示例：

```python
# Header方式：请求会自动携带 X-API-Key: <api_key>
[HTTP请求], 客户端: "apikey_header", 配置: '''
    method: GET
    url: /data
'''

# 查询参数方式：请求URL会自动添加 ?api_key=<api_key>
[HTTP请求], 客户端: "apikey_query", 配置: '''
    method: GET
    url: /data
'''
```

#### 4. OAuth2 Client Credentials认证

适用于服务器到服务器的认证场景：

```yaml
# config.yaml
http_clients:
  oauth2_api:
    base_url: "https://api.example.com"
    auth:
      type: "oauth2"
      token_url: "https://auth.example.com/oauth/token"
      client_id: "${OAUTH_CLIENT_ID}"
      client_secret: "${OAUTH_CLIENT_SECRET}"
      scope: "read write"                    # 可选，权限范围
      grant_type: "client_credentials"       # 授权类型，默认为client_credentials
      token_refresh_window: 60               # 令牌刷新窗口(秒)，默认60秒
```

OAuth2密码模式示例：

```yaml
# config.yaml
http_clients:
  oauth2_password:
    base_url: "https://api.example.com"
    auth:
      type: "oauth2"
      token_url: "https://auth.example.com/oauth/token"
      client_id: "${OAUTH_CLIENT_ID}"
      client_secret: "${OAUTH_CLIENT_SECRET}"
      grant_type: "password"
      username: "${OAUTH_USERNAME}"
      password: "${OAUTH_PASSWORD}"
      scope: "read write"
```

使用示例：

```python
# OAuth2会自动获取token并携带 Authorization: Bearer <access_token>
[HTTP请求], 客户端: "oauth2_api", 配置: '''
    method: GET
    url: /protected/data
    asserts:
        - ["status", "eq", 200]
'''
```

### 使用配置

```bash
pytest-dsl tests/ --yaml-vars config.yaml
```

```python
# 使用配置中的客户端，会自动应用默认授权
[HTTP请求], 客户端: "api_server", 配置: '''
    method: GET
    url: /users
'''
```

### 默认授权的优势

1. **简化测试代码**：无需在每个请求中重复设置认证信息
2. **统一管理**：认证信息集中配置，便于维护和更新
3. **环境隔离**：不同环境可以使用不同的配置文件
4. **安全性**：敏感信息可以通过环境变量引用，避免硬编码

### 禁用默认授权

在某些测试场景中，您可能需要测试未授权的访问，可以临时禁用默认授权：

```python
# 临时禁用客户端配置中的授权
[HTTP请求], 客户端: "api_server", 禁用授权: true, 配置: '''
    method: GET
    url: /public-endpoint
    asserts:
        - ["status", "eq", 200]
'''

# 测试未授权访问受保护资源
[HTTP请求], 客户端: "api_server", 禁用授权: true, 配置: '''
    method: GET
    url: /protected-endpoint
    asserts:
        - ["status", "eq", 401]  # 期望返回未授权错误
'''
```

### 覆盖默认授权

如果需要为特定请求使用不同的授权信息，可以在请求配置中覆盖：

```python
# 使用不同的token覆盖默认授权
[HTTP请求], 客户端: "api_server", 配置: '''
    method: GET
    url: /admin-only
    request:
        headers:
            Authorization: "Bearer ${ADMIN_TOKEN}"  # 覆盖默认token
    asserts:
        - ["status", "eq", 200]
'''
```

### 变量引用

默认授权配置支持变量引用，可以从环境变量或YAML变量中动态获取认证信息：

```yaml
# config.yaml
# 全局变量定义
variables:
  api_token: "${API_TOKEN}"          # 从环境变量获取
  api_username: "admin"              # 静态值
  api_password: "${API_PASSWORD}"    # 从环境变量获取

http_clients:
  dynamic_auth:
    base_url: "https://api.example.com"
    auth:
      type: "token"
      token: "${api_token}"           # 引用全局变量
```

环境变量设置：

```bash
export API_TOKEN="your_actual_token_here"
export API_PASSWORD="your_password_here"
pytest-dsl tests/ --yaml-vars config.yaml
```

## 请求配置详解

### HTTP方法

```python
# GET请求
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /api/users
'''

# POST请求
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: /api/users
    request:
        json:
            name: "张三"
            email: "zhangsan@example.com"
'''

# PUT请求
[HTTP请求], 客户端: "default", 配置: '''
    method: PUT
    url: /api/users/1
    request:
        json:
            name: "李四"
'''

# DELETE请求
[HTTP请求], 客户端: "default", 配置: '''
    method: DELETE
    url: /api/users/1
'''
```

### 请求参数

```python
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /api/search
    request:
        params:
            q: "pytest-dsl"
            page: 1
            limit: 10
        headers:
            Authorization: "Bearer ${token}"
            X-Custom-Header: "custom-value"
        timeout: 60
'''
```

### 请求体

#### JSON请求体

```python
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: /api/users
    request:
        json:
            name: "张三"
            age: 30
            email: "zhangsan@example.com"
            preferences:
                theme: "dark"
                language: "zh-CN"
'''
```

#### 表单数据

```python
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: /api/login
    request:
        data:
            username: "admin"
            password: "admin123"
        headers:
            Content-Type: "application/x-www-form-urlencoded"
'''
```

#### 文件上传

```python
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: /api/upload
    request:
        files:
            file: "/path/to/file.txt"
        data:
            description: "测试文件"
'''
```

## 响应捕获

### 基本捕获

```python
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/users/1
    captures:
        user_id: ["jsonpath", "$.id"]
        user_name: ["jsonpath", "$.name"]
        user_email: ["jsonpath", "$.email"]
        status_code: ["status"]
        response_body: ["body"]
    asserts:
        - ["status", "eq", 200]
'''

# 使用捕获的变量
[打印], 内容: "用户ID: ${user_id}"
[打印], 内容: "用户名: ${user_name}"
[打印], 内容: "邮箱: ${user_email}"
```

### 捕获器类型

| 捕获器类型 | 说明 | 示例 |
|-----------|------|------|
| jsonpath | 使用JSONPath从JSON响应中提取 | `["jsonpath", "$.data.id"]` |
| xpath | 使用XPath从HTML/XML响应中提取 | `["xpath", "//div[@class='user']/text()"]` |
| regex | 使用正则表达式从响应中提取 | `["regex", "id: ([0-9]+)"]` (有捕获组返回第一个匹配，无捕获组返回所有匹配) |
| header | 从响应头中提取 | `["header", "Location"]` |
| cookie | 从响应Cookie中提取 | `["cookie", "session_id"]` |
| status | 提取响应状态码 | `["status"]` |
| body | 提取整个响应体 | `["body"]` |
| response_time | 提取响应时间(毫秒) | `["response_time"]` |

### 复杂数据捕获

```python
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/users
    captures:
        first_user_name: ["jsonpath", "$[0].name"]
        last_user_id: ["jsonpath", "$[-1].id"]
        user_count: ["jsonpath", "$", "length"]
        all_emails: ["jsonpath", "$[*].email"]
    asserts:
        - ["status", "eq", 200]
'''

[打印], 内容: "第一个用户: ${first_user_name}"
[打印], 内容: "最后一个用户ID: ${last_user_id}"
[打印], 内容: "用户总数: ${user_count}"
```

### 正则表达式捕获特殊说明

正则表达式捕获器有特殊的行为规则：

```python
# 示例响应文本：
# "Orders: ORDER-2024-001, ORDER-2024-002, ORDER-2024-003"

[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /api/orders
    captures:
        # 无捕获组：返回所有匹配项的列表
        all_orders: ["regex", "ORDER-\\d{4}-\\d{3}"]
        # 结果：["ORDER-2024-001", "ORDER-2024-002", "ORDER-2024-003"]
        
        # 有捕获组：只返回第一个匹配的捕获组内容
        first_order: ["regex", "(ORDER-\\d{4}-\\d{3})"]
        # 结果："ORDER-2024-001"
        
        # 多个捕获组：返回第一个匹配的所有捕获组组成的元组
        order_parts: ["regex", "(ORDER)-(\\d{4})-(\\d{3})"]
        # 结果：("ORDER", "2024", "001")
'''
```

## 断言验证

### 基本断言

```python
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.id", "eq", 1]
        - ["jsonpath", "$.title", "exists"]
        - ["jsonpath", "$.body", "contains", "quia"]
        - ["header", "Content-Type", "contains", "application/json"]
'''
```

### 断言类型详解

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
| length | 预期长度/比较操作符+预期长度 | 长度断言 | `["jsonpath", "$.items", "length", 5]` 或 `["jsonpath", "$.items", "length", "eq", 5]` |
| type | 预期类型 | 类型断言 | `["jsonpath", "$.id", "type", "string"]` (支持: string, number, boolean, array, object, null) |
| schema | JSON Schema | JSON Schema验证 | `["body", "schema", {"type": "object", "properties": {...}}]` |
| in | 列表 | 包含在列表中 | `["status", "in", [200, 201, 204]]` |
| not_in | 列表 | 不包含在列表中 | `["status", "not_in", [400, 401, 403, 404]]` |

### 复杂断言示例

```python
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/users
    asserts:
        # 状态码断言
        - ["status", "in", [200, 201]]
        
        # 响应时间断言
        - ["response_time", "lt", 2000]
        
        # 数组长度断言
        - ["jsonpath", "$", "length", "gt", 0]
        - ["jsonpath", "$", "length", "eq", 10]  # 5参数格式
        - ["jsonpath", "$", "length", 10]        # 4参数格式（等价于上面）
        
        # 字段存在性断言
        - ["jsonpath", "$[0].name", "exists"]
        - ["jsonpath", "$[0].email", "exists"]
        
        # 字段类型断言
        - ["jsonpath", "$[0].id", "type", "number"]
        - ["jsonpath", "$[0].name", "type", "string"]
        
        # 字段值断言
        - ["jsonpath", "$[0].email", "contains", "@"]
        - ["jsonpath", "$[0].website", "startswith", "http"]
        
        # JSON Schema验证
        - ["body", "schema", {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "email": {"type": "string", "format": "email"}
                },
                "required": ["id", "name", "email"]
            }
        }]
'''
```

## 会话管理

### 基本会话

```python
@name: "会话管理示例"

# 登录获取会话
[HTTP请求], 客户端: "default", 会话: "user_session", 配置: '''
    method: POST
    url: https://httpbin.org/cookies/set/session_id/abc123
    captures:
        session_cookie: ["cookie", "session_id"]
'''

# 使用会话访问受保护资源
[HTTP请求], 客户端: "default", 会话: "user_session", 配置: '''
    method: GET
    url: https://httpbin.org/cookies
    asserts:
        - ["jsonpath", "$.cookies.session_id", "eq", "abc123"]
'''
```

### 认证流程示例

#### 方式一：手动管理认证流程

适用于需要动态获取token的场景：

```python
@name: "手动认证流程"

# 第一步：登录获取token
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: https://httpbin.org/post
    request:
        json:
            username: "admin"
            password: "admin123"
    captures:
        auth_token: ["jsonpath", "$.json.username"]  # 模拟token
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "用户登录"

# 第二步：使用token访问API
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://httpbin.org/headers
    request:
        headers:
            Authorization: "Bearer ${auth_token}"
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.headers.Authorization", "contains", "Bearer"]
''', 步骤名称: "访问受保护资源"
```

#### 方式二：使用默认授权配置（推荐）

适用于已知认证信息的场景：

```yaml
# config.yaml
http_clients:
  authenticated_api:
    base_url: "https://api.example.com"
    auth:
      type: "token"
      token: "${API_TOKEN}"

  basic_auth_api:
    base_url: "https://admin.example.com"
    auth:
      type: "basic"
      username: "${ADMIN_USERNAME}"
      password: "${ADMIN_PASSWORD}"
```

```python
@name: "默认授权认证流程"

# 直接使用配置的Bearer Token认证
[HTTP请求], 客户端: "authenticated_api", 配置: '''
    method: GET
    url: /users
    captures:
        user_list: ["jsonpath", "$"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$", "type", "array"]
''', 步骤名称: "获取用户列表(自动Bearer认证)"

# 使用Basic认证访问管理接口
[HTTP请求], 客户端: "basic_auth_api", 配置: '''
    method: GET
    url: /admin/stats
    captures:
        total_users: ["jsonpath", "$.total_users"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.total_users", "type", "number"]
''', 步骤名称: "获取统计信息(自动Basic认证)"

# 测试未授权访问
[HTTP请求], 客户端: "authenticated_api", 禁用授权: true, 配置: '''
    method: GET
    url: /protected-endpoint
    asserts:
        - ["status", "eq", 401]
        - ["jsonpath", "$.error", "contains", "Unauthorized"]
''', 步骤名称: "测试未授权访问"
```

#### 方式三：混合认证流程

结合动态获取和默认配置：

```python
@name: "混合认证流程"

# 使用默认客户端登录获取特殊权限token
[HTTP请求], 客户端: "basic_auth_api", 配置: '''
    method: POST
    url: /auth/admin-token
    request:
        json:
            scope: "admin:write"
    captures:
        admin_token: ["jsonpath", "$.access_token"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.access_token", "exists"]
''', 步骤名称: "获取管理员权限token"

# 使用特殊token执行高权限操作
[HTTP请求], 客户端: "authenticated_api", 配置: '''
    method: POST
    url: /admin/users
    request:
        headers:
            Authorization: "Bearer ${admin_token}"  # 覆盖默认token
        json:
            username: "newuser"
            role: "admin"
    asserts:
        - ["status", "eq", 201]
''', 步骤名称: "创建管理员用户(特殊权限)"
```

## 断言重试机制

HTTP请求断言重试功能允许您在断言失败时自动重试请求，这对于测试异步API或需要等待状态变化的场景非常有用。

### 基本概念

断言重试功能主要解决以下场景：

1. **异步处理**：当API需要在后台处理请求，返回结果需要时间
2. **状态转换**：需要等待资源状态从一个状态转变为另一个状态
3. **数据准备**：需要等待数据被生成或更新
4. **负载平衡**：在高负载下，某些请求可能临时失败需要重试

### 重试配置方式

断言重试支持以下几种配置方式，按优先级从高到低排序：

#### 1. 独立的retry_assertions配置（推荐）

新增的独立配置块，与asserts同级，可以更集中和清晰地定义重试策略：

```python
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://api.example.com/tasks/123
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.status", "eq", "completed"]
    retry_assertions:
        count: 3                # 全局重试次数
        interval: 1             # 全局重试间隔（秒）
        all: true               # 是否重试所有断言
        indices: [1]            # 指定要重试的断言索引（从0开始计数）
        specific:               # 针对特定断言的重试配置
            "1": {              # 断言索引为1的特定配置
                count: 5,       # 特定重试次数
                interval: 2     # 特定重试间隔
            }
'''
```

#### 2. 全局重试配置（传统方式）

在请求配置中设置全局重试策略：

```python
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://api.example.com/status
    retry:
        count: 3
        interval: 1
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.data", "exists"]
'''
```

#### 3. 关键字参数

通过关键字参数设置重试（向后兼容旧版本）：

```python
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://httpbin.org/delay/2
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.url", "exists"]
''', 断言重试次数: 3, 断言重试间隔: 1, 步骤名称: "测试断言重试"
```

### 独立重试配置详解

推荐使用新的`retry_assertions`配置块，它提供了更强大和灵活的断言重试控制：

```python
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://api.example.com/tasks/123
    asserts:
        - ["status", "eq", 200]               # 索引0
        - ["jsonpath", "$.status", "eq", "completed"]  # 索引1
        - ["jsonpath", "$.result", "exists"]  # 索引2
    retry_assertions:
        # 全局设置
        count: 3                # 重试次数，默认为3次
        interval: 1.5           # 重试间隔（秒），默认为1秒
        
        # 控制哪些断言会重试
        all: true               # 设置为true时重试所有断言（默认为false）
        indices: [1, 2]         # 指定断言索引列表（从0开始计数）
        
        # 为特定断言指定不同的重试策略
        specific:
            "1": {              # 断言索引为1的配置
                count: 5,       # 特定重试次数
                interval: 2     # 特定重试间隔
            }
            "2": {              # 断言索引为2的配置
                count: 10,
                interval: 0.5
            }
'''
```

### 重试配置优先级

当存在多种重试配置时，按照以下优先级处理：

1. `retry_assertions.specific`中针对特定断言的配置 (最高优先级)
2. `retry_assertions`中的全局设置
3. 传统的`retry`配置
4. 关键字参数配置
5. 默认值 (最低优先级)

### 重试行为说明

1. **选择性重试**：只有标记为可重试的断言失败时才会重试
2. **重试策略**：每次重试前会等待设定的间隔时间
3. **最大重试次数**：达到最大重试次数后，如果断言仍然失败，将抛出异常
4. **优先级**：特定断言配置优先于全局配置
5. **不同断言不同配置**：可以为不同断言设置不同的重试策略

### 实际应用示例

#### 异步任务状态检查

```python
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://api.example.com/tasks/123
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.status", "eq", "completed"]
    retry_assertions:
        count: 5
        interval: 2
        all: true
''', 步骤名称: "等待任务完成"
```

#### 只对特定断言进行重试

```python
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://api.example.com/tasks/123
    asserts:
        - ["status", "eq", 200]                    # 索引0，不重试
        - ["jsonpath", "$.status", "eq", "completed"]  # 索引1，将重试
        - ["jsonpath", "$.result", "exists"]       # 索引2，将重试
    retry_assertions:
        count: 3
        interval: 1
        indices: [1, 2]  # 只重试索引1和2的断言
''', 步骤名称: "检查任务状态和结果"
```

#### 为不同断言设置不同重试策略

```python
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://api.example.com/process/456
    asserts:
        - ["status", "eq", 200]                    # 索引0
        - ["jsonpath", "$.stage", "eq", "processing"]  # 索引1
        - ["jsonpath", "$.final_result", "exists"] # 索引2
    retry_assertions:
        count: 3  # 全局重试设置
        interval: 1
        indices: [1, 2]  # 只重试索引1和2
        specific:
            "1": {  # 阶段检查使用较短间隔
                count: 10,
                interval: 1
            }
            "2": {  # 最终结果检查使用较长间隔
                count: 5,
                interval: 5
            }
''', 步骤名称: "监控处理过程"
```

### 最佳实践

1. **使用独立的retry_assertions配置**：更清晰地定义重试策略
2. **适用场景识别**：只对可能需要等待的断言启用重试，比如状态检查
3. **合理的重试间隔**：设置与业务流程匹配的重试间隔
4. **最大重试次数控制**：避免过长的等待时间
5. **断言分类**：将致命错误和临时状态区分对待
   - 致命错误（如404状态码）不应该重试
   - 临时状态（如"pending"状态）适合重试

### 注意事项

1. 每次重试都会重新发送完整的HTTP请求
2. 断言重试会增加测试执行时间
3. 对于幂等API（GET、HEAD等）比非幂等API（POST、PUT等）更适合使用重试
4. 当使用非幂等API时，需要考虑重试的副作用

## 实际应用示例

### 用户管理API测试

```python
@name: "用户管理API测试"
@description: "测试用户的增删改查功能"

# 创建用户
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: https://jsonplaceholder.typicode.com/users
    request:
        json:
            name: "测试用户"
            username: "testuser"
            email: "test@example.com"
    captures:
        new_user_id: ["jsonpath", "$.id"]
    asserts:
        - ["status", "eq", 201]
        - ["jsonpath", "$.name", "eq", "测试用户"]
''', 步骤名称: "创建用户"

# 获取用户信息
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/users/1
    captures:
        user_name: ["jsonpath", "$.name"]
        user_email: ["jsonpath", "$.email"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.name", "exists"]
''', 步骤名称: "获取用户信息"

# 更新用户信息
[HTTP请求], 客户端: "default", 配置: '''
    method: PUT
    url: https://jsonplaceholder.typicode.com/users/1
    request:
        json:
            name: "更新后的用户名"
            email: "${user_email}"
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.name", "eq", "更新后的用户名"]
''', 步骤名称: "更新用户信息"

# 删除用户
[HTTP请求], 客户端: "default", 配置: '''
    method: DELETE
    url: https://jsonplaceholder.typicode.com/users/1
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "删除用户"
```

### 电商API测试流程

```python
@name: "电商API测试流程"

# 用户登录
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: https://httpbin.org/post
    request:
        json:
            username: "customer"
            password: "password123"
    captures:
        access_token: ["jsonpath", "$.json.username"]  # 模拟token
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "用户登录"

# 浏览商品
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts
    request:
        params:
            category: "electronics"
            limit: 10
        headers:
            Authorization: "Bearer ${access_token}"
    captures:
        product_list: ["jsonpath", "$"]
        first_product_id: ["jsonpath", "$[0].id"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$", "length", "gt", 0]
''', 步骤名称: "浏览商品列表"

# 添加到购物车
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: https://httpbin.org/post
    request:
        headers:
            Authorization: "Bearer ${access_token}"
        json:
            product_id: ${first_product_id}
            quantity: 2
    captures:
        cart_item_id: ["jsonpath", "$.json.product_id"]
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "添加商品到购物车"

# 查看购物车
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://httpbin.org/headers
    request:
        headers:
            Authorization: "Bearer ${access_token}"
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "查看购物车"

# 结算订单
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: https://httpbin.org/post
    request:
        headers:
            Authorization: "Bearer ${access_token}"
        json:
            payment_method: "credit_card"
            shipping_address: "北京市朝阳区"
    captures:
        order_id: ["jsonpath", "$.json.payment_method"]  # 模拟订单ID
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "创建订单"

[打印], 内容: "订单创建成功，订单ID: ${order_id}"
```

### 企业API测试流程（使用默认授权）

使用默认授权配置的完整企业API测试示例：

```yaml
# enterprise_config.yaml
variables:
  api_token: "${ENTERPRISE_API_TOKEN}"
  admin_username: "${ADMIN_USERNAME}"
  admin_password: "${ADMIN_PASSWORD}"

http_clients:
  # 企业API客户端（Bearer Token认证）
  enterprise_api:
    base_url: "https://api.enterprise.com"
    timeout: 30
    headers:
      Content-Type: "application/json"
      User-Agent: "pytest-dsl/enterprise-test"
    auth:
      type: "token"
      token: "${api_token}"
      scheme: "Bearer"

  # 管理员API客户端（Basic认证）
  admin_api:
    base_url: "https://admin.enterprise.com"
    timeout: 60
    auth:
      type: "basic"
      username: "${admin_username}"
      password: "${admin_password}"

  # 第三方API客户端（API Key认证）
  partner_api:
    base_url: "https://partner-api.example.com"
    auth:
      type: "api_key"
      api_key: "${PARTNER_API_KEY}"
      key_name: "X-Partner-Key"
```

```python
@name: "企业API完整测试流程"
@description: "使用默认授权配置的企业级API测试"

# 1. 获取企业信息（自动Bearer Token认证）
[HTTP请求], 客户端: "enterprise_api", 配置: '''
    method: GET
    url: /v1/company/info
    captures:
        company_id: ["jsonpath", "$.company.id"]
        company_name: ["jsonpath", "$.company.name"]
        employee_count: ["jsonpath", "$.company.employee_count"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.company.id", "exists"]
        - ["jsonpath", "$.company.status", "eq", "active"]
''', 步骤名称: "获取企业基本信息"

[打印], 内容: "企业信息: ${company_name} (ID: ${company_id}), 员工数: ${employee_count}"

# 2. 获取部门列表（自动Bearer Token认证）
[HTTP请求], 客户端: "enterprise_api", 配置: '''
    method: GET
    url: /v1/departments
    request:
        params:
            company_id: ${company_id}
            include_employees: true
    captures:
        departments: ["jsonpath", "$.departments"]
        first_dept_id: ["jsonpath", "$.departments[0].id"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.departments", "type", "array"]
        - ["jsonpath", "$.departments", "length", "gt", 0]
''', 步骤名称: "获取部门列表"

# 3. 创建新员工（自动Bearer Token认证）
[HTTP请求], 客户端: "enterprise_api", 配置: '''
    method: POST
    url: /v1/employees
    request:
        json:
            name: "张三"
            email: "zhangsan@enterprise.com"
            department_id: ${first_dept_id}
            position: "软件工程师"
            hire_date: "2024-01-15"
    captures:
        new_employee_id: ["jsonpath", "$.employee.id"]
        employee_number: ["jsonpath", "$.employee.employee_number"]
    asserts:
        - ["status", "eq", 201]
        - ["jsonpath", "$.employee.name", "eq", "张三"]
        - ["jsonpath", "$.employee.status", "eq", "active"]
''', 步骤名称: "创建新员工"

[打印], 内容: "创建员工成功: ${employee_number}"

# 4. 管理员操作 - 审批员工（自动Basic认证）
[HTTP请求], 客户端: "admin_api", 配置: '''
    method: POST
    url: /admin/employees/${new_employee_id}/approve
    request:
        json:
            action: "approve"
            approver_comment: "员工信息审核通过"
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.status", "eq", "approved"]
''', 步骤名称: "管理员审批员工"

# 5. 同步到第三方系统（自动API Key认证）
[HTTP请求], 客户端: "partner_api", 配置: '''
    method: POST
    url: /sync/employee
    request:
        json:
            employee_id: ${new_employee_id}
            company_id: ${company_id}
            sync_type: "new_employee"
    captures:
        sync_id: ["jsonpath", "$.sync_id"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.sync_status", "eq", "success"]
''', 步骤名称: "同步员工到第三方系统"

# 6. 验证同步状态（自动API Key认证）
[HTTP请求], 客户端: "partner_api", 配置: '''
    method: GET
    url: /sync/${sync_id}/status
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.status", "eq", "completed"]
        - ["jsonpath", "$.error_count", "eq", 0]
    retry_assertions:
        count: 5
        interval: 2
        indices: [1, 2]  # 重试状态和错误计数检查
''', 步骤名称: "验证第三方同步状态"

# 7. 测试权限控制 - 普通用户访问管理接口（应该失败）
[HTTP请求], 客户端: "enterprise_api", 配置: '''
    method: GET
    url: /admin/company/settings
    asserts:
        - ["status", "eq", 403]
        - ["jsonpath", "$.error", "contains", "insufficient_privileges"]
''', 步骤名称: "测试权限控制"

# 8. 测试未授权访问（禁用默认授权）
[HTTP请求], 客户端: "enterprise_api", 禁用授权: true, 配置: '''
    method: GET
    url: /v1/company/info
    asserts:
        - ["status", "eq", 401]
        - ["jsonpath", "$.error", "eq", "unauthorized"]
''', 步骤名称: "测试未授权访问"

# 9. 清理测试数据（管理员权限）
[HTTP请求], 客户端: "admin_api", 配置: '''
    method: DELETE
    url: /admin/employees/${new_employee_id}
    request:
        json:
            reason: "测试数据清理"
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "清理测试员工数据"

[打印], 内容: "✅ 企业API测试流程完成"
```

运行测试：

```bash
# 设置环境变量
export ENTERPRISE_API_TOKEN="your_enterprise_token"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="admin_password"
export PARTNER_API_KEY="partner_api_key_123"

# 运行测试
pytest-dsl enterprise_test.dsl --yaml-vars enterprise_config.yaml
```

## 最佳实践

### 1. 使用有意义的步骤名称

```python
# ✅ 好的实践
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /api/users/1
''', 步骤名称: "获取用户详细信息"

# ❌ 避免的做法
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /api/users/1
'''  # 没有步骤名称
```

### 2. 合理使用变量捕获

```python
# ✅ 捕获需要的数据
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /api/users/1
    captures:
        user_id: ["jsonpath", "$.id"]
        user_name: ["jsonpath", "$.name"]
    # 只捕获后续会用到的数据
'''

# 在后续请求中使用
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /api/users/${user_id}/posts
'''
```

### 3. 分层断言策略

```python
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /api/users
    asserts:
        # 第一层：基本断言
        - ["status", "eq", 200]
        - ["response_time", "lt", 2000]
        
        # 第二层：结构断言
        - ["jsonpath", "$", "type", "array"]
        - ["jsonpath", "$", "length", "gt", 0]
        
        # 第三层：内容断言
        - ["jsonpath", "$[0].id", "exists"]
        - ["jsonpath", "$[0].name", "type", "string"]
        - ["jsonpath", "$[0].email", "contains", "@"]
'''
```

### 4. 合理使用默认授权

```python
# ✅ 推荐：使用默认授权配置
# config.yaml中配置授权
http_clients:
  api_client:
    base_url: "https://api.example.com"
    auth:
      type: "token"
      token: "${API_TOKEN}"

# 测试代码简洁
[HTTP请求], 客户端: "api_client", 配置: '''
    method: GET
    url: /protected/data
'''

# ❌ 避免：每个请求都手动设置授权
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://api.example.com/protected/data
    request:
        headers:
            Authorization: "Bearer ${token}"
'''
```

### 5. 环境隔离策略

```yaml
# dev_config.yaml
http_clients:
  api_client:
    base_url: "https://dev-api.example.com"
    auth:
      type: "token"
      token: "${DEV_API_TOKEN}"

# prod_config.yaml  
http_clients:
  api_client:
    base_url: "https://api.example.com"
    auth:
      type: "token"
      token: "${PROD_API_TOKEN}"
```

```bash
# 开发环境测试
pytest-dsl tests/ --yaml-vars dev_config.yaml

# 生产环境测试
pytest-dsl tests/ --yaml-vars prod_config.yaml
```

### 4. 错误处理

```python
# 测试错误场景
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /api/users/999999  # 不存在的用户
    asserts:
        - ["status", "eq", 404]
        - ["jsonpath", "$.error", "exists"]
        - ["jsonpath", "$.message", "contains", "not found"]
''', 步骤名称: "测试用户不存在的情况"
```

## 常见问题

### Q: 如何处理HTTPS证书验证？

A: 在HTTP客户端配置中设置：

```yaml
http_clients:
  default:
    verify_ssl: false  # 跳过SSL验证（仅用于测试环境）
```

### Q: 如何设置请求超时？

A: 在请求配置中设置：

```python
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /api/slow-endpoint
    request:
        timeout: 60  # 60秒超时
'''
```

### Q: 如何处理动态URL？

A: 使用变量替换：

```python
user_id = 123
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /api/users/${user_id}
'''
```

### Q: 如何调试HTTP请求？

A: 使用调试模式运行：

```bash
# 使用pytest运行获得详细输出
pytest test_runner.py -v -s
```

### Q: 默认授权不生效怎么办？

A: 检查以下几个方面：

1. **确认配置文件已正确加载**：
```bash
pytest-dsl tests/ --yaml-vars config.yaml -v
```

2. **检查环境变量是否设置**：
```bash
echo $API_TOKEN  # 确认环境变量已设置
```

3. **验证客户端配置**：
```python
# 在测试中打印客户端配置进行调试
[打印], 内容: "使用客户端: api_client"
[HTTP请求], 客户端: "api_client", 配置: '''
    method: GET
    url: /debug
'''
```

### Q: 如何为不同的API使用不同的认证方式？

A: 在YAML配置中定义多个客户端：

```yaml
http_clients:
  # 使用Bearer Token的API
  main_api:
    base_url: "https://api.example.com"
    auth:
      type: "token"
      token: "${API_TOKEN}"
  
  # 使用Basic认证的API
  admin_api:
    base_url: "https://admin.example.com"
    auth:
      type: "basic"
      username: "${ADMIN_USER}"
      password: "${ADMIN_PASS}"
  
  # 使用API Key的第三方API
  third_party_api:
    base_url: "https://partner.example.com"
    auth:
      type: "api_key"
      api_key: "${PARTNER_KEY}"
```

### Q: 如何动态切换认证信息？

A: 有几种方式：

1. **使用不同的配置文件**：
```bash
# 开发环境
pytest-dsl tests/ --yaml-vars dev_config.yaml

# 生产环境  
pytest-dsl tests/ --yaml-vars prod_config.yaml
```

2. **在测试中临时覆盖**：
```python
# 使用不同的token
[HTTP请求], 客户端: "api_client", 配置: '''
    method: GET
    url: /admin-only
    request:
        headers:
            Authorization: "Bearer ${ADMIN_TOKEN}"
'''
```

3. **禁用默认授权后手动设置**：
```python
[HTTP请求], 客户端: "api_client", 禁用授权: true, 配置: '''
    method: GET
    url: /public-endpoint
    request:
        headers:
            X-Custom-Auth: "${CUSTOM_TOKEN}"
'''
```

### Q: OAuth2认证失败怎么处理？

A: 检查OAuth2配置和网络连接：

1. **验证OAuth2配置**：
```yaml
http_clients:
  oauth_api:
    base_url: "https://api.example.com"
    auth:
      type: "oauth2"
      token_url: "https://auth.example.com/oauth/token"  # 确认URL正确
      client_id: "${OAUTH_CLIENT_ID}"
      client_secret: "${OAUTH_CLIENT_SECRET}"
      scope: "read write"  # 确认scope正确
```

2. **测试token端点**：
```python
# 手动测试OAuth2 token获取
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: https://auth.example.com/oauth/token
    request:
        data:
            grant_type: "client_credentials"
            client_id: "${OAUTH_CLIENT_ID}"
            client_secret: "${OAUTH_CLIENT_SECRET}"
    captures:
        test_token: ["jsonpath", "$.access_token"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.access_token", "exists"]
'''
```

## 下一步

现在您已经掌握了HTTP API测试的完整流程，可以继续学习：

- **[自定义关键字](./custom-keywords)** - 创建可复用的API测试组件
- **[数据驱动测试](./data-driven)** - 使用外部数据批量测试API
- **[环境配置管理](./configuration)** - 管理不同环境的API配置 