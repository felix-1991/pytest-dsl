# 第一个测试

恭喜您完成了pytest-dsl的安装和配置！现在让我们创建第一个真正的测试用例，体验pytest-dsl的强大功能。

## 学习目标

通过本章学习，您将：

- 创建一个完整的API测试用例
- 学会使用变量和数据捕获
- 掌握基本的断言验证
- 了解测试的组织结构
- 学会调试和排错

## 测试场景

我们将创建一个用户管理API的测试场景，包括：

1. 获取用户列表
2. 获取单个用户详情
3. 验证用户数据的完整性
4. 测试错误处理

## 创建测试文件

### 1. 基础测试结构

创建`tests/user_api_test.dsl`：

```python
@name: "用户API测试"
@description: "测试用户管理相关的API接口"
@tags: ["api", "user", "smoke"]

# 测试开始提示
[打印], 内容: "开始执行用户API测试..."

# 定义测试数据
api_base = "https://jsonplaceholder.typicode.com"
test_user_id = 1
expected_user_name = "Leanne Graham"

[打印], 内容: "测试配置 - API地址: ${api_base}, 用户ID: ${test_user_id}"
```

### 2. 获取用户列表测试

```python
# ========== 测试1: 获取用户列表 ==========
[打印], 内容: "测试1: 获取用户列表"

[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: ${api_base}/users
    captures:
        users_count: ["jsonpath", "$", "length"]
        first_user_id: ["jsonpath", "$[0].id"]
        first_user_name: ["jsonpath", "$[0].name"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$", "length", "gt", 0]
        - ["jsonpath", "$[0].id", "exists"]
        - ["jsonpath", "$[0].name", "exists"]
        - ["jsonpath", "$[0].email", "exists"]
''', 步骤名称: "获取用户列表"

# 验证捕获的数据
[打印], 内容: "用户总数: ${users_count}"
[打印], 内容: "第一个用户: ID=${first_user_id}, 姓名=${first_user_name}"

# 断言验证
[断言], 条件: "${users_count} >= 10", 消息: "用户数量应该大于等于10"
[断言], 条件: "${first_user_id} == 1", 消息: "第一个用户ID应该是1"

[打印], 内容: "✓ 测试1通过: 用户列表获取成功"
```

### 3. 获取单个用户详情测试

```python
# ========== 测试2: 获取单个用户详情 ==========
[打印], 内容: "测试2: 获取用户详情"

[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: ${api_base}/users/${test_user_id}
    captures:
        user_id: ["jsonpath", "$.id"]
        user_name: ["jsonpath", "$.name"]
        user_email: ["jsonpath", "$.email"]
        user_phone: ["jsonpath", "$.phone"]
        user_website: ["jsonpath", "$.website"]
        address_city: ["jsonpath", "$.address.city"]
        company_name: ["jsonpath", "$.company.name"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.id", "eq", ${test_user_id}]
        - ["jsonpath", "$.name", "eq", "${expected_user_name}"]
        - ["jsonpath", "$.email", "contains", "@"]
        - ["jsonpath", "$.address", "exists"]
        - ["jsonpath", "$.company", "exists"]
''', 步骤名称: "获取用户详情"

# 打印用户信息
[打印], 内容: "用户详情:"
[打印], 内容: "  ID: ${user_id}"
[打印], 内容: "  姓名: ${user_name}"
[打印], 内容: "  邮箱: ${user_email}"
[打印], 内容: "  电话: ${user_phone}"
[打印], 内容: "  网站: ${user_website}"
[打印], 内容: "  城市: ${address_city}"
[打印], 内容: "  公司: ${company_name}"

# 数据完整性验证
[断言], 条件: '${user_name} == "${expected_user_name}"', 消息: "用户名不匹配"
[断言], 条件: '"@" in "${user_email}"', 消息: "邮箱格式不正确"
[断言], 条件: 'len("${user_phone}") > 0', 消息: "电话号码不能为空"

[打印], 内容: "✓ 测试2通过: 用户详情获取成功"
```

### 4. 错误处理测试

