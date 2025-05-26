@name: "远程全局变量功能测试"
@description: "测试远程关键字模式下的全局变量管理功能"
@tags: ["remote", "global", "variables", "example"]
@author: "Felix"
@date: 2024-12-19

# 导入远程关键字服务器
@remote: "http://localhost:8270/" as remote_server

[打印],内容: "=== 远程全局变量功能测试开始 ==="

# 清理可能存在的全局变量
[清除所有全局变量]
remote_server|[清除所有全局变量]

# 测试1: 基本全局变量操作
[打印],内容: "--- 测试1: 基本全局变量操作 ---"

# 本地全局变量操作
[设置全局变量],变量名: "local_config",值: "development"
[设置全局变量],变量名: "local_version",值: "1.0.0"
[设置全局变量],变量名: "local_debug",值: true

local_config = [获取全局变量],变量名: "local_config"
local_version = [获取全局变量],变量名: "local_version"
local_debug = [获取全局变量],变量名: "local_debug"

[打印],内容: "本地配置: ${local_config}"
[打印],内容: "本地版本: ${local_version}"
[打印],内容: "本地调试模式: ${local_debug}"

# 远程全局变量操作
remote_server|[设置全局变量],变量名: "remote_config",值: "production"
remote_server|[设置全局变量],变量名: "remote_version",值: "2.0.0"
remote_server|[设置全局变量],变量名: "remote_debug",值: false

remote_config = remote_server|[获取全局变量],变量名: "remote_config"
remote_version = remote_server|[获取全局变量],变量名: "remote_version"
remote_debug = remote_server|[获取全局变量],变量名: "remote_debug"

[打印],内容: "远程配置: ${remote_config}"
[打印],内容: "远程版本: ${remote_version}"
[打印],内容: "远程调试模式: ${remote_debug}"

# 验证本地和远程变量独立性
[断言],条件: "'${local_config}' != '${remote_config}'",消息: "本地和远程配置应该不同"
[断言],条件: "'${local_version}' != '${remote_version}'",消息: "本地和远程版本应该不同"

# 测试2: 复杂数据类型的全局变量
[打印],内容: "--- 测试2: 复杂数据类型的全局变量 ---"

# 设置复杂数据类型
complex_data = '{"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}], "settings": {"theme": "dark", "language": "zh-CN"}}'

[设置全局变量],变量名: "local_complex_data",值: "${complex_data}"
remote_server|[设置全局变量],变量名: "remote_complex_data",值: "${complex_data}"

# 获取并验证复杂数据
local_complex = [获取全局变量],变量名: "local_complex_data"
remote_complex = remote_server|[获取全局变量],变量名: "remote_complex_data"

[打印],内容: "本地复杂数据: ${local_complex}"
[打印],内容: "远程复杂数据: ${remote_complex}"

# 使用JSON断言验证数据结构
[JSON断言],JSON数据: "${local_complex}",JSONPath: "$.users[0].name",预期值: "Alice",操作符: "==",消息: "本地复杂数据验证"
remote_server|[JSON断言],JSON数据: "${remote_complex}",JSONPath: "$.settings.theme",预期值: "dark",操作符: "==",消息: "远程复杂数据验证"

# 测试3: 全局变量的增删改查
[打印],内容: "--- 测试3: 全局变量的增删改查 ---"

# 创建多个全局变量
variable_names = ["var1", "var2", "var3", "var4", "var5"]
variable_values = ["value1", "value2", "value3", "value4", "value5"]

# 批量设置本地全局变量
[设置全局变量],变量名: "var1",值: "value1"
[设置全局变量],变量名: "var2",值: "value2"
[设置全局变量],变量名: "var3",值: "value3"

# 批量设置远程全局变量
remote_server|[设置全局变量],变量名: "remote_var1",值: "remote_value1"
remote_server|[设置全局变量],变量名: "remote_var2",值: "remote_value2"
remote_server|[设置全局变量],变量名: "remote_var3",值: "remote_value3"

