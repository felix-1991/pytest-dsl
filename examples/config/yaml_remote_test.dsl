@name: "YAML远程服务器配置测试"
@description: "测试通过YAML配置自动加载远程服务器的功能"
@tags: ["remote", "yaml", "config"]
@author: "pytest-dsl"
@date: 2024-12-19
@remote: "http://localhost:8272/" as temp

# 注意：此测试需要在config目录下配置remote_servers
# 示例配置请参考 config/remote_servers.yaml

# 测试YAML配置的远程服务器连接
# 假设在YAML中配置了以下服务器：
# remote_servers:
#   main_server:
#     url: "http://localhost:8270/"
#     alias: "main"
#   test_server:
#     url: "http://localhost:8271/"
#     alias: "test"

# 直接使用YAML中配置的远程服务器（无需@remote导入）
main_server|[打印],内容: "这是通过YAML配置的主服务器执行的关键字"

# 测试远程字符串操作
result1 = main_server|[字符串操作],操作: concat, 字符串: "YAML配置-", 参数1: "-测试成功"
[打印],内容: "拼接结果: ${result1}"

# 如果配置了backup服务器，也可以使用
# backup_server|[打印],内容: "这是通过YAML配置的备份服务器执行的关键字"

# 使用@remote语法添加的临时服务器（在metadata部分定义）
temp|[打印],内容: "这是临时添加的远程服务器"

# 测试变量传递功能
g_test_var = "全局测试变量"
main_server|[打印],内容: "远程服务器可以访问全局变量: ${g_test_var}"

# 测试远程关键字返回值
random_num = main_server|[生成随机数],最小值: 1,最大值: 100
[打印],内容: "远程生成的随机数: ${random_num}"

[断言], 条件: "${random_num} >= 1",消息: "随机数应该大于等于1"
[断言], 条件: "${random_num} <= 100",消息: "随机数应该小于等于100"
