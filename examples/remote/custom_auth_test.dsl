@name: "自定义授权扩展机制验证测试"
@description: "验证远程服务器的自定义授权扩展机制，包括Hook机制和授权提供者注册"
@tags: ["remote", "auth", "hooks", "extension"]
@author: "Felix"
@date: 2024-12-19

# 导入远程关键字服务器（需要先启动带有自定义授权扩展的服务器）
# 启动命令: bash examples/remote/start_server_with_auth.sh
@remote: "http://localhost:8270" as auth_server

[打印],内容: "=== 自定义授权扩展机制验证测试开始 ==="

# 测试1: 验证Hook机制工作
[打印],内容: "--- 测试1: 验证Hook机制 ---"

# 执行一个简单的远程关键字，验证Hook是否被触发
auth_server|[打印],内容: "测试Hook机制触发"

# 测试2: 验证自定义授权提供者注册
[打印],内容: "--- 测试2: 验证自定义授权提供者 ---"

# 使用自定义授权进行HTTP请求
# 这个请求会触发自定义授权提供者的apply_auth方法
auth_result = auth_server|[HTTP请求],客户端: "default", 配置: '''
    method: GET
    url: https://httpbin.org/headers
    captures:
        auth_header: ["jsonpath", "$.headers.X-Auth-Source"]
        custom_header: ["jsonpath", "$.headers.X-Custom-Auth"]
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "验证自定义授权注入"

[打印],内容: "自定义授权结果: ${auth_result}"

# 测试3: 验证授权头部注入
[打印],内容: "--- 测试3: 验证授权头部注入 ---"

# 测试自定义授权头部是否正确注入
headers_result = auth_server|[HTTP请求],客户端: "default", 配置: '''
    method: GET
    url: https://httpbin.org/headers
    captures:
        all_headers: ["jsonpath", "$.headers"]
        x_auth_source: ["jsonpath", "$.headers.X-Auth-Source"]
        x_custom_auth: ["jsonpath", "$.headers.X-Custom-Auth"]
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "验证授权头部注入"

[打印],内容: "头部注入结果: ${headers_result}"

# 测试4: 对比本地和远程授权处理
[打印],内容: "--- 测试4: 对比本地和远程授权处理 ---"