```python
# ========== 测试3: 错误处理测试 ==========
[打印], 内容: "测试3: 错误处理"

# 测试不存在的用户
invalid_user_id = 999999

[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: ${api_base}/users/${invalid_user_id}
    asserts:
        - ["status", "eq", 404]
''', 步骤名称: "测试不存在的用户"

[打印], 内容: "✓ 测试3通过: 错误处理正确"
```

### 5. 数据关联测试

```python
# ========== 测试4: 数据关联测试 ==========
[打印], 内容: "测试4: 数据关联测试"

# 获取用户的文章
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: ${api_base}/users/${test_user_id}/posts
    captures:
        posts_count: ["jsonpath", "$", "length"]
        first_post_title: ["jsonpath", "$[0].title"]
        first_post_user_id: ["jsonpath", "$[0].userId"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$", "length", "gt", 0]
        - ["jsonpath", "$[0].userId", "eq", ${test_user_id}]
''', 步骤名称: "获取用户文章"

[打印], 内容: "用户${user_name}的文章数量: ${posts_count}"
[打印], 内容: "第一篇文章标题: ${first_post_title}"

# 验证数据关联
[断言], 条件: "${first_post_user_id} == ${test_user_id}", 消息: "文章用户ID应该匹配"
[断言], 条件: "${posts_count} > 0", 消息: "用户应该有文章"

[打印], 内容: "✓ 测试4通过: 数据关联正确"
```

### 6. 测试清理

```python
# ========== 测试总结 ==========
[打印], 内容: "所有测试执行完成！"
[打印], 内容: "测试结果总结:"
[打印], 内容: "  ✓ 用户列表获取: 通过"
[打印], 内容: "  ✓ 用户详情获取: 通过"
[打印], 内容: "  ✓ 错误处理: 通过"
[打印], 内容: "  ✓ 数据关联: 通过"

# 使用teardown确保清理工作
teardown do
    [打印], 内容: "执行测试清理工作..."
    [打印], 内容: "测试环境已清理完成"
end
```

## 运行测试

### 基本运行

```bash
# 运行测试
pytest-dsl tests/user_api_test.dsl

# 带详细输出
pytest-dsl tests/user_api_test.dsl -v

# 带配置文件运行
pytest-dsl tests/user_api_test.dsl --yaml-vars config/dev.yaml
```

### 预期输出

运行成功后，您应该看到类似的输出：

```
开始执行用户API测试...
测试配置 - API地址: https://jsonplaceholder.typicode.com, 用户ID: 1

测试1: 获取用户列表
✓ HTTP请求: 获取用户列表 (200 OK)
用户总数: 10
第一个用户: ID=1, 姓名=Leanne Graham
✓ 测试1通过: 用户列表获取成功

测试2: 获取用户详情
✓ HTTP请求: 获取用户详情 (200 OK)
用户详情:
  ID: 1
  姓名: Leanne Graham
  邮箱: Sincere@april.biz
  电话: 1-770-736-8031 x56442
  网站: hildegard.org
  城市: Gwenborough
  公司: Romaguera-Crona
✓ 测试2通过: 用户详情获取成功

测试3: 错误处理
✓ HTTP请求: 测试不存在的用户 (404 Not Found)
✓ 测试3通过: 错误处理正确

测试4: 数据关联测试
✓ HTTP请求: 获取用户文章 (200 OK)
用户Leanne Graham的文章数量: 10
第一篇文章标题: sunt aut facere repellat provident occaecati excepturi optio reprehenderit
✓ 测试4通过: 数据关联正确

所有测试执行完成！
测试结果总结:
  ✓ 用户列表获取: 通过
  ✓ 用户详情获取: 通过
  ✓ 错误处理: 通过
  ✓ 数据关联: 通过

执行测试清理工作...
测试环境已清理完成

==================== 1 passed in 2.34s ====================
```

## 测试优化

### 1. 使用配置文件

创建`config/api_test.yaml`：

