@name: "用户登录功能测试"
@description: "测试用户登录的各种场景"
@tags: ["auth", "login"]
@import: "auth.resource"

# 测试管理员登录
admin_token = [用户登录], 用户名: ${test_users.admin.username}, 密码: ${test_users.admin.password}
[断言], 条件: "${admin_token} != ''", 消息: "管理员登录失败"

# 验证登录状态（模拟）
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/users/1
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.name", "exists"]
''', 步骤名称: "验证登录状态"

# 测试登出
[用户登出]

teardown do
    [打印], 内容: "登录测试完成"
end
