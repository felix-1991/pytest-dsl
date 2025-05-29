@name: "断言重试机制示例"
@description: "演示HTTP请求的断言重试功能"

# 模拟异步任务状态检查
# 注意：这里使用一个总是返回200状态的API来演示重试机制
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.id", "eq", 1]
''', 断言重试次数: 3, 断言重试间隔: 1, 步骤名称: "测试断言重试机制"

[打印], 内容: "断言重试测试完成"
