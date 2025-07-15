@name: 断言关键字完整测试
@description: 演示内置断言关键字的完整功能和正确用法
@tags: [断言, 综合测试, 示例]
@author: pytest-dsl
@date: 2024-01-01

# 配置测试数据
test_number = 42
test_string = "Hello pytest-dsl"
test_boolean = True
test_list = [1, 2, 3, 4, 5]
test_dict = {"name": "张三", "age": 30, "active": True}

# 复杂JSON数据
json_response = '{"status": "success", "code": 200, "data": {"user": {"id": 123, "name": "李四", "email": "lisi@example.com", "scores": [85, 90, 88], "profile": {"city": "北京", "country": "中国"}}, "timestamp": 1640995200}, "message": "操作成功"}'

[打印], 内容: "=== 开始断言关键字完整测试 ==="

# ============================================
# 1. 基础断言测试
# ============================================
[打印], 内容: "1. 基础断言测试"

# 简单数学表达式
[断言], 条件: "1 + 1 == 2", 消息: "基础数学运算断言失败"
[断言], 条件: "10 * 5 == 50", 消息: "乘法运算断言失败"
[断言], 条件: "20 / 4 == 5", 消息: "除法运算断言失败"

# 变量比较
[断言], 条件: "${test_number} == 42", 消息: "数字变量断言失败"
[断言], 条件: "${test_number} > 40", 消息: "数字大小比较断言失败"
[断言], 条件: "${test_number} <= 50", 消息: "数字范围断言失败"

# 字符串断言
[断言], 条件: "${test_string} contains Hello", 消息: "字符串包含断言失败"
[断言], 条件: "${test_string} == Hello pytest-dsl", 消息: "字符串相等断言失败"

# 布尔值断言
[断言], 条件: "${test_boolean} == True", 消息: "布尔值断言失败"
[断言], 条件: "not False", 消息: "布尔逻辑断言失败"

[打印], 内容: "✓ 基础断言测试通过"

# ============================================
# 2. 数据比较测试
# ============================================
[打印], 内容: "2. 数据比较测试"

# 数字比较
[数据比较], 实际值: ${test_number}, 预期值: 42, 操作符: "==", 消息: "数字相等比较失败"
[数据比较], 实际值: ${test_number}, 预期值: 40, 操作符: ">", 消息: "数字大小比较失败"
[数据比较], 实际值: ${test_number}, 预期值: 45, 操作符: "<", 消息: "数字大小比较失败"

# 字符串比较
[数据比较], 实际值: ${test_string}, 预期值: "Hello pytest-dsl", 操作符: "==", 消息: "字符串相等比较失败"
[数据比较], 实际值: ${test_string}, 预期值: "Hello", 操作符: "contains", 消息: "字符串包含比较失败"
[数据比较], 实际值: ${test_string}, 预期值: "Goodbye", 操作符: "not_contains", 消息: "字符串不包含比较失败"

# 使用表达式的比较
[数据比较], 实际值: "10 + 10", 预期值: 20, 消息: "表达式计算比较失败"

[打印], 内容: "✓ 数据比较测试通过"

# ============================================
# 3. 类型断言测试
# ============================================
[打印], 内容: "3. 类型断言测试"

# 基本类型检查
[类型断言], 值: ${test_string}, 类型: "string", 消息: "字符串类型断言失败"
[类型断言], 值: ${test_number}, 类型: "number", 消息: "数字类型断言失败"
[类型断言], 值: ${test_boolean}, 类型: "boolean", 消息: "布尔类型断言失败"
[类型断言], 值: ${test_list}, 类型: "list", 消息: "列表类型断言失败"
[类型断言], 值: ${test_dict}, 类型: "object", 消息: "对象类型断言失败"

# 特殊值类型检查
null_value = "null"
[类型断言], 值: ${null_value}, 类型: "null", 消息: "空值类型断言失败"

# 字符串形式的数字和布尔值
string_number = "123"
string_boolean = "True"
[类型断言], 值: ${string_number}, 类型: "number", 消息: "字符串数字类型断言失败"
[类型断言], 值: ${string_boolean}, 类型: "boolean", 消息: "字符串布尔类型断言失败"

[打印], 内容: "✓ 类型断言测试通过"

# ============================================
# 4. JSON数据提取测试
# ============================================
[打印], 内容: "4. JSON数据提取测试"

# 基础字段提取
status = [JSON提取], JSON数据: ${json_response}, JSONPath: "$.status", 变量名: "extracted_status"
[打印], 内容: "提取的状态: ${status}"
[断言], 条件: "${status} == success", 消息: "状态提取断言失败"

# 数字字段提取
code = [JSON提取], JSON数据: ${json_response}, JSONPath: "$.code", 变量名: "extracted_code"
[打印], 内容: "提取的状态码: ${code}"
[断言], 条件: "${code} == 200", 消息: "状态码提取断言失败"

