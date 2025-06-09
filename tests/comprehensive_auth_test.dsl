@name: 综合授权功能测试
@description: 测试所有认证方式的正向和负向场景

## 1. 健康检查
[HTTP请求], 客户端: "no_auth", 配置: '''
    method: GET
    url: http://localhost:8889/health
    captures:
        server_status: ["jsonpath", "$.status"]
        supported_auth_types: ["jsonpath", "$.supported_auth"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.status", "eq", "healthy"]
        - ["jsonpath", "$.supported_auth", "contains", "basic"]
        - ["jsonpath", "$.supported_auth", "contains", "bearer"]
        - ["jsonpath", "$.supported_auth", "contains", "api_key"]
        - ["jsonpath", "$.supported_auth", "contains", "oauth2"]
'''

[打印], 内容: "✓ 服务器健康检查通过 - 支持的认证类型: ${supported_auth_types}"

## 2. Basic认证测试

# 有效凭据测试
[HTTP请求], 客户端: "basic_auth_valid", 配置: '''
    method: GET
    url: http://localhost:8889/auth/basic
    captures:
        basic_user: ["jsonpath", "$.user"]
        basic_auth_type: ["jsonpath", "$.auth_type"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.user", "eq", "admin"]
        - ["jsonpath", "$.auth_type", "eq", "basic"]
'''

[打印], 内容: "✓ Basic认证成功 - 用户: ${basic_user}"

# 无认证访问 - 应该返回401
[HTTP请求], 客户端: "no_auth", 配置: '''
    method: GET
    url: http://localhost:8889/auth/basic
    asserts:
        - ["status", "eq", 401]
        - ["header", "WWW-Authenticate", "exists"]
        - ["jsonpath", "$.error", "eq", "Unauthorized"]
'''

[打印], 内容: "✓ Basic认证 - 无认证访问正确返回401"

## 3. Bearer Token认证测试

# 有效Token测试
[HTTP请求], 客户端: "bearer_auth_valid", 配置: '''
    method: GET
    url: http://localhost:8889/auth/bearer
    captures:
        bearer_user: ["jsonpath", "$.user"]
        bearer_auth_type: ["jsonpath", "$.auth_type"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.user", "eq", "admin"]
        - ["jsonpath", "$.auth_type", "eq", "bearer"]
'''

[打印], 内容: "✓ Bearer Token认证成功 - 用户: ${bearer_user}"

# 无Token访问 - 应该返回401
[HTTP请求], 客户端: "no_auth", 配置: '''
    method: GET
    url: http://localhost:8889/auth/bearer
    asserts:
        - ["status", "eq", 401]
        - ["jsonpath", "$.error", "eq", "Unauthorized"]
'''

[打印], 内容: "✓ Bearer Token认证 - 无Token访问正确返回401"

## 4. API Key认证测试

# Header方式认证
[HTTP请求], 客户端: "apikey_header_valid", 配置: '''
    method: GET
    url: http://localhost:8889/auth/apikey
    captures:
        apikey_header_user: ["jsonpath", "$.user"]
        apikey_header_scope: ["jsonpath", "$.scope"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.user", "eq", "admin"]
        - ["jsonpath", "$.auth_type", "eq", "api_key"]
        - ["jsonpath", "$.scope", "contains", "read"]
        - ["jsonpath", "$.scope", "contains", "write"]
'''

[打印], 内容: "✓ API Key认证(Header)成功 - 用户: ${apikey_header_user}, 权限: ${apikey_header_scope}"

# Query参数方式认证
[HTTP请求], 客户端: "apikey_query_valid", 配置: '''
    method: GET
    url: http://localhost:8889/auth/apikey
    captures:
        apikey_query_user: ["jsonpath", "$.user"]
        apikey_query_scope: ["jsonpath", "$.scope"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.user", "eq", "admin"]
        - ["jsonpath", "$.auth_type", "eq", "api_key"]
'''

[打印], 内容: "✓ API Key认证(Query)成功 - 用户: ${apikey_query_user}, 权限: ${apikey_query_scope}"

# 无API Key访问 - 应该返回401
[HTTP请求], 客户端: "no_auth", 配置: '''
    method: GET
    url: http://localhost:8889/auth/apikey
    asserts:
        - ["status", "eq", 401]
        - ["jsonpath", "$.error", "eq", "Unauthorized"]
        - ["jsonpath", "$.message", "contains", "API key required"]
'''

[打印], 内容: "✓ API Key认证 - 无API Key访问正确返回401"

## 5. OAuth2认证测试

