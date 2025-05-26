@name: "多服务器协作测试"
@description: "测试多个远程关键字服务器之间的协作功能"
@tags: ["remote", "multi-server", "collaboration", "example"]
@author: "Felix"
@date: 2024-12-19

# 导入多个远程关键字服务器
# 注意：需要在不同端口启动多个服务器实例
@remote: "http://localhost:8270/" as server1
@remote: "http://localhost:8271/" as server2

[打印],内容: "=== 多服务器协作测试开始 ==="
[打印],内容: "注意：此测试需要在端口8270和8271上启动两个远程服务器"

# 清理环境
[清除所有全局变量]
server1|[清除所有全局变量]
server2|[清除所有全局变量]

# 测试1: 基本多服务器通信
[打印],内容: "--- 测试1: 基本多服务器通信 ---"

# 在不同服务器上执行基本操作
[打印],内容: "本地执行: Hello from local!"
server1|[打印],内容: "服务器1执行: Hello from server1!"
server2|[打印],内容: "服务器2执行: Hello from server2!"

# 在不同服务器上生成随机数据
local_random = [生成随机字符串],长度: 6,类型: "mixed"
server1_random = server1|[生成随机字符串],长度: 6,类型: "mixed"
server2_random = server2|[生成随机字符串],长度: 6,类型: "mixed"

[打印],内容: "本地随机字符串: ${local_random}"
[打印],内容: "服务器1随机字符串: ${server1_random}"
[打印],内容: "服务器2随机字符串: ${server2_random}"

# 验证随机字符串都不相同
[断言],条件: "'${local_random}' != '${server1_random}'",消息: "本地和服务器1的随机字符串应该不同"
[断言],条件: "'${server1_random}' != '${server2_random}'",消息: "服务器1和服务器2的随机字符串应该不同"

# 测试2: 多服务器全局变量隔离
[打印],内容: "--- 测试2: 多服务器全局变量隔离 ---"

# 在不同服务器上设置相同名称的全局变量
[设置全局变量],变量名: "server_id",值: "local"
server1|[设置全局变量],变量名: "server_id",值: "server1"
server2|[设置全局变量],变量名: "server_id",值: "server2"

# 设置不同的配置
[设置全局变量],变量名: "config",值: "local_config"
server1|[设置全局变量],变量名: "config",值: "server1_config"
server2|[设置全局变量],变量名: "config",值: "server2_config"

# 验证变量隔离
local_server_id = [获取全局变量],变量名: "server_id"
server1_server_id = server1|[获取全局变量],变量名: "server_id"
server2_server_id = server2|[获取全局变量],变量名: "server_id"

local_config = [获取全局变量],变量名: "config"
server1_config = server1|[获取全局变量],变量名: "config"
server2_config = server2|[获取全局变量],变量名: "config"

[打印],内容: "本地服务器ID: ${local_server_id}, 配置: ${local_config}"
[打印],内容: "服务器1 ID: ${server1_server_id}, 配置: ${server1_config}"
[打印],内容: "服务器2 ID: ${server2_server_id}, 配置: ${server2_config}"

# 验证隔离性
[断言],条件: "'${local_server_id}' == 'local'",消息: "本地服务器ID验证"
[断言],条件: "'${server1_server_id}' == 'server1'",消息: "服务器1 ID验证"
[断言],条件: "'${server2_server_id}' == 'server2'",消息: "服务器2 ID验证"

# 测试3: 多服务器HTTP请求协作
[打印],内容: "--- 测试3: 多服务器HTTP请求协作 ---"

