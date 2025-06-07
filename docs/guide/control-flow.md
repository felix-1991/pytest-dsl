# 流程控制

流程控制是编程的核心概念，pytest-dsl提供了直观的条件判断和循环语法，让您能够创建复杂的测试逻辑。

## 条件判断

### if语句

基本的条件判断语法：

```python
# 基本if语句
status = "success"
if status == "success" do
    [打印], 内容: "测试通过"
end

# 使用变量的条件判断
user_age = 25
if ${user_age} >= 18 do
    [打印], 内容: "用户已成年"
end
```

### if-else语句

```python
# if-else语句
environment = "production"
if environment == "development" do
    [打印], 内容: "开发环境：启用调试模式"
    debug_mode = True
else
    [打印], 内容: "生产环境：关闭调试模式"
    debug_mode = False
end

# 数值比较
score = 85
if ${score} >= 90 do
    grade = "A"
else
    grade = "B"
end
[打印], 内容: "分数: ${score}, 等级: ${grade}"
```

### if-elif-else语句

```python
# 多重条件判断
http_status = 200

if ${http_status} == 200 do
    [打印], 内容: "请求成功"
    result = "success"
elif ${http_status} == 404 do
    [打印], 内容: "资源未找到"
    result = "not_found"
elif ${http_status} >= 500 do
    [打印], 内容: "服务器错误"
    result = "server_error"
else
    [打印], 内容: "其他状态码: ${http_status}"
    result = "unknown"
end

[打印], 内容: "处理结果: ${result}"
```

### 复杂条件表达式

```python
# 逻辑运算符
user_role = "admin"
user_active = True

if user_role == "admin" and ${user_active} do
    [打印], 内容: "管理员用户且状态活跃"
    access_level = "full"
end

# 多条件组合
age = 25
country = "China"
if ${age} >= 18 and country == "China" do
    [打印], 内容: "符合条件的中国成年用户"
end

# 使用or运算符
user_type = "premium"
if user_type == "premium" or user_type == "vip" do
    [打印], 内容: "高级用户，享受特殊权限"
end

# 使用not运算符
is_banned = False
if not ${is_banned} do
    [打印], 内容: "用户未被封禁，可以正常使用"
end
```

### 嵌套条件

```python
# 嵌套if语句
user_type = "admin"
user_department = "IT"

if user_type == "admin" do
    [打印], 内容: "用户是管理员"
    
    if user_department == "IT" do
        [打印], 内容: "IT部门管理员，拥有系统权限"
        system_access = True
    else
        [打印], 内容: "其他部门管理员，拥有业务权限"
        system_access = False
    end
    
    [打印], 内容: "系统访问权限: ${system_access}"
end
```

## 循环结构

### for循环

#### 数值范围循环

```python
# 基本for循环
for i in range(1, 6) do
    [打印], 内容: "第 ${i} 次循环"
end

# 使用变量定义范围
max_count = 5
for j in range(1, ${max_count} + 1) do
    [打印], 内容: "计数: ${j}"
end

# 从0开始的循环
for k in range(5) do
    [打印], 内容: "索引: ${k}"
end
```

#### 列表循环

```python
# 遍历列表 - 注意：当前不支持直接遍历，需要使用索引
users = ["张三", "李四", "王五"]
users_length = 3  # 预定义长度

for i in range(0, ${users_length}) do
    [打印], 内容: "处理用户: ${users[i]}"
end

# 遍历数字列表 - 使用索引访问
numbers = [1, 2, 3, 4, 5]
numbers_length = 5  # 预定义长度
total = 0

for i in range(0, ${numbers_length}) do
    total = total + ${numbers[i]}
    [打印], 内容: "当前数字: ${numbers[i]}, 累计: ${total}"
end
```

#### 字典循环

```python
# 遍历字典的键 - 注意：当前不支持直接遍历字典
user_info = {"name": "张三", "age": 30, "city": "北京"}
# 需要预定义键列表
keys = ["name", "age", "city"]
keys_length = 3

for i in range(0, ${keys_length}) do
    key = ${keys[i]}
    value = ${user_info[key]}
    [打印], 内容: "${key}: ${value}"
end
```

### 循环控制语句

#### break语句

```python
# 使用break退出循环
for i in range(1, 11) do
    if ${i} == 5 do
        [打印], 内容: "达到5，退出循环"
        break
    end
    [打印], 内容: "当前数字: ${i}"
end

# 在条件满足时退出 - 使用索引访问
users = ["admin", "user1", "user2", "guest"]
users_length = 4

for i in range(0, ${users_length}) do
    [打印], 内容: "检查用户: ${users[i]}"
    if ${users[i]} == "guest" do
        [打印], 内容: "找到访客用户，停止搜索"
        break
    end
end
```

#### continue语句

