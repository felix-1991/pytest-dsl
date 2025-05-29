@name: "数据捕获和变量使用"
@description: "验证API响应数据捕获功能"

# 捕获响应数据
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/users/1
    captures:
        user_name: ["jsonpath", "$.name"]
        user_email: ["jsonpath", "$.email"]
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "获取用户信息"

# 使用捕获的变量
[打印], 内容: "用户名: ${user_name}"
[打印], 内容: "邮箱: ${user_email}"

# 在后续请求中使用
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts
    request:
        params:
            userId: 1
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "根据用户ID获取文章"
