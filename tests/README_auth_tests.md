# pytest-dsl HTTP授权功能全面测试

本测试系统为pytest-dsl的HTTP授权功能提供全面的验证，确保各种授权方式都符合相关的RFC协议标准。

## 文件结构

```
tests/
├── README_auth_tests.md           # 本说明文档
├── test_auth_mock_server.py       # 授权测试Mock HTTP服务器
├── auth_config.yaml               # 授权测试配置文件
├── test_auth_functionality.dsl    # 授权功能测试DSL
└── test_auth_runner.py             # 测试运行器
```

## 测试覆盖范围

### 1. 支持的授权方式

#### Basic Authentication (RFC 7617)
- 有效凭据认证
- 无效凭据处理
- WWW-Authenticate质询头验证
- RFC 7617标准合规性

#### Bearer Token Authentication (RFC 6750)
- 有效Token认证
- 过期Token处理
- 无效Token处理
- RFC 6750标准合规性

#### API Key Authentication
- Header方式传递 (`X-API-Key`)
- Query参数方式传递 (`api_key`)
- Header+Query双重方式
- 无效API Key处理

#### OAuth2 Client Credentials (RFC 6749)
- Token获取流程 (`/oauth/token`)
- 受保护资源访问
- 自动Token管理
- RFC 6749标准合规性

#### 自定义Token认证
- 无Bearer前缀Token
- 自定义Header名称

#### 混合认证支持
- 多种认证方式共存
- 认证方式优先级处理

### 2. 功能特性测试

- **访问控制**: 受保护资源访问、未授权访问拒绝
- **禁用认证**: `disable_auth`功能验证
- **认证状态**: 认证状态清理和恢复
- **协议合规**: RFC标准严格验证

## Mock服务器特性

### 支持的端点

- `GET /health` - 健康检查
- `GET /public` - 公共端点（无需认证）
- `GET /auth/basic` - Basic认证测试
- `GET /auth/bearer` - Bearer Token认证测试
- `GET /auth/apikey` - API Key认证测试
- `GET /auth/digest` - Digest认证测试
- `GET /auth/oauth` - OAuth2认证测试
- `GET /auth/custom` - 自定义认证测试
- `GET /auth/mixed` - 混合认证测试
- `POST /oauth/token` - OAuth2 Token端点
- `ANY /api/*` - 受保护资源

### 预置测试数据

#### 用户账户 (Basic Auth)
```
用户名: admin,  密码: admin123,  角色: admin
用户名: user1,  密码: password1, 角色: user
用户名: test,   密码: test123,   角色: user
```

#### Bearer Tokens
```
valid_bearer_token_123  -> admin用户, 未过期
expired_token_456       -> user1用户, 已过期
test_token_789          -> test用户, 未过期
```

#### API Keys
```
test_api_key_123  -> admin用户, 权限: read,write
readonly_key_456  -> user1用户, 权限: read
dev_key_789       -> test用户,  权限: read,write,admin
```

#### OAuth2客户端
```
Client ID: test_client_id
Client Secret: test_client_secret
Scope: read write
Grant Types: client_credentials

Client ID: readonly_client
Client Secret: readonly_secret
Scope: read
Grant Types: client_credentials
```

## 快速开始

### 方式1: 使用测试运行器（推荐）

```bash
# 运行完整的授权功能测试
python tests/test_auth_runner.py

# 指定不同的服务器配置
python tests/test_auth_runner.py --host localhost --port 8889 --timeout 300

# 只生成测试总结报告
python tests/test_auth_runner.py --summary
```

### 方式2: 手动运行

```bash
# 1. 启动Mock服务器
python tests/test_auth_mock_server.py

# 2. 在另一个终端运行DSL测试
pytest-dsl tests/test_auth_functionality.dsl --yaml-vars tests/auth_config.yaml -v
```

## 配置说明

### HTTP客户端配置 (auth_config.yaml)

```yaml
http_clients:
  # 无认证客户端
  no_auth:
    base_url: "http://localhost:8889"
    
  # Basic认证客户端
  basic_auth_valid:
    base_url: "http://localhost:8889"
    auth_config:
      type: "basic"
      username: "admin"
      password: "admin123"
      
  # Bearer Token认证客户端
  bearer_auth_valid:
    base_url: "http://localhost:8889"
    auth_config:
      type: "token"
      token: "valid_bearer_token_123"
      scheme: "Bearer"
      
  # API Key认证客户端
  apikey_header_valid:
    base_url: "http://localhost:8889"
    auth_config:
      type: "api_key"
      api_key: "test_api_key_123"
      key_name: "X-API-Key"
      in_header: true
      
  # OAuth2客户端认证
  oauth2_client:
    base_url: "http://localhost:8889"
    auth_config:
      type: "oauth2"
      token_url: "http://localhost:8889/oauth/token"
      client_id: "test_client_id"
      client_secret: "test_client_secret"
      grant_type: "client_credentials"
```

## 测试示例

### Basic认证测试

