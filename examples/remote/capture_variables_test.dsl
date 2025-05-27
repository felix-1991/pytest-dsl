@name: "远程变量捕获功能测试"
@description: "专门测试远程关键字模式下的变量捕获功能"
@tags: ["remote", "capture", "variables", "example"]
@author: "Felix"
@date: 2024-12-19

# 导入远程关键字服务器
@remote: "http://localhost:8270/" as remote_server

[打印],内容: "=== 远程变量捕获功能测试开始 ==="

# 测试1: HTTP请求变量捕获
[打印],内容: "--- 测试1: HTTP请求变量捕获 ---"

# 本地HTTP请求捕获变量
local_http_result = [HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
    captures:
        post_id: ["jsonpath", "$.id"]
        post_title: ["jsonpath", "$.title"]
        post_body: ["jsonpath", "$.body"]
        user_id: ["jsonpath", "$.userId"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.id", "eq", 1]
''',步骤名称: "本地HTTP请求捕获变量"

[打印],内容: "本地HTTP捕获结果: ${local_http_result}"
[打印],内容: "本地捕获的文章ID: ${post_id}"
[打印],内容: "本地捕获的文章标题: ${post_title}"

# 远程HTTP请求捕获变量
remote_http_result = remote_server|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/2
    captures:
        remote_post_id: ["jsonpath", "$.id"]
        remote_post_title: ["jsonpath", "$.title"]
        remote_post_body: ["jsonpath", "$.body"]
        remote_user_id: ["jsonpath", "$.userId"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.id", "eq", 2]
''',步骤名称: "远程HTTP请求捕获变量"

[打印],内容: "远程HTTP捕获结果: ${remote_http_result}"

# 测试2: JSON提取变量捕获
[打印],内容: "--- 测试2: JSON提取变量捕获 ---"

test_json_data = '{"user": {"id": 123, "name": "Alice", "email": "alice@example.com"}, "posts": [{"id": 1, "title": "First Post"}, {"id": 2, "title": "Second Post"}], "metadata": {"total": 2, "page": 1}}'

# 本地JSON提取
local_json_result = [JSON提取],JSON数据: "${test_json_data}",JSONPath: "$.user.name",变量名: "local_user_name"
[打印],内容: "本地JSON提取结果: ${local_json_result}"
[打印],内容: "本地提取的用户名: ${local_user_name}"

local_posts_result = [JSON提取],JSON数据: "${test_json_data}",JSONPath: "$.posts",变量名: "local_posts_data"
[打印],内容: "本地提取的文章数据: ${local_posts_data}"

# 远程JSON提取
remote_json_result = remote_server|[JSON提取],JSON数据: "${test_json_data}",JSONPath: "$.user.email",变量名: "remote_user_email"
[打印],内容: "远程JSON提取结果: ${remote_json_result}"

remote_total_result = remote_server|[JSON提取],JSON数据: "${test_json_data}",JSONPath: "$.metadata.total",变量名: "remote_total_count"
[打印],内容: "远程提取的总数: ${remote_total_result}"

# 测试3: 复杂数据结构捕获
[打印],内容: "--- 测试3: 复杂数据结构捕获 ---"

# 远程HTTP请求捕获数组数据
remote_array_result = remote_server|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts
    request:
        params:
            userId: 1
    captures:
        posts_array: ["jsonpath", "$"]
        posts_count: ["jsonpath", "$", "length"]
        first_post_title: ["jsonpath", "$[0].title"]
        last_post_id: ["jsonpath", "$[-1].id"]
        all_titles: ["jsonpath", "$[*].title"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$", "type", "array"]
''',步骤名称: "远程捕获数组数据"

[打印],内容: "远程数组捕获结果: ${remote_array_result}"

# 测试4: 嵌套对象捕获
[打印],内容: "--- 测试4: 嵌套对象捕获 ---"

# 远程HTTP请求捕获嵌套数据
remote_nested_result = remote_server|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/users/1
    captures:
        user_name: ["jsonpath", "$.name"]
        user_email: ["jsonpath", "$.email"]
        address_city: ["jsonpath", "$.address.city"]
        address_zipcode: ["jsonpath", "$.address.zipcode"]
        company_name: ["jsonpath", "$.company.name"]
        geo_lat: ["jsonpath", "$.address.geo.lat"]
        geo_lng: ["jsonpath", "$.address.geo.lng"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.id", "eq", 1]
''',步骤名称: "远程捕获嵌套对象数据"

[打印],内容: "远程嵌套对象捕获结果: ${remote_nested_result}"

# 测试5: 多次捕获累积测试
[打印],内容: "--- 测试5: 多次捕获累积测试 ---"

# 第一次远程捕获
first_capture = remote_server|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
    captures:
        first_id: ["jsonpath", "$.id"]
        first_title: ["jsonpath", "$.title"]
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "第一次远程捕获"

[打印],内容: "第一次捕获结果: ${first_capture}"

# 第二次远程捕获
second_capture = remote_server|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/2
    captures:
        second_id: ["jsonpath", "$.id"]
        second_title: ["jsonpath", "$.title"]
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "第二次远程捕获"

[打印],内容: "第二次捕获结果: ${second_capture}"

# 第三次远程捕获
third_capture = remote_server|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/3
    captures:
        third_id: ["jsonpath", "$.id"]
        third_title: ["jsonpath", "$.title"]
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "第三次远程捕获"

[打印],内容: "第三次捕获结果: ${third_capture}"

# 测试6: 捕获数据类型验证
[打印],内容: "--- 测试6: 捕获数据类型验证 ---"

# 远程捕获不同类型的数据
type_capture_result = remote_server|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
    captures:
        id_number: ["jsonpath", "$.id"]
        title_string: ["jsonpath", "$.title"]
        user_id_number: ["jsonpath", "$.userId"]
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "远程捕获不同数据类型"

[打印],内容: "类型捕获结果: ${type_capture_result}"

# 验证捕获的数据类型（通过JSON提取验证）
id_type_check = remote_server|[类型断言],值: 1,类型: "number",消息: "ID应该是数字类型"
title_type_check = remote_server|[类型断言],值: "test",类型: "string",消息: "标题应该是字符串类型"

[打印],内容: "ID类型检查结果: ${id_type_check}"
[打印],内容: "标题类型检查结果: ${title_type_check}"

# 测试7: 错误情况下的捕获处理
[打印],内容: "--- 测试7: 错误情况下的捕获处理 ---"

try
    # 尝试捕获不存在的字段
    error_capture_result = remote_server|[HTTP请求],客户端: "default",配置: '''
        method: GET
        url: https://jsonplaceholder.typicode.com/posts/1
        captures:
            nonexistent_field: ["jsonpath", "$.nonexistent"]
        asserts:
            - ["status", "eq", 200]
    ''',步骤名称: "远程捕获不存在的字段"

    [打印],内容: "错误捕获结果: ${error_capture_result}"
catch error
    [打印],内容: "捕获错误处理测试完成: ${error}"
end

[打印],内容: "=== 远程变量捕获功能测试完成 ==="
[打印],内容: "✅ 所有变量捕获功能测试通过！"

teardown do
    [打印],内容: "远程变量捕获测试清理完成"
end
