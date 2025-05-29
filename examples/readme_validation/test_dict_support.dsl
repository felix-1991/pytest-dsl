@name: "字典支持测试"
@description: "测试字典字面量定义和访问功能"
@tags: ["字典", "测试"]
@author: "pytest-dsl"
@date: 2024-12-19

# 测试空字典定义
empty_dict = {}
[打印], 内容: "空字典: ${empty_dict}"

# 测试简单字典定义
user_info = {"name": "张三", "age": 30, "city": "北京"}
[打印], 内容: "用户信息: ${user_info}"

# 测试字典访问
username = ${user_info["name"]}
user_age = ${user_info["age"]}
[打印], 内容: "用户名: ${username}"
[打印], 内容: "年龄: ${user_age}"

# 测试嵌套字典
config = {
    "database": {
        "host": "localhost",
        "port": 3306,
        "name": "test_db"
    },
    "api": {
        "base_url": "https://api.example.com",
        "timeout": 30
    }
}
[打印], 内容: "配置信息: ${config}"

# 测试嵌套字典访问
db_host = ${config["database"]["host"]}
api_url = ${config["api"]["base_url"]}
[打印], 内容: "数据库主机: ${db_host}"
[打印], 内容: "API地址: ${api_url}"

# 测试混合数据类型字典
mixed_data = {
    "string_value": "测试字符串",
    "number_value": 42,
    "boolean_value": True,
    "list_value": ["item1", "item2", "item3"],
    "nested_dict": {"key": "value"}
}
[打印], 内容: "混合数据: ${mixed_data}"

# 测试访问混合数据
str_val = ${mixed_data["string_value"]}
num_val = ${mixed_data["number_value"]}
bool_val = ${mixed_data["boolean_value"]}
list_val = ${mixed_data["list_value"]}
nested_val = ${mixed_data["nested_dict"]["key"]}

[打印], 内容: "字符串值: ${str_val}"
[打印], 内容: "数字值: ${num_val}"
[打印], 内容: "布尔值: ${bool_val}"
[打印], 内容: "列表值: ${list_val}"
[打印], 内容: "嵌套值: ${nested_val}"

# 测试断言
[断言], 条件: "${username} == '张三'", 消息: "用户名不匹配"
[断言], 条件: "${user_age} == 30", 消息: "年龄不匹配"
[断言], 条件: "${db_host} == 'localhost'", 消息: "数据库主机不匹配"

[打印], 内容: "字典支持测试完成！"