```python
[HTTP请求], 客户端: "basic_auth_valid", 配置: '''
    method: GET
    url: /auth/basic
    captures:
        auth_user: ["jsonpath", "$.user"]
        auth_type: ["jsonpath", "$.auth_type"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.auth_type", "eq", "basic"]
        - ["jsonpath", "$.user", "eq", "admin"]
'''
```

### OAuth2认证测试

```python
# 获取OAuth2 Token
[HTTP请求], 客户端: "no_auth", 配置: '''
    method: POST
    url: /oauth/token
    request:
        headers:
            Content-Type: "application/x-www-form-urlencoded"
        data:
            grant_type: "client_credentials"
            client_id: "test_client_id"
            client_secret: "test_client_secret"
            scope: "read write"
    captures:
        oauth_access_token: ["jsonpath", "$.access_token"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.token_type", "eq", "Bearer"]
'''

# 使用Token访问受保护资源
[HTTP请求], 客户端: "no_auth", 配置: '''
    method: GET
    url: /auth/oauth
    request:
        headers:
            Authorization: "Bearer ${oauth_access_token}"
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.auth_type", "eq", "oauth2"]
'''
```

### 禁用认证功能测试

```python
[HTTP请求], 客户端: "basic_auth_valid", 配置: '''
    method: GET
    url: /auth/basic
    disable_auth: true
    asserts:
        - ["status", "eq", 401]
        - ["header", "WWW-Authenticate", "contains", "Basic realm"]
'''
```

## RFC协议标准验证

### RFC 7617 - Basic Authentication
- 验证Authorization头格式: `Basic <base64(username:password)>`
- 验证WWW-Authenticate质询头: `Basic realm="TestRealm"`
- 验证401状态码响应

### RFC 6750 - Bearer Token
- 验证Authorization头格式: `Bearer <token>`
- 验证WWW-Authenticate质询头: `Bearer realm="TestRealm"`
- 验证token过期处理

### RFC 6749 - OAuth2
- 验证Token端点: `POST /oauth/token`
- 验证client_credentials流程
- 验证错误响应格式

### RFC 7235 - HTTP Authentication
- 验证401状态码
- 验证WWW-Authenticate头
- 验证多重认证质询

## 预期输出

成功运行测试后，您将看到类似以下的输出：

```
✓ 服务器状态: healthy, 支持认证类型: ['basic', 'bearer', 'api_key', 'oauth2', 'digest', 'custom']
✓ 公共端点访问成功: Public endpoint - no authentication required
✓ Basic认证成功 - 用户: admin, 消息: Basic authentication successful
✓ Bearer Token认证成功 - 用户: admin, 认证类型: bearer
✓ API Key Header认证成功 - 用户: admin, 权限: ['read', 'write']
✓ OAuth2 Token获取成功 - Token: oauth_xxx, 类型: Bearer, 有效期: 3600秒
✓ OAuth2认证成功 - 客户端: test_client_id, 权限: ['read', 'write']
✓ 混合端点Basic认证: Basic authentication successful
✓ 受保护资源访问成功 - 用户: admin, 路径: /api/users
✓ 禁用认证功能正常工作 - 收到质询: Basic realm="TestRealm"
✓ RFC 7617 Basic Authentication合规 - 质询: Basic realm="TestRealm"
✓ RFC 6750 Bearer Token合规 - 质询: Bearer realm="TestRealm"
✓ RFC 6749 OAuth2合规 - 错误处理: invalid_client
✓ RFC 7235 HTTP Authentication合规 - 多重质询: Basic realm="TestRealm", Bearer realm="TestRealm"

🎉 pytest-dsl HTTP授权功能全面测试完成！
```

## 故障排除

### 常见问题

1. **Mock服务器启动失败**
   - 检查端口8889是否被占用
   - 确保防火墙允许本地连接

2. **测试文件找不到**
   - 确保在项目根目录运行测试
   - 检查文件路径是否正确

3. **依赖缺失**
   ```bash
   pip install requests
   ```

4. **测试超时**
   - 增加超时时间: `--timeout 600`
   - 检查网络连接

### 调试模式

启用详细日志输出：

```bash
python tests/test_auth_runner.py --verbose
```

## 扩展测试

您可以通过以下方式扩展测试：

1. **添加新的认证方式**：在Mock服务器中实现新的认证逻辑
2. **扩展测试场景**：在DSL文件中添加新的测试用例
3. **自定义配置**：修改auth_config.yaml添加新的客户端配置
4. **添加性能测试**：测试大量并发请求的认证性能

## 总结

这个授权功能测试系统提供了：

- **全面覆盖**：测试所有主流HTTP授权方式
- **标准合规**：严格按照RFC协议标准验证
- **自动化运行**：一键启动完整测试流程
- **详细报告**：提供详细的测试结果和总结
- **易于扩展**：支持添加新的认证方式和测试场景

通过这个测试系统，您可以确信pytest-dsl的HTTP授权功能完全符合业界标准，为API测试提供了可靠的授权支持。 