@name: pytest-dsl HTTP授权功能全面测试
@description: 测试所有内置授权方式的功能和协议标准合规性
@tags: [HTTP, 授权, 认证, RFC标准, API测试]
@author: pytest-dsl
@date: 2024-12-30

# =====================================================================
# pytest-dsl HTTP授权功能全面测试
# 
# 本测试套件验证以下授权方式：
# 1. Basic Authentication (RFC 7617)
# 2. Bearer Token Authentication (RFC 6750) 
# 3. API Key Authentication (Header/Query/Both)
# 4. OAuth2 Client Credentials (RFC 6749)
# 5. 自定义Token认证
# 6. 混合认证支持
# 7. 禁用认证功能
# 8. 协议标准合规性验证
# =====================================================================

## 1. 健康检查和基础功能测试

# 测试服务器健康状态
[HTTP请求], 客户端: "no_auth", 配置: '''
    method: GET
    url: ${test_endpoints.health}
    captures:
        server_status: ["jsonpath", "$.status"]
        server_name: ["jsonpath", "$.server"]
        supported_auth_types: ["jsonpath", "$.supported_auth"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.status", "eq", "healthy"]
        - ["jsonpath", "$.server", "eq", "auth-mock-server"]
        - ["jsonpath", "$.supported_auth", "contains", "basic"]
        - ["jsonpath", "$.supported_auth", "contains", "bearer"]
        - ["jsonpath", "$.supported_auth", "contains", "api_key"]
        - ["jsonpath", "$.supported_auth", "contains", "oauth2"]
'''

[打印], 内容: "✓ 服务器状态: ${server_status}, 支持认证类型: ${supported_auth_types}"

# 测试公共端点（无需认证）
[HTTP请求], 客户端: "no_auth", 配置: '''
    method: GET
    url: ${test_endpoints.public}
    captures:
        public_message: ["jsonpath", "$.message"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.message", "contains", "Public endpoint"]
'''

[打印], 内容: "✓ 公共端点访问成功: ${public_message}"

## 2. Basic Authentication 测试 (RFC 7617)

# 有效凭据测试
[HTTP请求], 客户端: "basic_auth_valid", 配置: '''
    method: GET
    url: ${test_endpoints.auth_basic}
    captures:
        auth_user: ["jsonpath", "$.user"]
        auth_type: ["jsonpath", "$.auth_type"]
        auth_message: ["jsonpath", "$.message"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.message", "eq", "${expected_responses.auth_success.basic.message}"]
        - ["jsonpath", "$.auth_type", "eq", "basic"]
        - ["jsonpath", "$.user", "eq", "${test_users.admin.username}"]
'''

[打印], 内容: "✓ Basic认证成功 - 用户: ${auth_user}, 消息: ${auth_message}"

# 无效凭据测试
[HTTP请求], 客户端: "basic_auth_invalid", 配置: '''
    method: GET
    url: ${test_endpoints.auth_basic}
    captures:
        error_message: ["jsonpath", "$.message"]
        www_authenticate: ["header", "WWW-Authenticate"]
    asserts:
        - ["status", "eq", 401]
        - ["jsonpath", "$.error", "eq", "Unauthorized"]
        - ["header", "WWW-Authenticate", "eq", "${rfc_compliance.basic_auth.www_authenticate_header}"]
'''

[打印], 内容: "✓ Basic认证失败测试通过 - WWW-Authenticate: ${www_authenticate}"

# 无认证头测试
[HTTP请求], 客户端: "no_auth", 配置: '''
    method: GET
    url: ${test_endpoints.auth_basic}
    captures:
        challenge_header: ["header", "WWW-Authenticate"]
    asserts:
        - ["status", "eq", 401]
        - ["header", "WWW-Authenticate", "contains", "Basic realm"]
'''

[打印], 内容: "✓ Basic认证质询头验证通过: ${challenge_header}"

## 3. Bearer Token Authentication 测试 (RFC 6750)

