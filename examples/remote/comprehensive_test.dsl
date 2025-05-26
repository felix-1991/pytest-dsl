@name: "远程关键字综合功能测试"
@description: "综合测试远程关键字的所有功能，包括HTTP请求、变量捕获、会话管理、全局变量等"
@tags: ["remote", "comprehensive", "integration", "example"]
@author: "Felix"
@date: 2024-12-19

# 导入远程关键字服务器
@remote: "http://localhost:8270/" as remote_server

[打印],内容: "=== 远程关键字综合功能测试开始 ==="

# 清理环境
[清除所有全局变量]
remote_server|[清除所有全局变量]

# 测试场景: 模拟完整的API测试流程
[打印],内容: "--- 综合测试场景: 完整API测试流程 ---"

# 步骤1: 设置测试环境配置
[打印],内容: "步骤1: 设置测试环境配置"

# 本地环境配置
[设置全局变量],变量名: "local_env",值: "development"
[设置全局变量],变量名: "local_api_base",值: "https://jsonplaceholder.typicode.com"
[设置全局变量],变量名: "local_timeout",值: 30

# 远程环境配置
remote_server|[设置全局变量],变量名: "remote_env",值: "production"
remote_server|[设置全局变量],变量名: "remote_api_base",值: "https://jsonplaceholder.typicode.com"
remote_server|[设置全局变量],变量名: "remote_timeout",值: 60

# 获取配置用于后续测试
local_api_base = [获取全局变量],变量名: "local_api_base"
remote_api_base = remote_server|[获取全局变量],变量名: "remote_api_base"

[打印],内容: "本地API基础URL: ${local_api_base}"
[打印],内容: "远程API基础URL: ${remote_api_base}"

# 步骤2: 用户认证流程
[打印],内容: "步骤2: 用户认证流程"

# 本地用户认证
local_auth_result = [HTTP请求],客户端: "default",会话: "local_user_session",配置: '''
    method: POST
    url: ${local_api_base}/posts
    request:
        json:
            title: "Local Auth Test"
            body: "Testing local authentication"
            userId: 1
    captures:
        local_auth_post_id: ["jsonpath", "$.id"]
        local_auth_title: ["jsonpath", "$.title"]
    asserts:
        - ["status", "eq", 201]
''',步骤名称: "本地用户认证"

[打印],内容: "本地认证结果: ${local_auth_result}"

# 远程用户认证
remote_auth_result = remote_server|[HTTP请求],客户端: "default",会话: "remote_user_session",配置: '''
    method: POST
    url: ${remote_api_base}/posts
    request:
        json:
            title: "Remote Auth Test"
            body: "Testing remote authentication"
            userId: 2
    captures:
        remote_auth_post_id: ["jsonpath", "$.id"]
        remote_auth_title: ["jsonpath", "$.title"]
    asserts:
        - ["status", "eq", 201]
''',步骤名称: "远程用户认证"

[打印],内容: "远程认证结果: ${remote_auth_result}"

# 保存认证信息到全局变量
[设置全局变量],变量名: "local_user_id",值: 1
remote_server|[设置全局变量],变量名: "remote_user_id",值: 2

# 步骤3: 数据查询和处理
[打印],内容: "步骤3: 数据查询和处理"

# 本地数据查询
local_user_id = [获取全局变量],变量名: "local_user_id"
local_query_result = [HTTP请求],客户端: "default",会话: "local_user_session",配置: '''
    method: GET
    url: ${local_api_base}/posts
    request:
        params:
            userId: ${local_user_id}
    captures:
        local_posts: ["jsonpath", "$"]
        local_posts_count: ["jsonpath", "$", "length"]
        local_first_post_title: ["jsonpath", "$[0].title"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$", "type", "array"]
''',步骤名称: "本地数据查询"

[打印],内容: "本地查询结果: ${local_query_result}"