# 批量获取并验证
var1 = [获取全局变量],变量名: "var1"
var2 = [获取全局变量],变量名: "var2"
var3 = [获取全局变量],变量名: "var3"

remote_var1 = remote_server|[获取全局变量],变量名: "remote_var1"
remote_var2 = remote_server|[获取全局变量],变量名: "remote_var2"
remote_var3 = remote_server|[获取全局变量],变量名: "remote_var3"

[打印],内容: "本地变量: ${var1}, ${var2}, ${var3}"
[打印],内容: "远程变量: ${remote_var1}, ${remote_var2}, ${remote_var3}"

# 修改变量值
[设置全局变量],变量名: "var2",值: "modified_value2"
remote_server|[设置全局变量],变量名: "remote_var2",值: "modified_remote_value2"

# 验证修改结果
modified_var2 = [获取全局变量],变量名: "var2"
modified_remote_var2 = remote_server|[获取全局变量],变量名: "remote_var2"

[打印],内容: "修改后的本地变量2: ${modified_var2}"
[打印],内容: "修改后的远程变量2: ${modified_remote_var2}"

[断言],条件: "'${modified_var2}' == 'modified_value2'",消息: "本地变量修改验证"
[断言],条件: "'${modified_remote_var2}' == 'modified_remote_value2'",消息: "远程变量修改验证"

# 删除部分变量
[删除全局变量],变量名: "var3"
remote_server|[删除全局变量],变量名: "remote_var3"

# 验证删除结果（尝试获取已删除的变量应该失败）
try
    deleted_var = [获取全局变量],变量名: "var3"
    [打印],内容: "错误：应该无法获取已删除的变量"
catch error
    [打印],内容: "本地变量删除验证通过"
end

try
    deleted_remote_var = remote_server|[获取全局变量],变量名: "remote_var3"
    [打印],内容: "错误：应该无法获取已删除的远程变量"
catch error
    [打印],内容: "远程变量删除验证通过"
end

# 测试4: 全局变量在HTTP请求中的应用
[打印],内容: "--- 测试4: 全局变量在HTTP请求中的应用 ---"

# 设置API配置全局变量
[设置全局变量],变量名: "api_base_url",值: "https://jsonplaceholder.typicode.com"
[设置全局变量],变量名: "api_timeout",值: 30
[设置全局变量],变量名: "user_id",值: 1

remote_server|[设置全局变量],变量名: "remote_api_base_url",值: "https://jsonplaceholder.typicode.com"
remote_server|[设置全局变量],变量名: "remote_api_timeout",值: 30
remote_server|[设置全局变量],变量名: "remote_user_id",值: 2

# 获取全局变量用于HTTP请求
api_base = [获取全局变量],变量名: "api_base_url"
user_id = [获取全局变量],变量名: "user_id"

remote_api_base = remote_server|[获取全局变量],变量名: "remote_api_base_url"
remote_user_id = remote_server|[获取全局变量],变量名: "remote_user_id"

