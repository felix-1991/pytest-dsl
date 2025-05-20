@name: "系统关键字测试"
@description: "测试系统内置关键字功能，特别是等待功能"
@tags: ["system", "keywords", "wait"]
@author: "Felix"
@date: 2024-05-20

# 测试打印关键字
[打印],内容: "开始测试系统关键字"

# 测试等待关键字
[打印],内容: "测试等待关键字 - 等待1秒"
start_time = [获取当前时间],格式: "%Y-%m-%d %H:%M:%S.%f"
[等待],秒数: 1
end_time = [获取当前时间],格式: "%Y-%m-%d %H:%M:%S.%f"
[打印],内容: "等待前时间: ${start_time}, 等待后时间: ${end_time}"

# 测试随机字符串生成
[打印],内容: "测试随机字符串生成"
random_str1 = [生成随机字符串],长度: 10,类型: "letters"
random_str2 = [生成随机字符串],长度: 8,类型: "digits"
random_str3 = [生成随机字符串],长度: 12,类型: "alphanumeric"
[打印],内容: "随机字母: ${random_str1}"
[打印],内容: "随机数字: ${random_str2}"
[打印],内容: "随机字母数字: ${random_str3}"

# 测试随机数生成
[打印],内容: "测试随机数生成"
random_int = [生成随机数],最小值: 1,最大值: 100
random_float = [生成随机数],最小值: 0,最大值: 1,小数位数: 2
[打印],内容: "随机整数(1-100): ${random_int}"
[打印],内容: "随机浮点数(0-1): ${random_float}"

# 测试字符串操作
[打印],内容: "测试字符串操作"
original_str = "Hello, World!"
upper_str = [字符串操作],操作: "upper",字符串: "${original_str}"
lower_str = [字符串操作],操作: "lower",字符串: "${original_str}"
concat_str = [字符串操作],操作: "concat",字符串: "${original_str}",参数1: " Welcome!"
replace_str = [字符串操作],操作: "replace",字符串: "${original_str}",参数1: "World",参数2: "Python"
[打印],内容: "原始字符串: ${original_str}"
[打印],内容: "转大写: ${upper_str}"
[打印],内容: "转小写: ${lower_str}"
[打印],内容: "拼接: ${concat_str}"
[打印],内容: "替换: ${replace_str}"

# 测试日志记录
[打印],内容: "测试日志记录"
[日志],级别: "INFO",消息: "这是一条信息日志"
[日志],级别: "WARNING",消息: "这是一条警告日志"
[日志],级别: "ERROR",消息: "这是一条错误日志"

# 测试执行命令
[打印],内容: "测试执行命令"
cmd_result = [执行命令],命令: "echo 'Hello from command line'"
[打印],内容: "命令执行结果: ${cmd_result}"

# 测试返回结果
[打印],内容: "测试返回结果关键字"
result_value = [返回结果],结果: "这是返回的结果"
[打印],内容: "返回的结果: ${result_value}"

[打印],内容: "系统关键字测试完成"