```yaml
# API测试配置
api:
  base_url: "https://jsonplaceholder.typicode.com"
  timeout: 30

# HTTP客户端配置
http_clients:
  default:
    base_url: "${api.base_url}"
    timeout: ${api.timeout}
    headers:
      Content-Type: "application/json"
      User-Agent: "pytest-dsl-test/1.0"

# 测试数据
test_data:
  users:
    valid_user_id: 1
    invalid_user_id: 999999
    expected_user_name: "Leanne Graham"
  
  validation:
    min_users_count: 10
    required_fields: ["id", "name", "email", "phone", "website"]
```

### 2. 优化后的测试文件

```python
@name: "用户API测试 - 优化版"
@description: "使用配置文件的用户API测试"

# 使用配置文件中的数据
test_user_id = ${test_data.users.valid_user_id}
expected_user_name = ${test_data.users.expected_user_name}
min_users = ${test_data.validation.min_users_count}

[打印], 内容: "开始执行用户API测试（优化版）..."

# 获取用户列表
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /users
    captures:
        users_count: ["jsonpath", "$", "length"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$", "length", "gte", ${min_users}]
''', 步骤名称: "获取用户列表"

[断言], 条件: "${users_count} >= ${min_users}", 消息: "用户数量不足"
[打印], 内容: "✓ 用户列表测试通过，共${users_count}个用户"
```

### 3. 使用资源文件

创建`resources/user_api.resource`：

```python
@name: "用户API测试资源"
@description: "用户API测试的通用关键字"

function 获取用户信息 (用户ID=1) do
    [HTTP请求], 客户端: "default", 配置: '''
        method: GET
        url: /users/${用户ID}
        captures:
            user_data: ["json"]
        asserts:
            - ["status", "eq", 200]
            - ["jsonpath", "$.id", "eq", ${用户ID}]
    ''', 步骤名称: "获取用户${用户ID}的信息"
    
    return ${user_data}
end

function 验证用户数据完整性 (用户数据) do
    必需字段 = ["id", "name", "email", "phone", "website", "address", "company"]
    
    for 字段 in ${必需字段} do
        [断言], 条件: '"${字段}" in ${用户数据}', 消息: "缺少必需字段: ${字段}"
    end
    
    [打印], 内容: "✓ 用户数据完整性验证通过"
end
```

## 调试技巧

### 1. 添加调试信息

```python
# 开启调试模式
debug_mode = True

if ${debug_mode} do
    [打印], 内容: "调试信息: 当前测试用户ID = ${test_user_id}"
    [打印], 内容: "调试信息: API基础地址 = ${api_base}"
end
```

### 2. 条件执行

```python
# 根据环境执行不同的测试
environment = "development"

if ${environment} == "development" do
    [打印], 内容: "开发环境: 执行完整测试"
    # 执行所有测试
else
    [打印], 内容: "生产环境: 执行基础测试"
    # 只执行基础测试
end
```

### 3. 错误处理

```python
# 使用try-catch处理可能的错误
try do
    [HTTP请求], 客户端: "default", 配置: '''
        method: GET
        url: /users/invalid
    '''
catch error do
    [打印], 内容: "预期的错误: ${error}"
end
```

## 常见问题

### 1. 网络连接问题

```python
# 增加重试机制
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /users
    timeout: 60
    retries: 3
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "获取用户列表（带重试）"
```

### 2. 数据验证失败

```python
# 更详细的断言消息
[断言], 条件: "${user_id} == ${test_user_id}", 
    消息: "用户ID不匹配: 期望=${test_user_id}, 实际=${user_id}"
```

### 3. JSON路径错误

```python
# 验证JSON结构
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /users/1
    captures:
        response_text: ["text"]
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "获取响应"

[打印], 内容: "响应内容: ${response_text}"
```

## 下一步

恭喜！您已经成功创建并运行了第一个完整的pytest-dsl测试。现在您可以：

1. **[学习DSL语法](./dsl-syntax)** - 深入了解更多语法特性
2. **[掌握变量使用](./variables)** - 学习变量和数据类型
3. **[探索HTTP测试](./http-testing)** - 学习更高级的API测试技巧
4. **[创建自定义关键字](./custom-keywords)** - 提高测试代码的复用性

继续您的pytest-dsl学习之旅吧！ 