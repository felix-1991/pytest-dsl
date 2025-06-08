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

### 使用配置

```bash
pytest-dsl tests/ --yaml-vars config.yaml
```

```python
# 使用配置中的客户端
[HTTP请求], 客户端: "api_server", 配置: '''
    method: GET
    url: /users
'''
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

### 认证流程

```python
@name: "完整认证流程"

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

## 下一步

现在您已经掌握了HTTP API测试的完整流程，可以继续学习：

- **[自定义关键字](./custom-keywords)** - 创建可复用的API测试组件
- **[数据驱动测试](./data-driven)** - 使用外部数据批量测试API
- **[环境配置管理](./configuration)** - 管理不同环境的API配置 