@name: "远程会话管理功能测试"
@description: "测试远程关键字模式下的HTTP会话管理功能"
@tags: ["remote", "session", "http", "example"]
@author: "Felix"
@date: 2024-12-19

# 导入远程关键字服务器
@remote: "http://localhost:8270/" as remote_server

[打印],内容: "=== 远程会话管理功能测试开始 ==="

# 测试1: 基本会话功能
[打印],内容: "--- 测试1: 基本会话功能 ---"

# 本地会话测试
[打印],内容: "本地会话测试:"

# 设置本地会话Cookie
[HTTP请求],客户端: "default",会话: "local_test_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies/set/local_session_id/local_123
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "本地设置会话Cookie"

# 验证本地会话Cookie
local_session_result = [HTTP请求],客户端: "default",会话: "local_test_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies
    captures:
        local_session_id: ["jsonpath", "$.cookies.local_session_id"]
    asserts:
        - ["jsonpath", "$.cookies.local_session_id", "eq", "local_123"]
''',步骤名称: "本地验证会话Cookie"

[打印],内容: "本地会话验证结果: ${local_session_result}"

# 远程会话测试
[打印],内容: "远程会话测试:"

# 设置远程会话Cookie
remote_server|[HTTP请求],客户端: "default",会话: "remote_test_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies/set/remote_session_id/remote_456
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "远程设置会话Cookie"

# 验证远程会话Cookie
remote_session_result = remote_server|[HTTP请求],客户端: "default",会话: "remote_test_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies
    captures:
        remote_session_id: ["jsonpath", "$.cookies.remote_session_id"]
    asserts:
        - ["jsonpath", "$.cookies.remote_session_id", "eq", "remote_456"]
''',步骤名称: "远程验证会话Cookie"

[打印],内容: "远程会话验证结果: ${remote_session_result}"

# 测试2: 多个会话并行管理
[打印],内容: "--- 测试2: 多个会话并行管理 ---"

# 远程创建第一个会话
remote_server|[HTTP请求],客户端: "default",会话: "session_1",配置: '''
    method: GET
    url: https://httpbin.org/cookies/set
    request:
        params:
            user_id: user_001
            role: admin
            session_name: session_1
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "远程创建会话1"

# 远程创建第二个会话
remote_server|[HTTP请求],客户端: "default",会话: "session_2",配置: '''
    method: GET
    url: https://httpbin.org/cookies/set
    request:
        params:
            user_id: user_002
            role: user
            session_name: session_2
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "远程创建会话2"

# 验证第一个会话
session_1_result = remote_server|[HTTP请求],客户端: "default",会话: "session_1",配置: '''
    method: GET
    url: https://httpbin.org/cookies
    captures:
        session_1_user_id: ["jsonpath", "$.cookies.user_id"]
        session_1_role: ["jsonpath", "$.cookies.role"]
        session_1_name: ["jsonpath", "$.cookies.session_name"]
    asserts:
        - ["jsonpath", "$.cookies.user_id", "eq", "user_001"]
        - ["jsonpath", "$.cookies.role", "eq", "admin"]
        - ["jsonpath", "$.cookies.session_name", "eq", "session_1"]
''',步骤名称: "远程验证会话1"

[打印],内容: "会话1验证结果: ${session_1_result}"

# 验证第二个会话
session_2_result = remote_server|[HTTP请求],客户端: "default",会话: "session_2",配置: '''
    method: GET
    url: https://httpbin.org/cookies
    captures:
        session_2_user_id: ["jsonpath", "$.cookies.user_id"]
        session_2_role: ["jsonpath", "$.cookies.role"]
        session_2_name: ["jsonpath", "$.cookies.session_name"]
    asserts:
        - ["jsonpath", "$.cookies.user_id", "eq", "user_002"]
        - ["jsonpath", "$.cookies.role", "eq", "user"]
        - ["jsonpath", "$.cookies.session_name", "eq", "session_2"]
''',步骤名称: "远程验证会话2"

[打印],内容: "会话2验证结果: ${session_2_result}"

# 测试3: 会话持续性测试
[打印],内容: "--- 测试3: 会话持续性测试 ---"

# 远程设置持续会话
remote_server|[HTTP请求],客户端: "default",会话: "persistent_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies/set
    request:
        params:
            login_time: "2024-12-19 10:00:00"
            token: "abc123def456"
            expires: "2024-12-20 10:00:00"
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "远程设置持续会话"

# 第一次访问
first_access = remote_server|[HTTP请求],客户端: "default",会话: "persistent_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies
    captures:
        first_login_time: ["jsonpath", "$.cookies.login_time"]
        first_token: ["jsonpath", "$.cookies.token"]
    asserts:
        - ["jsonpath", "$.cookies.token", "eq", "abc123def456"]