# 有效Token测试
[HTTP请求], 客户端: "bearer_auth_valid", 配置: '''
    method: GET
    url: ${test_endpoints.auth_bearer}
    captures:
        token_user: ["jsonpath", "$.user"]
        token_auth_type: ["jsonpath", "$.auth_type"]
        token_message: ["jsonpath", "$.message"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.message", "eq", "${expected_responses.auth_success.bearer.message}"]
        - ["jsonpath", "$.auth_type", "eq", "bearer"]
        - ["jsonpath", "$.user", "eq", "admin"]
'''

[打印], 内容: "✓ Bearer Token认证成功 - 用户: ${token_user}, 认证类型: ${token_auth_type}"

# 过期Token测试
[HTTP请求], 客户端: "bearer_auth_expired", 配置: '''
    method: GET
    url: ${test_endpoints.auth_bearer}
    captures:
        bearer_error: ["jsonpath", "$.error"]
        bearer_www_auth: ["header", "WWW-Authenticate"]
    asserts:
        - ["status", "eq", 401]
        - ["jsonpath", "$.error", "eq", "Unauthorized"]
        - ["header", "WWW-Authenticate", "eq", "${rfc_compliance.bearer_token.www_authenticate_header}"]
'''

[打印], 内容: "✓ 过期Bearer Token处理正确 - WWW-Authenticate: ${bearer_www_auth}"

# 无效Token测试
[HTTP请求], 客户端: "bearer_auth_invalid", 配置: '''
    method: GET
    url: ${test_endpoints.auth_bearer}
    captures:
        invalid_token_error: ["jsonpath", "$.error"]
    asserts:
        - ["status", "eq", 401]
        - ["jsonpath", "$.error", "eq", "Unauthorized"]
        - ["header", "WWW-Authenticate", "contains", "Bearer realm"]
'''

[打印], 内容: "✓ 无效Bearer Token处理正确 - 错误: ${invalid_token_error}"

## 4. API Key Authentication 测试

# Header方式API Key测试
[HTTP请求], 客户端: "apikey_header_valid", 配置: '''
    method: GET
    url: ${test_endpoints.auth_apikey}
    captures:
        apikey_user: ["jsonpath", "$.user"]
        apikey_scope: ["jsonpath", "$.scope"]
        apikey_message: ["jsonpath", "$.message"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.message", "eq", "${expected_responses.auth_success.api_key.message}"]
        - ["jsonpath", "$.auth_type", "eq", "api_key"]
        - ["jsonpath", "$.user", "eq", "admin"]
        - ["jsonpath", "$.scope", "contains", "read"]
        - ["jsonpath", "$.scope", "contains", "write"]
'''

[打印], 内容: "✓ API Key Header认证成功 - 用户: ${apikey_user}, 权限: ${apikey_scope}"

# Query参数方式API Key测试
[HTTP请求], 客户端: "apikey_query_valid", 配置: '''
    method: GET
    url: ${test_endpoints.auth_apikey}
    captures:
        query_apikey_user: ["jsonpath", "$.user"]
        query_apikey_scope: ["jsonpath", "$.scope"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.auth_type", "eq", "api_key"]
        - ["jsonpath", "$.user", "eq", "test"]
        - ["jsonpath", "$.scope", "contains", "admin"]
'''

[打印], 内容: "✓ API Key Query认证成功 - 用户: ${query_apikey_user}, 权限: ${query_apikey_scope}"

# Header+Query双重API Key测试
[HTTP请求], 客户端: "apikey_both_valid", 配置: '''
    method: GET
    url: ${test_endpoints.auth_apikey}
    captures:
        both_apikey_user: ["jsonpath", "$.user"]
        both_apikey_scope: ["jsonpath", "$.scope"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.auth_type", "eq", "api_key"]
        - ["jsonpath", "$.user", "eq", "user1"]
        - ["jsonpath", "$.scope", "contains", "read"]
'''

[打印], 内容: "✓ API Key Both认证成功 - 用户: ${both_apikey_user}, 权限: ${both_apikey_scope}"

