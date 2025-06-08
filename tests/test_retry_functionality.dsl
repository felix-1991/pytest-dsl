@name: "重试功能综合测试"
@description: "测试HTTP请求重试功能的各种配置和场景"

# 重置服务器状态
[HTTP请求], 客户端: "mock_server", 配置: '''
    method: GET
    url: /api/reset
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "重置服务器状态"

# 测试1: 基础重试功能 - 失败后成功
[HTTP请求], 客户端: "mock_server", 配置: '''
    method: GET
    url: /api/retry/fail-then-success
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.success", "eq", true]
    retry_assertions:
        count: 3
        interval: 0.5
        all: true
''', 步骤名称: "测试基础重试功能"

# 重置状态
[HTTP请求], 客户端: "mock_server", 配置: '''
    method: GET
    url: /api/reset
''', 步骤名称: "重置状态1"

# 测试2: 重试时间间隔验证
[HTTP请求], 客户端: "mock_server", 配置: '''
    method: GET
    url: /api/retry/fail-then-success
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.success", "eq", true]
        - ["jsonpath", "$.data.attempts", "gte", 3]
    retry_assertions:
        count: 3
        interval: 1.0
        all: true
''', 步骤名称: "测试重试时间间隔"

# 重置状态
[HTTP请求], 客户端: "mock_server", 配置: '''
    method: GET
    url: /api/reset
''', 步骤名称: "重置状态2"

# 测试3: 特定断言重试配置
[HTTP请求], 客户端: "mock_server", 配置: '''
    method: GET
    url: /api/retry/fail-then-success
    asserts:
        - ["status", "eq", 200]           # 断言0 - 会重试
        - ["jsonpath", "$.success", "eq", true]  # 断言1 - 不重试
    retry_assertions:
        count: 3
        interval: 0.5
        indices: [0]  # 只重试第一个断言
''', 步骤名称: "测试特定断言重试"

# 重置状态
[HTTP请求], 客户端: "mock_server", 配置: '''
    method: GET
    url: /api/reset
''', 步骤名称: "重置状态3"

# 测试4: 无重试配置的边界情况
[测试用例], 配置: '''
    expect_failure: true
    steps:
        - [HTTP请求], 客户端: "mock_server", 配置: '''
            method: GET
            url: /api/retry/fail-then-success
            asserts:
                - ["status", "eq", 200]  # 第一次会失败
        '''
''', 步骤名称: "测试无重试配置"

# 重置状态
[HTTP请求], 客户端: "mock_server", 配置: '''
    method: GET
    url: /api/reset
''', 步骤名称: "重置状态4"

# 测试5: 整数和字符串索引混合使用
[HTTP请求], 客户端: "mock_server", 配置: '''
    method: GET
    url: /api/retry/fail-then-success
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.success", "eq", true]
    retry_assertions:
        count: 3
        interval: 0.5
        specific:
            0:  # 整数键
                count: 5
                interval: 2
            "1":  # 字符串键
                count: 2
                interval: 1
''', 步骤名称: "测试混合索引配置"

[打印], 内容: "✅ 重试功能综合测试完成！" 