# 使用全局变量进行HTTP请求
local_api_result = [HTTP请求],客户端: "default",配置: '''
    method: GET
    url: ${api_base}/posts
    request:
        params:
            userId: ${user_id}
    captures:
        local_posts_count: ["jsonpath", "$", "length"]
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "本地使用全局变量的API请求"

remote_api_result = remote_server|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: ${remote_api_base}/posts
    request:
        params:
            userId: ${remote_user_id}
    captures:
        remote_posts_count: ["jsonpath", "$", "length"]
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "远程使用全局变量的API请求"

[打印],内容: "本地API请求结果: ${local_api_result}"
[打印],内容: "远程API请求结果: ${remote_api_result}"

# 测试5: 全局变量的并发访问
[打印],内容: "--- 测试5: 全局变量的并发访问 ---"

# 设置共享配置
[设置全局变量],变量名: "shared_counter",值: 0
remote_server|[设置全局变量],变量名: "remote_shared_counter",值: 0

# 模拟并发更新
for i in range(1, 4) do
    current_local = [获取全局变量],变量名: "shared_counter"
    new_local_value = ${current_local} + 1
    [设置全局变量],变量名: "shared_counter",值: ${new_local_value}
    
    current_remote = remote_server|[获取全局变量],变量名: "remote_shared_counter"
    new_remote_value = ${current_remote} + 1
    remote_server|[设置全局变量],变量名: "remote_shared_counter",值: ${new_remote_value}
    
    [打印],内容: "第${i}次更新 - 本地计数器: ${new_local_value}, 远程计数器: ${new_remote_value}"
end

# 验证最终结果
final_local_counter = [获取全局变量],变量名: "shared_counter"
final_remote_counter = remote_server|[获取全局变量],变量名: "remote_shared_counter"

[打印],内容: "最终本地计数器: ${final_local_counter}"
[打印],内容: "最终远程计数器: ${final_remote_counter}"

[断言],条件: "${final_local_counter} == 3",消息: "本地计数器应该为3"
[断言],条件: "${final_remote_counter} == 3",消息: "远程计数器应该为3"

# 测试6: 全局变量的跨请求持久性
[打印],内容: "--- 测试6: 全局变量的跨请求持久性 ---"

# 设置持久性测试变量
[设置全局变量],变量名: "persistent_token",值: "token_abc123"
remote_server|[设置全局变量],变量名: "remote_persistent_token",值: "remote_token_def456"

# 等待一段时间
[等待],秒数: 1

# 验证变量仍然存在
persistent_token = [获取全局变量],变量名: "persistent_token"
remote_persistent_token = remote_server|[获取全局变量],变量名: "remote_persistent_token"

[打印],内容: "持久化本地令牌: ${persistent_token}"
[打印],内容: "持久化远程令牌: ${remote_persistent_token}"

[断言],条件: "'${persistent_token}' == 'token_abc123'",消息: "本地令牌应该持久化"
[断言],条件: "'${remote_persistent_token}' == 'remote_token_def456'",消息: "远程令牌应该持久化"

[打印],内容: "=== 远程全局变量功能测试完成 ==="
[打印],内容: "✅ 所有全局变量功能测试通过！"

@teardown do
    [打印],内容: "清理测试全局变量..."
    
    # 清理本地全局变量
    try
        [删除全局变量],变量名: "local_config"
        [删除全局变量],变量名: "local_version"
        [删除全局变量],变量名: "local_debug"
        [删除全局变量],变量名: "local_complex_data"
        [删除全局变量],变量名: "var1"
        [删除全局变量],变量名: "var2"
        [删除全局变量],变量名: "api_base_url"
        [删除全局变量],变量名: "api_timeout"
        [删除全局变量],变量名: "user_id"
        [删除全局变量],变量名: "shared_counter"
        [删除全局变量],变量名: "persistent_token"
    catch error
        [打印],内容: "本地变量清理完成（部分变量可能已不存在）"
    end
    
    # 清理远程全局变量
    try
        remote_server|[删除全局变量],变量名: "remote_config"
        remote_server|[删除全局变量],变量名: "remote_version"
        remote_server|[删除全局变量],变量名: "remote_debug"
        remote_server|[删除全局变量],变量名: "remote_complex_data"
        remote_server|[删除全局变量],变量名: "remote_var1"
        remote_server|[删除全局变量],变量名: "remote_var2"
        remote_server|[删除全局变量],变量名: "remote_api_base_url"
        remote_server|[删除全局变量],变量名: "remote_api_timeout"
        remote_server|[删除全局变量],变量名: "remote_user_id"
        remote_server|[删除全局变量],变量名: "remote_shared_counter"
        remote_server|[删除全局变量],变量名: "remote_persistent_token"
    catch error
        [打印],内容: "远程变量清理完成（部分变量可能已不存在）"
    end
    
    [打印],内容: "远程全局变量测试清理完成"
end