```python
# 使用continue跳过当前迭代
for i in range(1, 11) do
    # 跳过偶数
    if ${i} % 2 == 0 do
        continue
    end
    [打印], 内容: "奇数: ${i}"
end

# 跳过特定条件 - 使用索引访问
test_cases = ["case1", "skip_case", "case2", "case3"]
test_cases_length = 4

for i in range(0, ${test_cases_length}) do
    if ${test_cases[i]} == "skip_case" do
        [打印], 内容: "跳过测试用例: ${test_cases[i]}"
        continue
    end
    [打印], 内容: "执行测试用例: ${test_cases[i]}"
end
```

### 嵌套循环

```python
# 嵌套循环示例 - 使用索引访问
environments = ["dev", "test", "prod"]
test_types = ["unit", "integration", "e2e"]
environments_length = 3
test_types_length = 3

for i in range(0, ${environments_length}) do
    [打印], 内容: "环境: ${environments[i]}"
    
    for j in range(0, ${test_types_length}) do
        [打印], 内容: "  执行 ${test_types[j]} 测试"
        
        # 模拟测试执行
        if ${environments[i]} == "prod" and ${test_types[j]} == "unit" do
            [打印], 内容: "    生产环境跳过单元测试"
            continue
        end
        
        [打印], 内容: "    ${environments[i]} 环境的 ${test_types[j]} 测试完成"
    end
end
```

## 实际应用场景

### 1. API测试中的条件处理

```python
# 根据环境选择不同的API地址
environment = "development"

if environment == "development" do
    api_base = "https://dev-api.example.com"
    timeout = 60
elif environment == "testing" do
    api_base = "https://test-api.example.com"
    timeout = 30
else
    api_base = "https://api.example.com"
    timeout = 10
end

[打印], 内容: "使用API地址: ${api_base}, 超时: ${timeout}秒"

# 执行API测试
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: ${api_base}/health
    timeout: ${timeout}
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "健康检查"
```

### 2. 批量用户测试

```python
# 批量测试多个用户 - 使用索引访问
test_users = [
    {"username": "admin", "password": "admin123", "role": "admin"},
    {"username": "user1", "password": "user123", "role": "user"},
    {"username": "guest", "password": "guest123", "role": "guest"}
]
test_users_length = 3

for i in range(0, ${test_users_length}) do
    username = ${test_users[i]["username"]}
    password = ${test_users[i]["password"]}
    role = ${test_users[i]["role"]}
    
    [打印], 内容: "测试用户: ${username} (${role})"
    
    # 模拟登录
    [HTTP请求], 客户端: "default", 配置: '''
        method: POST
        url: /api/login
        request:
            json:
                username: "${username}"
                password: "${password}"
        captures:
            login_status: ["jsonpath", "$.status"]
            user_token: ["jsonpath", "$.token"]
        asserts:
            - ["status", "eq", 200]
    ''', 步骤名称: "用户${username}登录"
    
    # 根据角色执行不同的测试
    if role == "admin" do
        [打印], 内容: "执行管理员权限测试"
        # 管理员特有的测试
    elif role == "user" do
        [打印], 内容: "执行普通用户权限测试"
        # 普通用户测试
    else
        [打印], 内容: "执行访客权限测试"
        # 访客测试
    end
end
```

### 3. 错误重试机制

```python
# 实现重试机制
max_retries = 3
retry_count = 0
success = False

for attempt in range(1, ${max_retries} + 1) do
    [打印], 内容: "第 ${attempt} 次尝试"
    
    # 模拟可能失败的操作
    [HTTP请求], 客户端: "default", 配置: '''
        method: GET
        url: /api/unstable-endpoint
        captures:
            response_status: ["status"]
    ''', 步骤名称: "尝试访问不稳定接口"
    
    if ${response_status} == 200 do
        [打印], 内容: "请求成功！"
        success = True
        break
    else
        [打印], 内容: "请求失败，状态码: ${response_status}"
        if ${attempt} < ${max_retries} do
                    [打印], 内容: "等待重试..."
        [等待], 秒数: 2
        end
    end
end

if not ${success} do
    [打印], 内容: "所有重试都失败了"
    [断言], 条件: "False", 消息: "接口请求最终失败"
end
```

### 4. 数据验证循环

```python
# 验证API返回的数据列表
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /api/users
    captures:
        users_data: ["json"]
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "获取用户列表"

# 验证每个用户数据的完整性
required_fields = ["id", "name", "email", "status"]

for user in ${users_data} do
    user_id = user["id"]
    [打印], 内容: "验证用户 ${user_id} 的数据"
    
    for field in ${required_fields} do
        if field in user do
            [打印], 内容: "  ✓ 字段 ${field} 存在"
        else
            [打印], 内容: "  ✗ 字段 ${field} 缺失"
            [断言], 条件: "False", 消息: "用户${user_id}缺少必需字段${field}"
        end
    end
    
    # 验证邮箱格式
    user_email = user["email"]
    if "@" in user_email do
        [打印], 内容: "  ✓ 邮箱格式正确: ${user_email}"
    else
        [打印], 内容: "  ✗ 邮箱格式错误: ${user_email}"
    end
end
```