# 嵌套字段提取
user_id = [JSON提取], JSON数据: ${json_response}, JSONPath: "$.data.user.id", 变量名: "extracted_user_id"
[打印], 内容: "提取的用户ID: ${user_id}"
[断言], 条件: "${user_id} == 123", 消息: "用户ID提取断言失败"

user_name = [JSON提取], JSON数据: ${json_response}, JSONPath: "$.data.user.name", 变量名: "extracted_user_name"
[打印], 内容: "提取的用户名: ${user_name}"
[断言], 条件: "${user_name} == 李四", 消息: "用户名提取断言失败"

# 数组元素提取
first_score = [JSON提取], JSON数据: ${json_response}, JSONPath: "$.data.user.scores[0]", 变量名: "extracted_first_score"
[打印], 内容: "提取的第一个分数: ${first_score}"
[断言], 条件: "${first_score} == 85", 消息: "第一个分数提取断言失败"

# 所有分数提取
all_scores = [JSON提取], JSON数据: ${json_response}, JSONPath: "$.data.user.scores[*]", 变量名: "extracted_all_scores"
[打印], 内容: "提取的所有分数: ${all_scores}"

# 深度嵌套提取
user_city = [JSON提取], JSON数据: ${json_response}, JSONPath: "$.data.user.profile.city", 变量名: "extracted_city"
[打印], 内容: "提取的城市: ${user_city}"
[断言], 条件: "${user_city} == 北京", 消息: "城市提取断言失败"

[打印], 内容: "✓ JSON数据提取测试通过"

# ============================================
# 5. JSON断言测试
# ============================================
[打印], 内容: "5. JSON断言测试"

# 基础JSON断言
[JSON断言], JSON数据: ${json_response}, JSONPath: "$.status", 预期值: "success", 消息: "状态字段JSON断言失败"
[JSON断言], JSON数据: ${json_response}, JSONPath: "$.code", 预期值: 200, 消息: "状态码字段JSON断言失败"

# 不同操作符的JSON断言
[JSON断言], JSON数据: ${json_response}, JSONPath: "$.code", 预期值: 200, 操作符: "==", 消息: "状态码相等断言失败"
[JSON断言], JSON数据: ${json_response}, JSONPath: "$.code", 预期值: 100, 操作符: ">", 消息: "状态码大于断言失败"
[JSON断言], JSON数据: ${json_response}, JSONPath: "$.code", 预期值: 300, 操作符: "<", 消息: "状态码小于断言失败"

# 嵌套字段断言
[JSON断言], JSON数据: ${json_response}, JSONPath: "$.data.user.id", 预期值: 123, 消息: "用户ID JSON断言失败"
[JSON断言], JSON数据: ${json_response}, JSONPath: "$.data.user.name", 预期值: "李四", 消息: "用户名JSON断言失败"
[JSON断言], JSON数据: ${json_response}, JSONPath: "$.data.user.email", 预期值: "lisi@example.com", 消息: "邮箱JSON断言失败"

# 数组元素断言
[JSON断言], JSON数据: ${json_response}, JSONPath: "$.data.user.scores[0]", 预期值: 85, 消息: "第一个分数JSON断言失败"
[JSON断言], JSON数据: ${json_response}, JSONPath: "$.data.user.scores[1]", 预期值: 90, 消息: "第二个分数JSON断言失败"

# 深度嵌套断言
[JSON断言], JSON数据: ${json_response}, JSONPath: "$.data.user.profile.city", 预期值: "北京", 消息: "城市JSON断言失败"
[JSON断言], JSON数据: ${json_response}, JSONPath: "$.data.user.profile.country", 预期值: "中国", 消息: "国家JSON断言失败"

[打印], 内容: "✓ JSON断言测试通过"

# ============================================
# 6. 复杂条件断言测试
# ============================================
[打印], 内容: "6. 复杂条件断言测试"

# 复合条件 - 分步断言
score1 = 85
score2 = 90
[断言], 条件: "${score1} >= 80", 消息: "第一个分数应>=80"
[断言], 条件: "${score2} >= 80", 消息: "第二个分数应>=80"

# 范围检查 - 分步断言
temperature = 25
[断言], 条件: "${temperature} >= 20", 消息: "温度应>=20"
[断言], 条件: "${temperature} <= 30", 消息: "温度应<=30"

# 字符串操作组合 - 分步断言
test_email = "test@example.com"
[断言], 条件: "${test_email} contains @", 消息: "邮箱应包含@符号"
[断言], 条件: "${test_email} contains .", 消息: "邮箱应包含点号"

# 列表操作
[断言], 条件: "1 in ${test_list}", 消息: "列表包含断言失败"
[断言], 条件: "6 not in ${test_list}", 消息: "列表不包含断言失败"

