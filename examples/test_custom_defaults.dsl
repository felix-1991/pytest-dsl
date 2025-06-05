@name: "自定义关键字默认值测试"
@description: "测试自定义关键字中的默认值功能"

# 注意：需要确保custom_keywords_with_defaults.py已经被加载
# 可以通过以下方式之一：
# 1. 将文件放在keywords目录下
# 2. 使用Python导入机制加载

[打印], 内容: "=== 自定义关键字默认值功能测试 ==="

# 测试1：HTTP请求模拟 - 使用默认值
[打印], 内容: "--- 测试1：HTTP请求模拟 ---"

# 只传递必需的参数，其他使用默认值
response1 = [HTTP请求模拟], 地址: "https://api.example.com/users"
[打印], 内容: "响应1 - 使用默认方法(GET)、超时(30)、重试(3)、SSL验证(True): ${response1}"

# 部分覆盖默认值
response2 = [HTTP请求模拟], 方法: "POST", 地址: "https://api.example.com/users", 超时: 60
[打印], 内容: "响应2 - 自定义方法和超时: ${response2}"

# 覆盖所有参数
response3 = [HTTP请求模拟], 方法: "PUT", 地址: "https://api.example.com/users/1", 超时: 45, 重试次数: 5, 验证SSL: False
[打印], 内容: "响应3 - 所有参数自定义: ${response3}"

# 测试2：数据库连接 - 使用默认值
[打印], 内容: "--- 测试2：数据库连接 ---"

# 只传递必需的参数
conn1 = [数据库连接], 用户名: "admin", 密码: "password", 数据库名: "test_db"
[打印], 内容: "连接1 - 使用默认主机(localhost)、端口(3306)、池大小(10)、超时(30): ${conn1}"

# 部分覆盖默认值
conn2 = [数据库连接], 主机: "db.example.com", 端口: 5432, 用户名: "user", 密码: "pass", 数据库名: "app_db"
[打印], 内容: "连接2 - 自定义主机和端口: ${conn2}"

# 覆盖所有参数
conn3 = [数据库连接], 主机: "remote.db.com", 端口: 3307, 用户名: "root", 密码: "secret", 数据库名: "prod_db", 连接池大小: 20, 连接超时: 60
[打印], 内容: "连接3 - 所有参数自定义: ${conn3}"

# 测试3：文件处理 - 使用默认值
[打印], 内容: "--- 测试3：文件处理 ---"

# 只传递必需的参数
file1 = [文件处理], 文件路径: "/tmp/test.txt"
[打印], 内容: "文件操作1 - 使用默认操作(read)、编码(utf-8)、缓冲区(8192)、创建目录(False): ${file1}"

# 部分覆盖默认值
file2 = [文件处理], 文件路径: "/data/config.json", 操作: "write", 编码: "gbk"
[打印], 内容: "文件操作2 - 自定义操作和编码: ${file2}"

# 覆盖所有参数
file3 = [文件处理], 文件路径: "/opt/app/logs/app.log", 操作: "append", 编码: "utf-8", 缓冲区大小: 4096, 创建目录: True
[打印], 内容: "文件操作3 - 所有参数自定义: ${file3}"

# 测试4：验证默认值的灵活性
[打印], 内容: "--- 测试4：验证默认值灵活性 ---"

# 测试不同的参数组合
requests = []

# 组合1：只改方法
req1 = [HTTP请求模拟], 方法: "DELETE", 地址: "https://api.example.com/users/1"
requests = requests + [req1]

# 组合2：只改超时
req2 = [HTTP请求模拟], 地址: "https://api.example.com/slow-endpoint", 超时: 120
requests = requests + [req2]

# 组合3：只改SSL验证
req3 = [HTTP请求模拟], 地址: "https://internal-api.example.com/health", 验证SSL: False
requests = requests + [req3]

[打印], 内容: "创建了 ${len(requests)} 个不同配置的请求，展示了默认值的灵活性"

# 测试5：嵌套使用默认值
[打印], 内容: "--- 测试5：嵌套使用默认值 ---"

# 模拟一个测试流程：连接数据库 -> 执行HTTP请求 -> 处理文件
[打印], 内容: "模拟测试流程开始..."

# 步骤1：连接测试数据库（使用默认配置）
test_conn = [数据库连接], 用户名: "test_user", 密码: "test_pass", 数据库名: "test_db"
[打印], 内容: "步骤1完成 - 数据库连接: ${test_conn.connection_id}"

# 步骤2：执行API调用（使用默认HTTP配置）
api_response = [HTTP请求模拟], 地址: "https://api.example.com/test-data"
[打印], 内容: "步骤2完成 - API响应: ${api_response.status_code}"

# 步骤3：处理结果文件（使用默认文件配置）
file_result = [文件处理], 文件路径: "/tmp/test_results.json"
[打印], 内容: "步骤3完成 - 文件处理: ${file_result.status}"

[打印], 内容: "模拟测试流程完成！所有步骤都成功使用了默认值配置。"

teardown do
    [打印], 内容: "自定义关键字默认值测试完成！"
    [打印], 内容: "总结："
    [打印], 内容: "- 默认值让关键字调用更简洁"
    [打印], 内容: "- 只需要指定必要的参数"
    [打印], 内容: "- 可以选择性地覆盖默认值"
    [打印], 内容: "- 提高了DSL的可读性和易用性"
end 