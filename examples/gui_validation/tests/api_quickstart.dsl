@name: "接口测试核心链路：查询用户、登录并校验账户"
@description: "使用一个内置 HTTP请求 关键字完成请求、捕获、断言和变量传递"
@tags: ["api", "http", "quickstart"]

[HTTP请求], 客户端: "local_api", 配置: '''
    method: GET
    url: /api/users/${api_demo.user_id}
    captures:
        user_id: ["jsonpath", "$.data.id"]
        username: ["jsonpath", "$.data.username"]
        user_role: ["jsonpath", "$.data.role"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.code", "eq", 0]
        - ["jsonpath", "$.data.role", "eq", "tester"]
''', 步骤名称: "查询接口测试用户"

[HTTP请求], 客户端: "local_api", 配置: '''
    method: POST
    url: /api/sessions
    request:
        headers:
            Content-Type: application/json
        json:
            username: "${username}"
            password: "${api_demo.password}"
    captures:
        access_token: ["jsonpath", "$.data.access_token"]
        login_user_id: ["jsonpath", "$.data.user_id"]
    asserts:
        - ["status", "eq", 201]
        - ["jsonpath", "$.code", "eq", 0]
        - ["jsonpath", "$.data.user_id", "eq", ${user_id}]
''', 步骤名称: "登录并捕获访问令牌"

[HTTP请求], 客户端: "local_api", 配置: '''
    method: GET
    url: /api/users/${login_user_id}/profile
    request:
        headers:
            Authorization: "Bearer ${access_token}"
    captures:
        account_active: ["jsonpath", "$.data.active"]
        account_plan: ["jsonpath", "$.data.plan"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.data.active", "eq", true]
        - ["jsonpath", "$.data.plan", "eq", "team"]
''', 步骤名称: "携带令牌查询账户状态"

[断言], 条件: "${account_active} == True", 消息: "账户应该处于启用状态"
[打印], 内容: "接口测试核心链路验证完成：用户=${username}，角色=${user_role}，套餐=${account_plan}"
