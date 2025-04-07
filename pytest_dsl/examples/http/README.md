# HTTP请求关键字使用指南

本目录包含HTTP请求关键字的示例和使用指南。HTTP请求关键字是pytest-dsl框架的强大功能，用于进行API接口测试。

## 关键字语法

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

## 参数说明

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| 客户端 | 字符串 | 否 | YAML变量文件中定义的HTTP客户端配置名称，不提供则使用默认客户端 |
| 配置 | YAML字符串 | 是 | 包含请求、捕获和断言的YAML配置 |
| 会话 | 字符串 | 否 | 会话名称，用于在多个请求间保持会话状态 |
| 保存响应 | 字符串 | 否 | 将完整响应保存到指定变量名中，便于后续使用 |
| 重试次数 | 整数 | 否 | 请求失败时的重试次数，默认为0 |
| 重试间隔 | 整数 | 否 | 重试间隔时间（秒），默认为1 |
| 模板 | 字符串 | 否 | 使用YAML变量文件中定义的请求模板 |

## 配置详细说明

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
    session: true
  
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
```

## 使用YAML变量文件

运行测试时使用`--yaml-vars`参数指定YAML变量文件:

```bash
pytest-dsl --yaml-vars vars.yaml test_file.auto
```

## 示例

本目录包含以下示例:

1. `http_example.auto` - HTTP请求关键字的基本用法
2. `http_advanced.auto` - 高级用法，包括会话管理和复杂断言
3. `http_with_yaml.auto` - 使用YAML变量和模板的示例
4. `vars.yaml` - 客户端配置和模板的YAML变量文件 