# 在不同服务器上执行HTTP请求，获取不同的数据
server1_post = server1|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
    captures:
        server1_post_id: ["jsonpath", "$.id"]
        server1_post_title: ["jsonpath", "$.title"]
        server1_user_id: ["jsonpath", "$.userId"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.id", "eq", 1]
''',步骤名称: "服务器1获取文章1"

server2_post = server2|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/2
    captures:
        server2_post_id: ["jsonpath", "$.id"]
        server2_post_title: ["jsonpath", "$.title"]
        server2_user_id: ["jsonpath", "$.userId"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.id", "eq", 2]
''',步骤名称: "服务器2获取文章2"

[打印],内容: "服务器1获取的文章: ${server1_post}"
[打印],内容: "服务器2获取的文章: ${server2_post}"

# 测试4: 多服务器会话管理
[打印],内容: "--- 测试4: 多服务器会话管理 ---"

# 在不同服务器上创建独立的会话
server1|[HTTP请求],客户端: "default",会话: "server1_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies/set
    request:
        params:
            server: "server1"
            session_id: "s1_session_123"
            timestamp: "2024-12-19T10:00:00"
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "服务器1创建会话"

server2|[HTTP请求],客户端: "default",会话: "server2_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies/set
    request:
        params:
            server: "server2"
            session_id: "s2_session_456"
            timestamp: "2024-12-19T10:00:00"
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "服务器2创建会话"

# 验证会话独立性
server1_session_check = server1|[HTTP请求],客户端: "default",会话: "server1_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies
    captures:
        s1_server: ["jsonpath", "$.cookies.server"]
        s1_session_id: ["jsonpath", "$.cookies.session_id"]
    asserts:
        - ["jsonpath", "$.cookies.server", "eq", "server1"]
        - ["jsonpath", "$.cookies.session_id", "eq", "s1_session_123"]
''',步骤名称: "服务器1会话验证"

server2_session_check = server2|[HTTP请求],客户端: "default",会话: "server2_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies
    captures:
        s2_server: ["jsonpath", "$.cookies.server"]
        s2_session_id: ["jsonpath", "$.cookies.session_id"]
    asserts:
        - ["jsonpath", "$.cookies.server", "eq", "server2"]
        - ["jsonpath", "$.cookies.session_id", "eq", "s2_session_456"]
''',步骤名称: "服务器2会话验证"

[打印],内容: "服务器1会话验证: ${server1_session_check}"
[打印],内容: "服务器2会话验证: ${server2_session_check}"

# 测试5: 多服务器数据聚合
[打印],内容: "--- 测试5: 多服务器数据聚合 ---"

# 从不同服务器获取数据并聚合
server1_users = server1|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/users/1
    captures:
        s1_user_name: ["jsonpath", "$.name"]
        s1_user_email: ["jsonpath", "$.email"]
        s1_user_city: ["jsonpath", "$.address.city"]
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "服务器1获取用户1信息"

server2_users = server2|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/users/2
    captures:
        s2_user_name: ["jsonpath", "$.name"]
        s2_user_email: ["jsonpath", "$.email"]
        s2_user_city: ["jsonpath", "$.address.city"]
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "服务器2获取用户2信息"

[打印],内容: "服务器1用户信息: ${server1_users}"
[打印],内容: "服务器2用户信息: ${server2_users}"

# 聚合数据到本地
aggregated_data = [字符串操作],操作: "concat",字符串: "用户聚合: ",参数1: "服务器1用户, ",参数2: "服务器2用户"
[打印],内容: "${aggregated_data}"

# 测试6: 多服务器负载分担
[打印],内容: "--- 测试6: 多服务器负载分担 ---"

# 模拟负载分担：奇数请求发送到服务器1，偶数请求发送到服务器2
for i in range(1, 7) do
    if ${i} % 2 == 1 do
        # 奇数请求发送到服务器1
        result = server1|[HTTP请求],客户端: "default",配置: '''
            method: GET
            url: https://jsonplaceholder.typicode.com/posts/${i}
            captures:
                post_id_${i}: ["jsonpath", "$.id"]
            asserts:
                - ["status", "eq", 200]
        ''',步骤名称: "服务器1处理请求${i}"
        [打印],内容: "请求${i}由服务器1处理: ${result}"
    else
        # 偶数请求发送到服务器2
        result = server2|[HTTP请求],客户端: "default",配置: '''
            method: GET
            url: https://jsonplaceholder.typicode.com/posts/${i}
            captures:
                post_id_${i}: ["jsonpath", "$.id"]
            asserts:
                - ["status", "eq", 200]
        ''',步骤名称: "服务器2处理请求${i}"
        [打印],内容: "请求${i}由服务器2处理: ${result}"
    end
end

# 测试7: 多服务器错误处理
[打印],内容: "--- 测试7: 多服务器错误处理 ---"

# 测试服务器1的错误处理
try
    server1|[HTTP请求],客户端: "default",配置: '''
        method: GET
        url: https://jsonplaceholder.typicode.com/posts/99999
        asserts:
            - ["status", "eq", 200]  # 这会失败
    ''',步骤名称: "服务器1错误测试"
catch error
    [打印],内容: "服务器1错误处理正常: ${error}"
end

# 测试服务器2的错误处理
try
    server2|[断言],条件: "1 == 2",消息: "服务器2故意失败的断言"
catch error
    [打印],内容: "服务器2错误处理正常: ${error}"
end

# 测试8: 多服务器性能对比
[打印],内容: "--- 测试8: 多服务器性能对比 ---"

# 记录开始时间
start_time = [获取当前时间],格式: "%Y-%m-%d %H:%M:%S"

# 在两个服务器上执行相同的操作
server1_perf = server1|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts
    captures:
        s1_posts_count: ["jsonpath", "$", "length"]
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "服务器1性能测试"

server2_perf = server2|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts
    captures:
        s2_posts_count: ["jsonpath", "$", "length"]
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "服务器2性能测试"

end_time = [获取当前时间],格式: "%Y-%m-%d %H:%M:%S"

[打印],内容: "性能测试 - 开始时间: ${start_time}, 结束时间: ${end_time}"
[打印],内容: "服务器1结果: ${server1_perf}"
[打印],内容: "服务器2结果: ${server2_perf}"

[打印],内容: "=== 多服务器协作测试完成 ==="
[打印],内容: "✅ 所有多服务器协作功能测试通过！"

@teardown do
    [打印],内容: "执行多服务器测试清理..."
    
    # 清理所有服务器的全局变量
    try
        [清除所有全局变量]
        server1|[清除所有全局变量]
        server2|[清除所有全局变量]
    catch error
        [打印],内容: "清理过程中出现错误，但测试已完成"
    end
    
    [打印],内容: "多服务器协作测试清理完成"
end
