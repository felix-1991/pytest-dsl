@name: 简单授权测试
@description: 测试基本HTTP请求功能

# 测试服务器健康状态
[HTTP请求], 客户端: "no_auth", 配置: '''
    method: GET
    url: http://localhost:8889/health
    captures:
        server_status: ["jsonpath", "$.status"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.status", "eq", "healthy"]
'''

[打印], 内容: "✓ 服务器状态: ${server_status}"

# Basic认证测试
[HTTP请求], 客户端: "basic_auth_valid", 配置: '''
    method: GET
    url: http://localhost:8889/auth/basic
    captures:
        auth_user: ["jsonpath", "$.user"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.user", "eq", "admin"]
'''

[打印], 内容: "✓ Basic认证成功 - 用户: ${auth_user}"

# Bearer Token认证测试
[HTTP请求], 客户端: "bearer_auth_valid", 配置: '''
    method: GET
    url: http://localhost:8889/auth/bearer
    captures:
        bearer_user: ["jsonpath", "$.user"]
        bearer_type: ["jsonpath", "$.auth_type"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.user", "eq", "admin"]
        - ["jsonpath", "$.auth_type", "eq", "bearer"]
'''

[打印], 内容: "✓ Bearer Token认证成功 - 用户: ${bearer_user}"

# API Key认证测试 - Header方式
[HTTP请求], 客户端: "apikey_header_valid", 配置: '''
    method: GET
    url: http://localhost:8889/auth/apikey
    captures:
        apikey_user: ["jsonpath", "$.user"]
        apikey_type: ["jsonpath", "$.auth_type"]
        apikey_scope: ["jsonpath", "$.scope"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.user", "eq", "admin"]
        - ["jsonpath", "$.auth_type", "eq", "api_key"]
'''

[打印], 内容: "✓ API Key认证(Header)成功 - 用户: ${apikey_user}, 权限: ${apikey_scope}"

# API Key认证测试 - Query方式
[HTTP请求], 客户端: "apikey_query_valid", 配置: '''
    method: GET
    url: http://localhost:8889/auth/apikey
    captures:
        apikey_query_user: ["jsonpath", "$.user"]
        apikey_query_type: ["jsonpath", "$.auth_type"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.user", "eq", "admin"]
        - ["jsonpath", "$.auth_type", "eq", "api_key"]
'''

[打印], 内容: "✓ API Key认证(Query)成功 - 用户: ${apikey_query_user}"

# OAuth2认证测试
[HTTP请求], 客户端: "oauth2_client", 配置: '''
    method: GET
    url: http://localhost:8889/auth/oauth
    captures:
        oauth_client_id: ["jsonpath", "$.client_id"]
        oauth_type: ["jsonpath", "$.auth_type"]
        oauth_scope: ["jsonpath", "$.scope"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.client_id", "eq", "test_client_id"]
        - ["jsonpath", "$.auth_type", "eq", "oauth2"]
'''

[打印], 内容: "✓ OAuth2认证成功 - 客户端: ${oauth_client_id}, 权限: ${oauth_scope}" 