# 无效API Key测试
[HTTP请求], 客户端: "apikey_invalid", 配置: '''
    method: GET
    url: ${test_endpoints.auth_apikey}
    captures:
        invalid_apikey_error: ["jsonpath", "$.error"]
        invalid_apikey_message: ["jsonpath", "$.message"]
    asserts:
        - ["status", "eq", 401]
        - ["jsonpath", "$.error", "eq", "Unauthorized"]
        - ["jsonpath", "$.message", "contains", "Valid API key required"]
'''

[打印], 内容: "✓ 无效API Key处理正确 - 错误: ${invalid_apikey_error}"

## 5. OAuth2 Client Credentials 测试 (RFC 6749)


# 获取OAuth2 Token
[HTTP请求], 客户端: "no_auth", 配置: '''
    method: POST
    url: ${test_endpoints.oauth_token}
    request:
        headers:
            Content-Type: "application/x-www-form-urlencoded"
        data:
            grant_type: "client_credentials"
            client_id: "${oauth_clients.test_client.client_id}"
            client_secret: "${oauth_clients.test_client.client_secret}"
            scope: "read write"
    captures:
        oauth_access_token: ["jsonpath", "$.access_token"]
        oauth_token_type: ["jsonpath", "$.token_type"]
        oauth_expires_in: ["jsonpath", "$.expires_in"]
        oauth_scope: ["jsonpath", "$.scope"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.token_type", "eq", "Bearer"]
        - ["jsonpath", "$.access_token", "exists"]
        - ["jsonpath", "$.expires_in", "gt", 0]
        - ["jsonpath", "$.scope", "contains", "read"]
        - ["jsonpath", "$.scope", "contains", "write"]
'''

[打印], 内容: "✓ OAuth2 Token获取成功 - Token: ${oauth_access_token}, 类型: ${oauth_token_type}, 有效期: ${oauth_expires_in}秒"

# 使用OAuth2 Token访问受保护资源
[HTTP请求], 客户端: "no_auth", 配置: '''
    method: GET
    url: ${test_endpoints.auth_oauth}
    request:
        headers:
            Authorization: "Bearer ${oauth_access_token}"
    captures:
        oauth_client_id: ["jsonpath", "$.client_id"]
        oauth_message: ["jsonpath", "$.message"]
        oauth_scope_received: ["jsonpath", "$.scope"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.message", "eq", "${expected_responses.auth_success.oauth2.message}"]
        - ["jsonpath", "$.auth_type", "eq", "oauth2"]
        - ["jsonpath", "$.client_id", "eq", "${oauth_clients.test_client.client_id}"]
'''

[打印], 内容: "✓ OAuth2认证成功 - 客户端: ${oauth_client_id}, 权限: ${oauth_scope_received}"

# OAuth2自动获取和使用Token（通过配置的OAuth2客户端）
[HTTP请求], 客户端: "oauth2_client", 配置: '''
    method: GET
    url: ${test_endpoints.auth_oauth}
    captures:
        auto_oauth_client: ["jsonpath", "$.client_id"]
        auto_oauth_message: ["jsonpath", "$.message"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.auth_type", "eq", "oauth2"]
        - ["jsonpath", "$.client_id", "eq", "${oauth_clients.test_client.client_id}"]
'''

[打印], 内容: "✓ OAuth2自动认证成功 - 客户端: ${auto_oauth_client}"

## 6. 自定义Token认证测试


# 自定义Token格式测试
[HTTP请求], 客户端: "custom_token_auth", 配置: '''
    method: GET
    url: ${test_endpoints.auth_bearer}
    captures:
        custom_token_user: ["jsonpath", "$.user"]
        custom_token_type: ["jsonpath", "$.auth_type"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.auth_type", "eq", "bearer"]
        - ["jsonpath", "$.user", "eq", "test"]
'''

[打印], 内容: "✓ 自定义Token认证成功 - 用户: ${custom_token_user}, 类型: ${custom_token_type}"

## 7. 混合认证测试


