@name: "重试执行关键字测试"
@description: "测试重试执行关键字的功能"

# 测试1: 基本重试功能（无成功条件）
[打印], 内容: "=== 测试1: 基本重试功能 ==="
测试结果1 = [重试执行],
    关键字名称: "打印",
    关键字参数: {
        "内容": "这是测试打印"
    },
    重试次数: 2,
    重试间隔: 1

[打印], 内容: "重试结果1 - 成功: ${测试结果1.success}"

# 测试2: 带成功条件的重试
[打印], 内容: "=== 测试2: 带成功条件的重试 ==="
# 先执行一个HTTP请求获取结果
响应 = [HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
    asserts:
        - ["status", "eq", 200]
'''

测试结果2 = [重试执行],
    关键字名称: "HTTP请求",
    关键字参数: {
        "客户端": "default",
        "配置": '''
            method: GET
            url: https://jsonplaceholder.typicode.com/posts/1
            asserts:
                - ["status", "eq", 200]
        '''
    },
    重试次数: 2,
    重试间隔: 1,
    成功条件: "${result.status_code} == 200",
    打印字段: ["result.status_code"]

if ${测试结果2.success} do
    [打印], 内容: "✓ 重试成功，状态码: ${测试结果2.result.status_code}"
else
    [打印], 内容: "✗ 重试失败"
end

[打印], 内容: "=== 测试完成 ==="