# 正则表达式匹配（如果支持）
# 注意：对于纯数字字符串的正则匹配，建议在实际使用中通过变量传递并确保类型正确
phone_text = "phone13812345678"
[断言], 条件: "${phone_text} matches phone", 消息: "电话文本正则匹配断言失败"

phone_number = "13812345678"
[断言], 条件: "${phone_number} matches ^138", 消息: "手机号正则匹配断言失败"

[打印], 内容: "✓ 复杂条件断言测试通过"

# ============================================
# 7. 错误处理和边界情况测试
# ============================================
[打印], 内容: "7. 边界情况测试"

# 空字符串测试
empty_string = ""
[类型断言], 值: ${empty_string}, 类型: "string", 消息: "空字符串类型断言失败"
[断言], 条件: "'${empty_string}' == ''", 消息: "空字符串比较断言失败"

# 空列表测试
empty_list = []
[类型断言], 值: ${empty_list}, 类型: "list", 消息: "空列表类型断言失败"

# 零值测试
zero_value = 0
[断言], 条件: "${zero_value} == 0", 消息: "零值断言失败"
[数据比较], 实际值: ${zero_value}, 预期值: 0, 操作符: "==", 消息: "零值比较失败"

# 负数测试（通过变量传递）
# 注意：DSL不支持负数字面量，需要通过配置传递

[打印], 内容: "✓ 边界情况测试通过"

# ============================================
# 8. 实际场景模拟测试
# ============================================
[打印], 内容: "8. 实际场景模拟测试"

# 模拟API响应验证
api_response = '{"success": true, "data": {"products": [{"id": 1, "name": "商品A", "price": 99.99, "stock": 10}, {"id": 2, "name": "商品B", "price": 199.99, "stock": 5}], "total": 2, "page": 1, "pageSize": 10}}'

# 验证API成功状态
api_success = [JSON提取], JSON数据: ${api_response}, JSONPath: "$.success", 变量名: "api_success"
[断言], 条件: "${api_success} == True", 消息: "API成功状态断言失败"

# 验证商品数量
total_products = [JSON提取], JSON数据: ${api_response}, JSONPath: "$.data.total", 变量名: "total_products"
[断言], 条件: "${total_products} > 0", 消息: "商品数量断言失败"
[数据比较], 实际值: ${total_products}, 预期值: 2, 操作符: "==", 消息: "具体商品数量比较失败"

# 验证第一个商品信息
first_product_name = [JSON提取], JSON数据: ${api_response}, JSONPath: "$.data.products[0].name", 变量名: "first_product_name"
[JSON断言], JSON数据: ${api_response}, JSONPath: "$.data.products[0].name", 预期值: "商品A", 消息: "第一个商品名称断言失败"

first_product_price = [JSON提取], JSON数据: ${api_response}, JSONPath: "$.data.products[0].price", 变量名: "first_product_price"
[断言], 条件: "${first_product_price} > 0", 消息: "商品价格应大于0"
[数据比较], 实际值: ${first_product_price}, 预期值: 100, 操作符: "<", 消息: "商品价格应小于100"

# 验证库存充足
first_product_stock = [JSON提取], JSON数据: ${api_response}, JSONPath: "$.data.products[0].stock", 变量名: "first_product_stock"
[断言], 条件: "${first_product_stock} >= 5", 消息: "库存应不少于5件"

[打印], 内容: "✓ 实际场景模拟测试通过"

# ============================================
# 9. 数据类型转换和验证
# ============================================
[打印], 内容: "9. 数据类型转换验证测试"

# 字符串数字的断言
str_num = "42"
[断言], 条件: "${str_num} == 42", 消息: "字符串数字转换断言失败"
[数据比较], 实际值: ${str_num}, 预期值: 42, 操作符: "==", 消息: "字符串数字比较失败"

# 字符串布尔值的断言
str_bool_True = "True"
str_bool_False = "False"
[断言], 条件: "${str_bool_True} == True", 消息: "字符串True转换断言失败"
# 数字字符串的类型检查
[类型断言], 值: ${str_num}, 类型: "number", 消息: "数字字符串类型识别失败"
[类型断言], 值: ${str_bool_True}, 类型: "boolean", 消息: "布尔字符串类型识别失败"

[打印], 内容: "✓ 数据类型转换验证测试通过"

# ============================================
# 测试总结
# ============================================
[打印], 内容: "=== 断言关键字完整测试成功完成 ==="
[打印], 内容: "✓ 所有测试用例都已通过"
[打印], 内容: "✓ 验证了断言、数据比较、类型断言、JSON提取、JSON断言等功能"
[打印], 内容: "✓ 覆盖了基础用法、复杂条件、边界情况和实际应用场景"

teardown do
    [打印], 内容: "断言关键字测试清理完成"
end 