''',步骤名称: "远程第一次访问"

[打印],内容: "第一次访问结果: ${first_access}"

# 等待一秒
[等待],秒数: 1

# 第二次访问（验证会话持续）
second_access = remote_server|[HTTP请求],客户端: "default",会话: "persistent_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies
    captures:
        second_login_time: ["jsonpath", "$.cookies.login_time"]
        second_token: ["jsonpath", "$.cookies.token"]
    asserts:
        - ["jsonpath", "$.cookies.token", "eq", "abc123def456"]
        - ["jsonpath", "$.cookies.login_time", "eq", "2024-12-19 10:00:00"]
''',步骤名称: "远程第二次访问"

[打印],内容: "第二次访问结果: ${second_access}"

# 测试4: 会话数据更新
[打印],内容: "--- 测试4: 会话数据更新 ---"

# 远程初始化会话
remote_server|[HTTP请求],客户端: "default",会话: "update_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies/set
    request:
        params:
            counter: "1"
            last_action: "login"
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "远程初始化更新会话"

# 第一次更新
remote_server|[HTTP请求],客户端: "default",会话: "update_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies/set
    request:
        params:
            counter: "2"
            last_action: "view_profile"
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "远程第一次更新会话"

# 验证更新后的会话
update_result = remote_server|[HTTP请求],客户端: "default",会话: "update_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies
    captures:
        updated_counter: ["jsonpath", "$.cookies.counter"]
        updated_action: ["jsonpath", "$.cookies.last_action"]
    asserts:
        - ["jsonpath", "$.cookies.counter", "eq", "2"]
        - ["jsonpath", "$.cookies.last_action", "eq", "view_profile"]
''',步骤名称: "远程验证更新后会话"

[打印],内容: "会话更新结果: ${update_result}"

# 测试5: 复杂会话场景
[打印],内容: "--- 测试5: 复杂会话场景 ---"

# 模拟用户登录流程
login_result = remote_server|[HTTP请求],客户端: "default",会话: "user_session",配置: '''
    method: POST
    url: https://httpbin.org/post
    request:
        json:
            username: "testuser"
            password: "testpass"
        headers:
            Content-Type: "application/json"
    captures:
        login_response: ["jsonpath", "$.json"]
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "远程模拟用户登录"

[打印],内容: "登录结果: ${login_result}"

# 设置登录后的会话状态
remote_server|[HTTP请求],客户端: "default",会话: "user_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies/set
    request:
        params:
            authenticated: "true"
            username: "testuser"
            login_timestamp: "1703001600"
            permissions: "read,write"
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "远程设置登录会话状态"

# 模拟业务操作
business_result = remote_server|[HTTP请求],客户端: "default",会话: "user_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies
    captures:
        auth_status: ["jsonpath", "$.cookies.authenticated"]
        current_user: ["jsonpath", "$.cookies.username"]
        user_permissions: ["jsonpath", "$.cookies.permissions"]
    asserts:
        - ["jsonpath", "$.cookies.authenticated", "eq", "true"]
        - ["jsonpath", "$.cookies.username", "eq", "testuser"]
''',步骤名称: "远程执行业务操作"

[打印],内容: "业务操作结果: ${business_result}"

# 测试6: 会话隔离验证
[打印],内容: "--- 测试6: 会话隔离验证 ---"

# 创建两个独立的会话，验证它们互不影响
remote_server|[HTTP请求],客户端: "default",会话: "isolated_session_a",配置: '''
    method: GET
    url: https://httpbin.org/cookies/set/session_type/session_a
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "远程创建隔离会话A"

remote_server|[HTTP请求],客户端: "default",会话: "isolated_session_b",配置: '''
    method: GET
    url: https://httpbin.org/cookies/set/session_type/session_b
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "远程创建隔离会话B"

# 验证会话A
session_a_check = remote_server|[HTTP请求],客户端: "default",会话: "isolated_session_a",配置: '''
    method: GET
    url: https://httpbin.org/cookies
    captures:
        session_a_type: ["jsonpath", "$.cookies.session_type"]
    asserts:
        - ["jsonpath", "$.cookies.session_type", "eq", "session_a"]
''',步骤名称: "远程验证隔离会话A"

# 验证会话B
session_b_check = remote_server|[HTTP请求],客户端: "default",会话: "isolated_session_b",配置: '''
    method: GET
    url: https://httpbin.org/cookies
    captures:
        session_b_type: ["jsonpath", "$.cookies.session_type"]
    asserts:
        - ["jsonpath", "$.cookies.session_type", "eq", "session_b"]
''',步骤名称: "远程验证隔离会话B"

[打印],内容: "会话A验证结果: ${session_a_check}"
[打印],内容: "会话B验证结果: ${session_b_check}"

[打印],内容: "=== 远程会话管理功能测试完成 ==="
[打印],内容: "✅ 所有会话管理功能测试通过！"

teardown do
    [打印],内容: "远程会话管理测试清理完成"
end
