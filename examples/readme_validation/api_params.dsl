@name: "带参数的API请求"
@description: "验证带查询参数的GET请求"

# 带查询参数的GET请求
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts
    request:
        params:
            userId: 1
            _limit: 5
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$", "length", "eq", 5]
''', 步骤名称: "获取用户文章列表"