# 使用Basic认证访问混合端点
[HTTP请求], 客户端: "basic_auth_valid", 配置: '''
    method: GET
    url: ${test_endpoints.auth_mixed}
    captures:
        mixed_basic_user: ["jsonpath", "$.user"]
        mixed_basic_type: ["jsonpath", "$.auth_type"]
        mixed_basic_message: ["jsonpath", "$.message"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.auth_type", "eq", "basic"]
        - ["jsonpath", "$.user", "eq", "${test_users.admin.username}"]
        - ["jsonpath", "$.message", "contains", "Basic authentication successful"]
'''

[打印], 内容: "✓ 混合端点Basic认证: ${mixed_basic_message}"

# 使用Bearer Token访问混合端点
[HTTP请求], 客户端: "bearer_auth_valid", 配置: '''
    method: GET
    url: ${test_endpoints.auth_mixed}
    captures:
        mixed_bearer_user: ["jsonpath", "$.user"]
        mixed_bearer_type: ["jsonpath", "$.auth_type"]
        mixed_bearer_message: ["jsonpath", "$.message"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.auth_type", "eq", "bearer"]
        - ["jsonpath", "$.user", "eq", "admin"]
        - ["jsonpath", "$.message", "contains", "Bearer authentication successful"]
'''

[打印], 内容: "✓ 混合端点Bearer认证: ${mixed_bearer_message}"

# 使用API Key访问混合端点
[HTTP请求], 客户端: "apikey_header_valid", 配置: '''
    method: GET
    url: ${test_endpoints.auth_mixed}
    captures:
        mixed_apikey_user: ["jsonpath", "$.user"]
        mixed_apikey_type: ["jsonpath", "$.auth_type"]
        mixed_apikey_message: ["jsonpath", "$.message"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.auth_type", "eq", "api_key"]
        - ["jsonpath", "$.user", "eq", "admin"]
        - ["jsonpath", "$.message", "contains", "Api_key authentication successful"]
'''

[打印], 内容: "✓ 混合端点API Key认证: ${mixed_apikey_message}"

## 8. 受保护资源访问测试


# 有认证访问受保护资源
[HTTP请求], 客户端: "basic_auth_valid", 配置: '''
    method: GET
    url: ${test_endpoints.protected_resource}
    captures:
        protected_user: ["jsonpath", "$.user"]
        protected_path: ["jsonpath", "$.path"]
        protected_data: ["jsonpath", "$.data.message"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.user", "eq", "${test_users.admin.username}"]
        - ["jsonpath", "$.auth_type", "eq", "basic"]
        - ["jsonpath", "$.path", "eq", "${test_endpoints.protected_resource}"]
        - ["jsonpath", "$.data.message", "contains", "Protected resource accessed"]
'''

[打印], 内容: "✓ 受保护资源访问成功 - 用户: ${protected_user}, 路径: ${protected_path}"

# 无认证访问受保护资源（应失败）
[HTTP请求], 客户端: "no_auth", 配置: '''
    method: GET
    url: ${test_endpoints.protected_resource}
    captures:
        protected_error: ["jsonpath", "$.error"]
        protected_challenge: ["header", "WWW-Authenticate"]
    asserts:
        - ["status", "eq", 401]
        - ["jsonpath", "$.error", "eq", "Unauthorized"]
        - ["header", "WWW-Authenticate", "contains", "Basic realm"]
        - ["header", "WWW-Authenticate", "contains", "Bearer realm"]
'''

[打印], 内容: "✓ 未授权访问正确拒绝 - 质询头: ${protected_challenge}"

## 9. 禁用认证功能测试


# 使用disable_auth访问需要认证的端点
[HTTP请求], 客户端: "basic_auth_valid", 配置: '''
    method: GET
    url: ${test_endpoints.auth_basic}
    disable_auth: true
    captures:
        disabled_auth_error: ["jsonpath", "$.error"]
        disabled_auth_challenge: ["header", "WWW-Authenticate"]
    asserts:
        - ["status", "eq", 401]
        - ["jsonpath", "$.error", "eq", "Unauthorized"]
        - ["header", "WWW-Authenticate", "contains", "Basic realm"]
'''

[打印], 内容: "✓ 禁用认证功能正常工作 - 收到质询: ${disabled_auth_challenge}"

