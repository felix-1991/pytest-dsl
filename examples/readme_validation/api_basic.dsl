@name: "API测试入门"
@description: "学习基本的API测试方法"

# 简单的GET请求
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.title", "contains", "sunt"]
''', 步骤名称: "获取文章详情"