# 远程数据查询
remote_user_id = remote_server|[获取全局变量],变量名: "remote_user_id"
remote_query_result = remote_server|[HTTP请求],客户端: "default",会话: "remote_user_session",配置: '''
    method: GET
    url: ${remote_api_base}/posts
    request:
        params:
            userId: ${remote_user_id}
    captures:
        remote_posts: ["jsonpath", "$"]
        remote_posts_count: ["jsonpath", "$", "length"]
        remote_first_post_title: ["jsonpath", "$[0].title"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$", "type", "array"]
''',步骤名称: "远程数据查询"

[打印],内容: "远程查询结果: ${remote_query_result}"

# 步骤4: 数据处理和分析
[打印],内容: "步骤4: 数据处理和分析"

# 使用JSON提取进行数据分析
local_analysis = [JSON提取],JSON数据: '{"posts_count": 10, "avg_length": 150, "categories": ["tech", "life"]}',JSONPath: "$.posts_count",变量名: "local_analysis_count"
remote_analysis = remote_server|[JSON提取],JSON数据: '{"posts_count": 20, "avg_length": 200, "categories": ["business", "tech"]}',JSONPath: "$.posts_count",变量名: "remote_analysis_count"

[打印],内容: "本地分析结果: ${local_analysis}"
[打印],内容: "远程分析结果: ${remote_analysis}"

# 生成分析报告
local_report_id = [生成随机字符串],长度: 8,类型: "mixed"
remote_report_id = remote_server|[生成随机字符串],长度: 8,类型: "mixed"

[设置全局变量],变量名: "local_report_id",值: "${local_report_id}"
remote_server|[设置全局变量],变量名: "remote_report_id",值: "${remote_report_id}"

[打印],内容: "本地报告ID: ${local_report_id}"
[打印],内容: "远程报告ID: ${remote_report_id}"

# 步骤5: 业务逻辑处理
[打印],内容: "步骤5: 业务逻辑处理"

# 复杂业务逻辑：根据数据创建新内容
current_time = [获取当前时间],格式: "%Y-%m-%d %H:%M:%S"
remote_current_time = remote_server|[获取当前时间],格式: "%Y-%m-%d %H:%M:%S"

# 创建业务数据
local_business_result = [HTTP请求],客户端: "default",会话: "local_user_session",配置: '''
    method: POST
    url: ${local_api_base}/posts
    request:
        json:
            title: "Local Business Report ${local_report_id}"
            body: "Generated at ${current_time}"
            userId: ${local_user_id}
    captures:
        local_business_post_id: ["jsonpath", "$.id"]
        local_business_title: ["jsonpath", "$.title"]
    asserts:
        - ["status", "eq", 201]
''',步骤名称: "本地业务逻辑处理"

remote_business_result = remote_server|[HTTP请求],客户端: "default",会话: "remote_user_session",配置: '''
    method: POST
    url: ${remote_api_base}/posts
    request:
        json:
            title: "Remote Business Report ${remote_report_id}"
            body: "Generated at ${remote_current_time}"
            userId: ${remote_user_id}
    captures:
        remote_business_post_id: ["jsonpath", "$.id"]
        remote_business_title: ["jsonpath", "$.title"]
    asserts:
        - ["status", "eq", 201]
''',步骤名称: "远程业务逻辑处理"

[打印],内容: "本地业务处理结果: ${local_business_result}"
[打印],内容: "远程业务处理结果: ${remote_business_result}"

# 步骤6: 数据验证和断言
[打印],内容: "步骤6: 数据验证和断言"

# 验证创建的数据
local_verification = [HTTP请求],客户端: "default",会话: "local_user_session",配置: '''
    method: GET
    url: ${local_api_base}/posts/1
    captures:
        verified_local_title: ["jsonpath", "$.title"]
        verified_local_user_id: ["jsonpath", "$.userId"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.id", "eq", 1]
''',步骤名称: "本地数据验证"