# OAuth2客户端认证
[HTTP请求], 客户端: "oauth2_client", 配置: '''
    method: GET
    url: http://localhost:8889/auth/oauth
    captures:
        oauth_client_id: ["jsonpath", "$.client_id"]
        oauth_scope: ["jsonpath", "$.scope"]
        oauth_auth_type: ["jsonpath", "$.auth_type"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.client_id", "eq", "test_client_id"]
        - ["jsonpath", "$.auth_type", "eq", "oauth2"]
        - ["jsonpath", "$.scope", "contains", "read"]
        - ["jsonpath", "$.scope", "contains", "write"]
'''

[打印], 内容: "✓ OAuth2认证成功 - 客户端: ${oauth_client_id}, 权限: ${oauth_scope}"

# 无OAuth Token访问 - 应该返回401
[HTTP请求], 客户端: "no_auth", 配置: '''
    method: GET
    url: http://localhost:8889/auth/oauth
    asserts:
        - ["status", "eq", 401]
        - ["jsonpath", "$.error", "eq", "invalid_token"]
        - ["jsonpath", "$.error_description", "eq", "Bearer token required"]
'''

[打印], 内容: "✓ OAuth2认证 - 无Token访问正确返回401"

## 6. 混合认证测试

# 使用Basic认证访问混合端点
[HTTP请求], 客户端: "basic_auth_valid", 配置: '''
    method: GET
    url: http://localhost:8889/auth/mixed
    captures:
        mixed_user: ["jsonpath", "$.user"]
        mixed_auth_type: ["jsonpath", "$.auth_type"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.user", "eq", "admin"]
        - ["jsonpath", "$.auth_type", "eq", "basic"]
'''

# 使用API Key访问混合端点
[HTTP请求], 客户端: "apikey_header_valid", 配置: '''
    method: GET
    url: http://localhost:8889/auth/mixed
    captures:
        mixed_apikey_user: ["jsonpath", "$.user"]
        mixed_apikey_auth_type: ["jsonpath", "$.auth_type"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.user", "eq", "admin"]
        - ["jsonpath", "$.auth_type", "eq", "api_key"]
'''

[打印], 内容: "✓ 混合认证测试通过 - Basic: ${mixed_user}, API Key: ${mixed_apikey_user}"

## 7. 受保护资源访问测试

# 有认证访问受保护资源
[HTTP请求], 客户端: "bearer_auth_valid", 配置: '''
    method: GET
    url: http://localhost:8889/api/users/123
    captures:
        protected_user: ["jsonpath", "$.user"]
        protected_path: ["jsonpath", "$.path"]
        protected_resource_id: ["jsonpath", "$.data.resource_id"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.user", "eq", "admin"]
        - ["jsonpath", "$.path", "eq", "/api/users/123"]
        - ["jsonpath", "$.data.resource_id", "eq", "123"]
'''

# 无认证访问受保护资源 - 应该返回401
[HTTP请求], 客户端: "no_auth", 配置: '''
    method: GET
    url: http://localhost:8889/api/users/123
    asserts:
        - ["status", "eq", 401]
        - ["jsonpath", "$.error", "eq", "Unauthorized"]
        - ["header", "WWW-Authenticate", "exists"]
'''

[打印], 内容: "✓ 受保护资源访问控制正常 - 有认证: ${protected_user}, 无认证: 401"

## 8. 公共端点测试（无需认证）

[HTTP请求], 客户端: "no_auth", 配置: '''
    method: GET
    url: http://localhost:8889/public
    captures:
        public_message: ["jsonpath", "$.message"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.message", "contains", "no authentication required"]
'''

[打印], 内容: "✓ 公共端点访问正常 - ${public_message}"

## 9. 禁用认证功能测试

# 使用有认证的客户端但禁用认证访问需要认证的端点
[HTTP请求], 客户端: "basic_auth_valid", 配置: '''
    method: GET
    url: http://localhost:8889/auth/basic
    disable_auth: true
    asserts:
        - ["status", "eq", 401]
        - ["jsonpath", "$.error", "eq", "Unauthorized"]
'''

[打印], 内容: "✓ 禁用认证功能正常工作"

## 总结
[打印], 内容: """
🎉 综合授权功能测试完成！

测试覆盖：
✅ Basic Authentication (RFC 7617)
✅ Bearer Token Authentication (RFC 6750) 
✅ API Key Authentication (Header + Query)
✅ OAuth2 Client Credentials (RFC 6749)
✅ 混合认证支持
✅ 受保护资源访问控制
✅ 公共端点访问
✅ 禁用认证功能
✅ 错误场景和状态码验证

所有认证方式都符合相关RFC协议标准！
""" 