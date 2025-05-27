@name: "CLI YAML配置测试"
@description: "测试CLI模式下YAML配置自动加载远程服务器的功能"
@tags: ["cli", "yaml", "remote"]
@author: "pytest-dsl"
@date: 2024-12-19

# 这个测试文件用于验证CLI模式下的YAML配置加载
# 使用方法：
# pytest-dsl --yaml-vars example/config/test_remote_servers.yaml example/cli_yaml_test.dsl

# 如果YAML中配置了远程服务器，可以直接使用
# 例如：main|[打印],内容: "CLI模式下的远程关键字调用"

# 本地关键字测试
[打印],内容: "CLI模式测试开始"

# 测试变量替换（如果YAML中有配置）
[打印],内容: "测试环境: ${g_test_environment}"

# 生成随机数测试
random_num = [生成随机数],最小值: 1,最大值: 100
[打印],内容: "生成的随机数: ${random_num}"

# 字符串操作测试
result = [字符串操作],操作: "concat",字符串: "CLI测试-",参数1: "完成"
[打印],内容: "拼接结果: ${result}"

[打印],内容: "CLI模式测试完成"
