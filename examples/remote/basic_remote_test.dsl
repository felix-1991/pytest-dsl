@name: "基础远程关键字测试"
@description: "测试远程关键字的基本功能，包括打印、返回值、工具关键字等"
@tags: ["remote", "basic", "example"]
@author: "Felix"
@date: 2024-12-19

# 导入远程关键字服务器
@remote: "http://localhost:8270/" as remote_server

[打印],内容: "=== 基础远程关键字测试开始 ==="

# 测试1: 基础打印功能
[打印],内容: "--- 测试1: 基础打印功能 ---"

# 本地打印
[打印],内容: "本地打印: Hello World!"

# 远程打印
remote_server|[打印],内容: "远程打印: Hello Remote World!"

# 测试2: 返回值功能
[打印],内容: "--- 测试2: 返回值功能 ---"

# 本地返回值
local_result = [返回结果],结果: "本地返回的值"
[打印],内容: "本地返回结果: ${local_result}"

# 远程返回值
remote_result = remote_server|[返回结果],结果: "远程返回的值"
[打印],内容: "远程返回结果: ${remote_result}"

# 验证返回值
[断言],条件: "'${local_result}' == '本地返回的值'",消息: "本地返回值验证失败"
[断言],条件: "'${remote_result}' == '远程返回的值'",消息: "远程返回值验证失败"

# 测试3: 工具关键字
[打印],内容: "--- 测试3: 工具关键字 ---"

# 生成随机字符串
local_random_str = [生成随机字符串],长度: 8,类型: "mixed"
remote_random_str = remote_server|[生成随机字符串],长度: 8,类型: "mixed"

[打印],内容: "本地生成随机字符串: ${local_random_str}"
[打印],内容: "远程生成随机字符串: ${remote_random_str}"

# 验证随机字符串长度
[断言],条件: "len('${local_random_str}') == 8",消息: "本地随机字符串长度不正确"
[断言],条件: "len('${remote_random_str}') == 8",消息: "远程随机字符串长度不正确"

# 生成随机数
local_random_num = [生成随机数],最小值: 1,最大值: 100
remote_random_num = remote_server|[生成随机数],最小值: 1,最大值: 100

[打印],内容: "本地生成随机数: ${local_random_num}"
[打印],内容: "远程生成随机数: ${remote_random_num}"

# 验证随机数范围（简化验证）
[断言],条件: "${local_random_num} > 0",消息: "本地随机数应该大于0"
[断言],条件: "${remote_random_num} > 0",消息: "远程随机数应该大于0"

# 测试4: 字符串操作
[打印],内容: "--- 测试4: 字符串操作 ---"

# 字符串拼接
local_concat = [字符串操作],操作: "concat",字符串: "Hello",参数1: " ",参数2: "Local"
remote_concat = remote_server|[字符串操作],操作: "concat",字符串: "Hello",参数1: " ",参数2: "Remote"

[打印],内容: "本地字符串拼接: ${local_concat}"
[打印],内容: "远程字符串拼接: ${remote_concat}"

# 验证拼接结果（简化验证）
[断言],条件: "len('${local_concat}') > 0",消息: "本地字符串拼接应该有内容"
[断言],条件: "len('${remote_concat}') > 0",消息: "远程字符串拼接应该有内容"

# 测试5: 时间功能
[打印],内容: "--- 测试5: 时间功能 ---"

# 获取当前时间
local_time = [获取当前时间],格式: "%Y-%m-%d %H:%M:%S"
remote_time = remote_server|[获取当前时间],格式: "%Y-%m-%d %H:%M:%S"

[打印],内容: "本地当前时间: ${local_time}"
[打印],内容: "远程当前时间: ${remote_time}"

# 验证时间格式（简单验证长度）
[断言],条件: "len('${local_time}') == 19",消息: "本地时间格式不正确"
[断言],条件: "len('${remote_time}') == 19",消息: "远程时间格式不正确"

# 测试6: 断言功能
[打印],内容: "--- 测试6: 断言功能 ---"

# 本地断言
[断言],条件: "1 + 1 == 2",消息: "本地基本数学断言"
[打印],内容: "本地断言测试通过"

# 远程断言
remote_server|[断言],条件: "2 * 3 == 6",消息: "远程基本数学断言"
[打印],内容: "远程断言测试通过"

# 数据比较
local_compare = [数据比较],实际值: 10,预期值: 10,操作符: "==",消息: "本地数据比较"
remote_compare = remote_server|[数据比较],实际值: 20,预期值: 20,操作符: "==",消息: "远程数据比较"

[打印],内容: "本地数据比较结果: ${local_compare}"
[打印],内容: "远程数据比较结果: ${remote_compare}"

# 验证比较结果
[断言],条件: "${local_compare} == True",消息: "本地数据比较应该返回True"
[断言],条件: "${remote_compare} == True",消息: "远程数据比较应该返回True"

# 类型断言
local_type_check = [类型断言],值: "hello",类型: "string",消息: "本地类型检查"
remote_type_check = remote_server|[类型断言],值: 123,类型: "number",消息: "远程类型检查"

[打印],内容: "本地类型断言结果: ${local_type_check}"
[打印],内容: "远程类型断言结果: ${remote_type_check}"

# 验证类型断言结果
[断言],条件: "${local_type_check} == True",消息: "本地类型断言应该返回True"
[断言],条件: "${remote_type_check} == True",消息: "远程类型断言应该返回True"

[打印],内容: "=== 基础远程关键字测试完成 ==="
[打印],内容: "✅ 所有基础功能测试通过！"

teardown do
    [打印],内容: "基础远程关键字测试清理完成"
end
