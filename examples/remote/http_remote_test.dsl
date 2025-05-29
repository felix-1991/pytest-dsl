@name: "远程HTTP请求功能测试"
@description: "测试远程关键字模式下的HTTP请求功能，包括capture和会话保存"
@tags: ["remote", "http", "example"]
@author: "Felix"
@date: 2024-12-19

# 导入远程关键字服务器
@remote: "http://localhost:8270/" as remote_server

[打印],内容: "=== 远程HTTP请求功能测试开始 ==="

# 测试1: 基本的远程HTTP请求
[打印],内容: "--- 测试1: 基本远程HTTP请求 ---"

# 本地HTTP请求
[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.id", "eq", 1]
''',步骤名称: "本地获取文章详情"

[打印],内容: "本地HTTP请求执行成功"

# 远程HTTP请求
remote_server|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/2
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.id", "eq", 2]
''',步骤名称: "远程获取文章详情"

[打印],内容: "远程HTTP请求执行成功"

# 测试2: 远程HTTP请求with变量捕获
[打印],内容: "--- 测试2: 远程HTTP请求变量捕获 ---"

# 本地HTTP请求with捕获
local_result = [HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/3
    captures:
        local_post_id: ["jsonpath", "$.id"]
        local_post_title: ["jsonpath", "$.title"]
        local_user_id: ["jsonpath", "$.userId"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.id", "eq", 3]
''',步骤名称: "本地捕获文章信息"

[打印],内容: "本地HTTP请求捕获结果: ${local_result}"

# 远程HTTP请求with捕获
remote_result = remote_server|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/4
    captures:
        remote_post_id: ["jsonpath", "$.id"]
        remote_post_title: ["jsonpath", "$.title"]
        remote_user_id: ["jsonpath", "$.userId"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.id", "eq", 4]
''',步骤名称: "远程捕获文章信息"

[打印],内容: "远程HTTP请求捕获结果: ${remote_result}"

# 测试3: 远程HTTP请求with保存响应
[打印],内容: "--- 测试3: 远程HTTP请求保存响应 ---"

# 本地HTTP请求保存响应
local_response_result = [HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts
    request:
        params:
            userId: 1
    captures:
        local_posts_count: ["jsonpath", "$", "length"]
        local_first_post_id: ["jsonpath", "$[0].id"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$", "type", "array"]
''',保存响应: "local_posts_response",步骤名称: "本地获取用户文章列表"

[打印],内容: "本地HTTP请求保存响应结果: ${local_response_result}"

# 远程HTTP请求保存响应
remote_response_result = remote_server|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts
    request:
        params:
            userId: 2
    captures:
        remote_posts_count: ["jsonpath", "$", "length"]
        remote_first_post_id: ["jsonpath", "$[0].id"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$", "type", "array"]
''',保存响应: "remote_posts_response",步骤名称: "远程获取用户文章列表"

[打印],内容: "远程HTTP请求保存响应结果: ${remote_response_result}"

# 测试4: 远程HTTP请求with会话管理
[打印],内容: "--- 测试4: 远程HTTP请求会话管理 ---"

# 本地会话测试
[HTTP请求],客户端: "default",会话: "local_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies/set
    request:
        params:
            local_session_id: local_test_123
            local_user: local_user
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "本地设置会话Cookie"

[HTTP请求],客户端: "default",会话: "local_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies
    captures:
        local_session_id: ["jsonpath", "$.cookies.local_session_id"]
        local_user: ["jsonpath", "$.cookies.local_user"]
    asserts:
        - ["jsonpath", "$.cookies.local_session_id", "eq", "local_test_123"]
        - ["jsonpath", "$.cookies.local_user", "eq", "local_user"]
''',步骤名称: "本地验证会话Cookie"

[打印],内容: "本地会话管理测试完成"

# 远程会话测试
remote_server|[HTTP请求],客户端: "default",会话: "remote_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies/set
    request:
        params:
            remote_session_id: remote_test_456
            remote_user: remote_user
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "远程设置会话Cookie"

remote_session_result = remote_server|[HTTP请求],客户端: "default",会话: "remote_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies
    captures:
        remote_session_id: ["jsonpath", "$.cookies.remote_session_id"]
        remote_user: ["jsonpath", "$.cookies.remote_user"]
    asserts:
        - ["jsonpath", "$.cookies.remote_session_id", "eq", "remote_test_456"]
        - ["jsonpath", "$.cookies.remote_user", "eq", "remote_user"]
''',步骤名称: "远程验证会话Cookie"

[打印],内容: "远程会话管理结果: ${remote_session_result}"
[打印],内容: "远程会话管理测试完成"

# 测试5: 复杂HTTP请求测试
[打印],内容: "--- 测试5: 复杂HTTP请求测试 ---"

# 远程POST请求
remote_post_result = remote_server|[HTTP请求],客户端: "default",配置: '''
    method: POST
    url: https://jsonplaceholder.typicode.com/posts
    request:
        json:
            title: "Remote Test Post"
            body: "This is a test post from remote server"
            userId: 1
    captures:
        created_post_id: ["jsonpath", "$.id"]
        created_post_title: ["jsonpath", "$.title"]
    asserts:
        - ["status", "eq", 201]
        - ["jsonpath", "$.title", "eq", "Remote Test Post"]
        - ["jsonpath", "$.userId", "eq", 1]
''',步骤名称: "远程创建文章"

[打印],内容: "远程POST请求结果: ${remote_post_result}"


[打印],内容: "=== 远程HTTP请求功能测试完成 ==="
[打印],内容: "✅ 所有HTTP功能测试通过！"

teardown do
    [打印],内容: "远程HTTP请求测试清理完成"
end