### 5. 条件测试执行

```python
# 根据配置决定是否执行某些测试
run_performance_tests = False
run_security_tests = True
test_environment = "staging"

[打印], 内容: "开始执行测试套件"

# 基础功能测试（总是执行）
[打印], 内容: "执行基础功能测试"
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /api/health
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "健康检查"

# 性能测试（条件执行）
if ${run_performance_tests} do
    [打印], 内容: "执行性能测试"
    for i in range(1, 101) do
        [HTTP请求], 客户端: "default", 配置: '''
            method: GET
            url: /api/fast-endpoint
            asserts:
                - ["status", "eq", 200]
                - ["response_time", "lt", 100]
        ''', 步骤名称: "性能测试 ${i}"
    end
else
    [打印], 内容: "跳过性能测试"
end

# 安全测试（条件执行）
if ${run_security_tests} and test_environment != "production" do
    [打印], 内容: "执行安全测试"
    
    # SQL注入测试
    malicious_inputs = ["'; DROP TABLE users; --", "1' OR '1'='1", "<script>alert('xss')</script>"]
    
    for payload in ${malicious_inputs} do
        [打印], 内容: "测试恶意输入: ${payload}"
        [HTTP请求], 客户端: "default", 配置: '''
            method: POST
            url: /api/search
            request:
                json:
                    query: "${payload}"
            asserts:
                - ["status", "in", [400, 403]]
        ''', 步骤名称: "安全测试 - 恶意输入"
    end
else
    [打印], 内容: "跳过安全测试"
end
```

## 最佳实践

### 1. 避免过深的嵌套

```python
# 不好的做法：过深嵌套
if condition1 do
    if condition2 do
        if condition3 do
            if condition4 do
                # 代码逻辑
            end
        end
    end
end

# 好的做法：使用早期返回或组合条件
if condition1 and condition2 and condition3 and condition4 do
    # 代码逻辑
end
```

### 2. 使用有意义的变量名

```python
# 不好的做法
for i in range(10) do
    for j in range(5) do
        # 不清楚i和j代表什么
    end
end

# 好的做法
for test_case_index in range(10) do
    for retry_attempt in range(5) do
        # 变量名清晰表达意图
    end
end
```

### 3. 适当使用注释

```python
# 复杂的条件判断应该添加注释
user_score = 85
user_level = "premium"

# 检查用户是否符合高级功能使用条件
if ${user_score} >= 80 and user_level == "premium" do
    [打印], 内容: "用户符合高级功能使用条件"
    enable_advanced_features = True
end
```

### 4. 合理使用循环控制

```python
# 在适当的时候使用break和continue
found_target = False
target_id = 123

for item in ${item_list} do
    item_id = item["id"]
    
    # 跳过无效项目
    if item["status"] != "active" do
        continue
    end
    
    # 找到目标后立即退出
    if ${item_id} == ${target_id} do
        [打印], 内容: "找到目标项目: ${item_id}"
        found_target = True
        break
    end
end

if not ${found_target} do
    [打印], 内容: "未找到目标项目"
end
```

## 常见问题

### 1. 条件表达式错误

```python
# 错误：字符串比较时忘记引号
status = "success"
if status == success do  # 错误：success应该是"success"
    [打印], 内容: "成功"
end

# 正确写法
if status == "success" do
    [打印], 内容: "成功"
end
```

### 2. 循环变量作用域

```python
# 注意：循环变量在循环外仍然可用
for i in range(5) do
    [打印], 内容: "循环中: ${i}"
end

# 循环结束后，i仍然是最后一次的值
[打印], 内容: "循环外: ${i}"  # 输出: 循环外: 4
```

### 3. 无限循环风险

```python
# 避免可能的无限循环
counter = 0
max_iterations = 100

for i in range(${max_iterations}) do
    # 确保有退出条件
    if some_condition do
        break
    end
    
    counter = counter + 1
    if ${counter} >= ${max_iterations} do
        [打印], 内容: "达到最大迭代次数，强制退出"
        break
    end
end
```

## 下一步

现在您已经掌握了pytest-dsl的流程控制，可以继续学习：

1. **[内置关键字](./builtin-keywords)** - 了解框架提供的功能
2. **[自定义关键字](./custom-keywords)** - 创建可复用的测试组件
3. **[HTTP API测试](./http-testing)** - 在API测试中应用流程控制
4. **[数据驱动测试](./data-driven)** - 结合循环实现数据驱动测试 