remote_verification = remote_server|[HTTP请求],客户端: "default",会话: "remote_user_session",配置: '''
    method: GET
    url: ${remote_api_base}/posts/1
    captures:
        verified_remote_title: ["jsonpath", "$.title"]
        verified_remote_user_id: ["jsonpath", "$.userId"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.id", "eq", 1]
''',步骤名称: "远程数据验证"

[打印],内容: "本地验证结果: ${local_verification}"
[打印],内容: "远程验证结果: ${remote_verification}"

# 执行复杂断言
[断言],条件: "'${local_report_id}' != '${remote_report_id}'",消息: "本地和远程报告ID应该不同"
[断言],条件: "len('${local_report_id}') == 8",消息: "本地报告ID长度应该为8"

remote_server|[断言],条件: "len('${remote_report_id}') == 8",消息: "远程报告ID长度应该为8"

# 类型断言
[类型断言],值: "${local_user_id}",类型: "number",消息: "本地用户ID应该是数字"
remote_server|[类型断言],值: "${remote_user_id}",类型: "number",消息: "远程用户ID应该是数字"

# 数据比较
local_compare_result = [数据比较],实际值: "${local_user_id}",预期值: 1,操作符: "==",消息: "本地用户ID比较"
remote_compare_result = remote_server|[数据比较],实际值: "${remote_user_id}",预期值: 2,操作符: "==",消息: "远程用户ID比较"

[打印],内容: "本地比较结果: ${local_compare_result}"
[打印],内容: "远程比较结果: ${remote_compare_result}"

# 步骤7: 性能和压力测试
[打印],内容: "步骤7: 性能和压力测试"

# 批量请求测试
for i in range(1, 4) do
    batch_local_result = [HTTP请求],客户端: "default",配置: '''
        method: GET
        url: ${local_api_base}/posts/${i}
        captures:
            batch_local_id_${i}: ["jsonpath", "$.id"]
        asserts:
            - ["status", "eq", 200]
    ''',步骤名称: "本地批量请求${i}"

    batch_remote_result = remote_server|[HTTP请求],客户端: "default",配置: '''
        method: GET
        url: ${remote_api_base}/posts/${i}
        captures:
            batch_remote_id_${i}: ["jsonpath", "$.id"]
        asserts:
            - ["status", "eq", 200]
    ''',步骤名称: "远程批量请求${i}"

    [打印],内容: "批量测试${i} - 本地: ${batch_local_result}, 远程: ${batch_remote_result}"
end

# 步骤8: 清理和总结
[打印],内容: "步骤8: 清理和总结"

# 获取最终统计信息
final_local_env = [获取全局变量],变量名: "local_env"
final_remote_env = remote_server|[获取全局变量],变量名: "remote_env"
final_local_report = [获取全局变量],变量名: "local_report_id"
final_remote_report = remote_server|[获取全局变量],变量名: "remote_report_id"

[打印],内容: "测试总结:"
[打印],内容: "- 本地环境: ${final_local_env}, 报告ID: ${final_local_report}"
[打印],内容: "- 远程环境: ${final_remote_env}, 报告ID: ${final_remote_report}"

# 生成测试报告
test_summary = [字符串操作],操作: "concat",字符串: "综合测试完成 - 本地环境: ",参数1: "${final_local_env}",参数2: ", 远程环境: ${final_remote_env}"
[打印],内容: "${test_summary}"

# 最终验证
[断言],条件: "'${final_local_env}' == 'development'",消息: "本地环境配置验证"
remote_server|[断言],条件: "'${final_remote_env}' == 'production'",消息: "远程环境配置验证"

[打印],内容: "=== 远程关键字综合功能测试完成 ==="
[打印],内容: "✅ 所有综合功能测试通过！"

@teardown do
    [打印],内容: "执行综合测试清理..."

    # 清理全局变量
    try
        [清除所有全局变量]
        remote_server|[清除所有全局变量]
    catch error
        [打印],内容: "清理过程中出现错误，但测试已完成"
    end

    [打印],内容: "远程关键字综合测试清理完成"
end