# 验证禁用认证后再次启用
[HTTP请求], 客户端: "basic_auth_valid", 配置: '''
    method: GET
    url: ${test_endpoints.auth_basic}
    disable_auth: false
    captures:
        reenabled_auth_user: ["jsonpath", "$.user"]
        reenabled_auth_message: ["jsonpath", "$.message"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.user", "eq", "${test_users.admin.username}"]
        - ["jsonpath", "$.auth_type", "eq", "basic"]
'''

[打印], 内容: "✓ 重新启用认证功能正常 - 用户: ${reenabled_auth_user}"

## 10. 协议标准合规性验证


# RFC 7617 - Basic Authentication 合规性
[HTTP请求], 客户端: "no_auth", 配置: '''
    method: GET
    url: ${test_endpoints.auth_basic}
    captures:
        rfc7617_challenge: ["header", "WWW-Authenticate"]
        rfc7617_status: ["status"]
    asserts:
        - ["status", "eq", ${rfc_compliance.http_auth.challenge_status_code}]
        - ["header", "WWW-Authenticate", "startswith", "${rfc_compliance.basic_auth.authorization_scheme}"]
        - ["header", "WWW-Authenticate", "contains", "realm="]
'''

[打印], 内容: "✓ RFC 7617 Basic Authentication合规 - 质询: ${rfc7617_challenge}"

# RFC 6750 - Bearer Token 合规性
[HTTP请求], 客户端: "no_auth", 配置: '''
    method: GET
    url: ${test_endpoints.auth_bearer}
    captures:
        rfc6750_challenge: ["header", "WWW-Authenticate"]
        rfc6750_status: ["status"]
    asserts:
        - ["status", "eq", ${rfc_compliance.http_auth.challenge_status_code}]
        - ["header", "WWW-Authenticate", "startswith", "${rfc_compliance.bearer_token.authorization_scheme}"]
        - ["header", "WWW-Authenticate", "contains", "realm="]
'''

[打印], 内容: "✓ RFC 6750 Bearer Token合规 - 质询: ${rfc6750_challenge}"

# RFC 6749 - OAuth2 合规性
[HTTP请求], 客户端: "no_auth", 配置: '''
    method: POST
    url: ${rfc_compliance.oauth2.token_endpoint}
    request:
        headers:
            Content-Type: "application/x-www-form-urlencoded"
        data:
            grant_type: "invalid_grant"
            client_id: "invalid_client"
    captures:
        rfc6749_error: ["jsonpath", "$.error"]
        rfc6749_status: ["status"]
    asserts:
        - ["status", "eq", 401]
        - ["jsonpath", "$.error", "eq", "${expected_responses.auth_errors.invalid_client.error}"]
'''

[打印], 内容: "✓ RFC 6749 OAuth2合规 - 错误处理: ${rfc6749_error}"

# RFC 7235 - HTTP Authentication 合规性
[HTTP请求], 客户端: "no_auth", 配置: '''
    method: GET
    url: ${test_endpoints.auth_mixed}
    captures:
        rfc7235_challenge: ["header", "${rfc_compliance.http_auth.challenge_header}"]
        rfc7235_status: ["status"]
    asserts:
        - ["status", "eq", ${rfc_compliance.http_auth.challenge_status_code}]
        - ["header", "WWW-Authenticate", "contains", "Basic realm"]
        - ["header", "WWW-Authenticate", "contains", "Bearer realm"]
'''

[打印], 内容: "✓ RFC 7235 HTTP Authentication合规 - 多重质询: ${rfc7235_challenge}"


[打印], 内容: """
========================================
🎉 pytest-dsl HTTP授权功能全面测试完成！
========================================

测试覆盖范围:
✓ Basic Authentication (RFC 7617)
✓ Bearer Token Authentication (RFC 6750)
✓ API Key Authentication (Header/Query/Both)
✓ OAuth2 Client Credentials (RFC 6749)
✓ 自定义Token认证
✓ 混合认证支持
✓ 受保护资源访问控制
✓ 禁用认证功能 (disable_auth)
✓ RFC协议标准合规性验证

所有认证方式均按照相关RFC标准实现并通过验证！
""" 