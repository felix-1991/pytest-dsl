@name: "Python内置函数关键字示例"
@description: "展示新增的Python内置函数关键字的使用方法"

# ===== 数据准备 =====
[打印], 内容: "=== Python内置函数关键字示例 ==="

# 测试数据
numbers = [10, 25, 5, 30, 15]
prices = [19.99, 25.50, 8.75, 12.30]
text_data = "Hello, pytest-dsl!"
user_scores = [85, 92, 78, 96, 88, 73]

# ===== 数学运算类函数 =====
[打印], 内容: "=== 数学运算类函数 ==="

# 求和功能
total_numbers = [求和], 数据: ${numbers}
[打印], 内容: "数字列表 ${numbers} 的总和: ${total_numbers}"

total_prices = [求和], 数据: ${prices}
[打印], 内容: "价格列表总和: ${total_prices}"

# 带起始值的求和
total_with_bonus = [求和], 数据: ${user_scores}, 起始值: 100
[打印], 内容: "用户分数加100分奖励: ${total_with_bonus}"

# 最大值和最小值
highest_score = [获取最大值], 数据: ${user_scores}
lowest_score = [获取最小值], 数据: ${user_scores}
[打印], 内容: "最高分: ${highest_score}, 最低分: ${lowest_score}"

highest_price = [获取最大值], 数据: ${prices}
lowest_price = [获取最小值], 数据: ${prices}
[打印], 内容: "最高价格: ${highest_price}, 最低价格: ${lowest_price}"

# 绝对值计算
positive_value = 42
abs_positive = [绝对值], 数值: ${positive_value}
[打印], 内容: "${positive_value} 的绝对值: ${abs_positive}"

# 四舍五入
pi_value = 3.14159
rounded_pi = [四舍五入], 数值: ${pi_value}, 小数位数: 2
[打印], 内容: "π值 ${pi_value} 四舍五入到2位小数: ${rounded_pi}"

average_price = 23.456
rounded_avg = [四舍五入], 数值: ${average_price}
[打印], 内容: "平均价格 ${average_price} 四舍五入到整数: ${rounded_avg}"

# ===== 数据操作类函数 =====
[打印], 内容: "=== 数据操作类函数 ==="

# 获取长度
text_length = [获取长度], 对象: ${text_data}
[打印], 内容: "文本 '${text_data}' 的长度: ${text_length}"

numbers_count = [获取长度], 对象: ${numbers}
[打印], 内容: "数字列表的长度: ${numbers_count}"

scores_count = [获取长度], 对象: ${user_scores}
[打印], 内容: "用户分数列表的长度: ${scores_count}"

# ===== 类型转换类函数 =====
[打印], 内容: "=== 类型转换类函数 ==="

# 转换为字符串
score_str = [转换为字符串], 值: ${highest_score}
[打印], 内容: "最高分转换为字符串: '${score_str}'"

price_str = [转换为字符串], 值: ${total_prices}
[打印], 内容: "总价格转换为字符串: '${price_str}'"

# 转换为整数
number_text = "123"
converted_number = [转换为整数], 值: ${number_text}
[打印], 内容: "字符串 '${number_text}' 转换为整数: ${converted_number}"

# 十六进制转换
hex_value = "ff"
hex_number = [转换为整数], 值: ${hex_value}, 进制: 16
[打印], 内容: "十六进制 '${hex_value}' 转换为整数: ${hex_number}"

# 二进制转换（注意：DSL会将"1010"解析为整数，但转换函数会正确处理）
binary_value = "1010"
binary_number = [转换为整数], 值: ${binary_value}, 进制: 2
[打印], 内容: "二进制 '${binary_value}' 转换为整数: ${binary_number}"

# 转换为浮点数
price_text = "29.99"
converted_price = [转换为浮点数], 值: ${price_text}
[打印], 内容: "字符串 '${price_text}' 转换为浮点数: ${converted_price}"

# 转换为布尔值
zero_value = 0
one_value = 1
empty_text = ""
non_empty_text = "hello"

bool_zero = [转换为布尔值], 值: ${zero_value}
bool_one = [转换为布尔值], 值: ${one_value}
bool_empty = [转换为布尔值], 值: ${empty_text}
bool_text = [转换为布尔值], 值: ${non_empty_text}

[打印], 内容: "数字转布尔值: 0 -> ${bool_zero}, 1 -> ${bool_one}"
[打印], 内容: "字符串转布尔值: '' -> ${bool_empty}, 'hello' -> ${bool_text}"

# ===== 实际应用场景示例 =====
[打印], 内容: "=== 实际应用场景示例 ==="

# 场景1: 计算平均分
total_score = [求和], 数据: ${user_scores}
score_count = [获取长度], 对象: ${user_scores}
# 注意：这里需要先转换为浮点数再计算，因为DSL不支持直接除法运算
total_float = [转换为浮点数], 值: ${total_score}
count_float = [转换为浮点数], 值: ${score_count}
# 实际项目中可能需要通过其他方式计算平均值
[打印], 内容: "总分: ${total_score}, 人数: ${score_count}"

# 场景2: 数据验证
min_required_score = 60
max_score = [获取最大值], 数据: ${user_scores}
min_score = [获取最小值], 数据: ${user_scores}

[断言], 条件: "${max_score} <= 100", 消息: "最高分不应超过100分"
[断言], 条件: "${min_score} >= 0", 消息: "最低分不应低于0分"
[打印], 内容: "分数范围验证通过: ${min_score} - ${max_score}"

# 场景3: 数据格式化
formatted_scores = []
# 在实际使用中，可能需要循环处理每个分数
first_score = ${user_scores[0]}
formatted_first = [转换为字符串], 值: ${first_score}
[打印], 内容: "第一个分数格式化: ${formatted_first}"

# 场景4: 价格计算
total_amount = [求和], 数据: ${prices}
rounded_total = [四舍五入], 数值: ${total_amount}, 小数位数: 2
total_str = [转换为字符串], 值: ${rounded_total}
[打印], 内容: "购物车总金额: $${total_str}"

# 场景5: 数据统计
item_count = [获取长度], 对象: ${prices}
avg_price_raw = 16.635  # 假设计算出的平均价格
avg_price = [四舍五入], 数值: ${avg_price_raw}, 小数位数: 2
[打印], 内容: "商品统计: 共${item_count}件商品，平均价格: $${avg_price}"

[打印], 内容: "=== Python内置函数关键字示例完成 ==="
[打印], 内容: "✅ 所有功能演示完毕！" 