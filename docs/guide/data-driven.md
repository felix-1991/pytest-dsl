# 数据驱动测试

数据驱动测试是pytest-dsl的核心特性之一，允许您使用外部数据源（如CSV、JSON、Excel等）来驱动测试执行，实现同一测试逻辑在不同数据集上的重复执行。

::: warning 重要提示
**数据驱动测试只有在使用pytest集成方式运行时才会生效！**

使用`pytest-dsl`命令直接运行包含`@data`指令的DSL文件时，数据驱动功能不会工作，测试只会执行一次。
要使用数据驱动功能，必须通过`auto_dsl`装饰器和pytest来运行测试。
:::

## 什么是数据驱动测试

数据驱动测试将测试逻辑与测试数据分离，通过外部数据源提供测试输入和期望结果，使得：

- 同一测试用例可以在多组数据上执行
- 测试数据易于维护和更新
- 非技术人员也能参与测试数据的管理
- 提高测试覆盖率和测试效率

## 基本语法

数据驱动测试需要两个步骤：

### 1. 在DSL文件中使用`@data`指令

```python
@name: "数据驱动测试示例"
@data: "test_data.csv" using csv

# 测试逻辑中可以直接使用数据列名作为变量
[打印], 内容: "测试用户: ${username}, 期望结果: ${expected_result}"
```

### 2. 通过pytest运行（必需步骤）

创建`test_runner.py`：

```python
from pytest_dsl.core.auto_decorator import auto_dsl

@auto_dsl("./tests")  # 指向包含DSL文件的目录
class TestDataDriven:
    """数据驱动测试类"""
    pass
```

运行测试：

```bash
# ✅ 正确方式 - 数据驱动生效
pytest test_runner.py -v

# ❌ 错误方式 - 数据驱动不生效，只执行一次
pytest-dsl tests/data_driven_test.dsl
```

## 支持的数据格式

### CSV数据源

CSV是最常用的数据驱动格式，适合表格化数据。

**数据文件：** `user_test_data.csv`
```csv
username,password,expected_status,expected_message
admin,admin123,200,登录成功
user1,password123,200,登录成功
guest,guest123,403,权限不足
invalid_user,wrong_pass,401,用户名或密码错误
```

**测试文件：** `test_login.dsl`
```python
@name: "用户登录数据驱动测试"
@description: "使用CSV数据测试不同用户的登录场景"
@data: "user_test_data.csv" using csv

[打印], 内容: "测试用户登录: ${username}"

# 执行登录操作
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: /api/auth/login
    request:
        json:
            username: "${username}"
            password: "${password}"
    captures:
        actual_status: ["status"]
        actual_message: ["jsonpath", "$.message"]
    asserts:
        - ["status", "eq", ${expected_status}]
        - ["jsonpath", "$.message", "eq", "${expected_message}"]
'''

[打印], 内容: "用户 ${username} 测试完成"
```

### JSON数据源

JSON格式适合复杂的嵌套数据结构。

**数据文件：** `api_test_data.json`
```json
[
    {
        "test_name": "创建新用户",
        "user_data": {
            "username": "newuser1",
            "email": "newuser1@example.com",
            "profile": {
                "firstName": "张",
                "lastName": "三",
                "age": 25
            }
        },
        "expected_status": 201,
        "expected_fields": ["id", "username", "email"]
    },
    {
        "test_name": "创建重复用户",
        "user_data": {
            "username": "admin",
            "email": "admin@example.com",
            "profile": {
                "firstName": "管理",
                "lastName": "员",
                "age": 30
            }
        },
        "expected_status": 409,
        "expected_fields": ["error", "message"]
    }
]
```

**测试文件：** `test_user_creation.dsl`
```python
@name: "用户创建API数据驱动测试"
@data: "api_test_data.json" using json

[打印], 内容: "执行测试: ${test_name}"

# 发送创建用户请求
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: /api/users
    request:
        json: ${user_data}
    captures:
        response_data: ["json"]
    asserts:
        - ["status", "eq", ${expected_status}]
'''

# 验证响应字段
for field in ${expected_fields} do
    [断言], 条件: "'${field}' in response_data", 消息: "响应中应包含字段: ${field}"
end

[打印], 内容: "测试 '${test_name}' 完成"
```

### Excel数据源

Excel格式适合大量数据和复杂的数据组织。

**数据文件：** `comprehensive_test_data.xlsx`

工作表：`LoginTests`
| username | password | user_type | expected_status | expected_role | notes |
|----------|----------|-----------|-----------------|---------------|--------|
| admin | admin123 | admin | 200 | administrator | 管理员账户 |
| manager | manager123 | manager | 200 | manager | 经理账户 |
| employee | emp123 | employee | 200 | employee | 普通员工 |
| disabled_user | password | disabled | 403 | none | 已禁用账户 |

**测试文件：** `test_comprehensive_login.dsl`
```python
@name: "综合登录测试"
@data: "comprehensive_test_data.xlsx:LoginTests" using excel

[打印], 内容: "测试${user_type}用户登录: ${username}"

# 登录请求
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: /api/auth/login
    request:
        json:
            username: "${username}"
            password: "${password}"
    captures:
        status_code: ["status"]
        user_role: ["jsonpath", "$.user.role"]
    asserts:
        - ["status", "eq", ${expected_status}]
'''

# 条件验证
if ${expected_status} == 200 do
    [断言], 条件: "'${user_role}' == '${expected_role}'", 消息: "用户角色应为: ${expected_role}"
    [打印], 内容: "✓ ${username} 登录成功，角色: ${user_role}"
else
    [打印], 内容: "✓ ${username} 登录失败，符合预期"
end

# 显示测试备注
if "${notes}" != "" do
    [打印], 内容: "备注: ${notes}"
end
```

## 高级数据驱动功能

### 多数据源组合

可以在同一测试中使用多个数据源：

```python
@name: "多数据源测试"
@data: "users.csv" using csv
@data: "scenarios.json" using json

# 使用CSV中的用户数据和JSON中的场景数据
[打印], 内容: "用户: ${username}, 场景: ${scenario_name}"

# 根据场景类型执行不同的测试逻辑
if "${scenario_type}" == "api" do
    [HTTP请求], 客户端: "default", 配置: '''
        method: ${http_method}
        url: ${api_endpoint}
        request:
            json:
                username: "${username}"
                data: ${scenario_data}
    '''
elif "${scenario_type}" == "ui" do
    [打印], 内容: "执行UI测试场景"
    # UI测试逻辑
end
```

### 条件数据过滤

可以基于条件过滤数据行：

**数据文件：** `filtered_test_data.csv`
```csv
username,password,environment,enabled,test_type
admin,admin123,dev,True,smoke
user1,pass123,dev,True,regression
user2,pass456,prod,True,smoke
user3,pass789,dev,False,regression
manager,mgr123,staging,True,integration
```

**测试文件：** `test_filtered.dsl`
```python
@name: "条件过滤数据驱动测试"
@data: "filtered_test_data.csv" using csv

# 只测试开发环境且启用的用户
if "${environment}" == "dev" and ${enabled} == True do
    [打印], 内容: "测试用户: ${username} (${test_type})"
    
    # 执行测试逻辑
    [HTTP请求], 客户端: "default", 配置: '''
        method: POST
        url: /api/login
        request:
            json:
                username: "${username}"
                password: "${password}"
        asserts:
            - ["status", "eq", 200]
    '''
else
    [打印], 内容: "跳过用户: ${username} (环境: ${environment}, 启用: ${enabled})"
end
```

### 参数化资源文件

结合资源文件实现更灵活的数据驱动测试：

**资源文件：** `data_driven_utils.resource`
```python
@name: "数据驱动测试工具"

function 执行用户操作 (操作类型, 用户数据, 期望结果) do
    [打印], 内容: "执行操作: ${操作类型}"
    
    if "${操作类型}" == "create" do
        [HTTP请求], 客户端: "default", 配置: '''
            method: POST
            url: /api/users
            request:
                json: ${用户数据}
            asserts:
                - ["status", "eq", ${期望结果.status_code}]
        '''
    elif "${操作类型}" == "update" do
        [HTTP请求], 客户端: "default", 配置: '''
            method: PUT
            url: /api/users/${用户数据.id}
            request:
                json: ${用户数据}
            asserts:
                - ["status", "eq", ${期望结果.status_code}]
        '''
    elif "${操作类型}" == "delete" do
        [HTTP请求], 客户端: "default", 配置: '''
            method: DELETE
            url: /api/users/${用户数据.id}
            asserts:
                - ["status", "eq", ${期望结果.status_code}]
        '''
    end
    
    [打印], 内容: "操作 ${操作类型} 完成"
end

function 验证响应数据 (实际数据, 期望数据) do
    for key in ${期望数据} do
        if ${key} in ${实际数据} do
            [断言], 条件: "${实际数据[key]} == ${期望数据[key]}", 消息: "字段 ${key} 值不匹配"
        else
            [打印], 内容: "警告: 响应中缺少字段 ${key}"
        end
    end
end
```

**测试文件：** `test_parameterized.dsl`
```python
@name: "参数化数据驱动测试"
@import: "data_driven_utils.resource"
@data: "user_operations.json" using json

# 使用资源文件中的关键字处理数据
[执行用户操作], 操作类型: ${operation}, 用户数据: ${user_data}, 期望结果: ${expected}

# 如果有响应验证数据，进行验证
if "response_validation" in locals() and ${response_validation} != null do
    [验证响应数据], 实际数据: ${captured_response}, 期望数据: ${response_validation}
end
```

## 动态数据生成

### 使用自定义关键字生成测试数据

```python
@name: "动态数据生成测试"

# 定义数据生成关键字
function 生成测试用户 (用户类型, 序号) do
    基础数据 = {
        "username": "${用户类型}_user_${序号}",
        "email": "${用户类型}_user_${序号}@example.com",
        "type": "${用户类型}"
    }
    
    # 根据用户类型设置不同属性
    if "${用户类型}" == "admin" do
        基础数据["permissions"] = ["read", "write", "admin"]
        基础数据["department"] = "IT"
    elif "${用户类型}" == "manager" do
        基础数据["permissions"] = ["read", "write"]
        基础数据["department"] = "Sales"
    else
        基础数据["permissions"] = ["read"]
        基础数据["department"] = "General"
    end
    
    return ${基础数据}
end

# 生成不同类型的用户进行测试
用户类型列表 = ["admin", "manager", "employee"]

for 用户类型 in ${用户类型列表} do
    for 序号 in range(1, 4) do
        测试用户 = [生成测试用户], 用户类型: ${用户类型}, 序号: ${序号}
        
        [打印], 内容: "创建测试用户: ${测试用户.username}"
        
        [HTTP请求], 客户端: "default", 配置: '''
            method: POST
            url: /api/users
            request:
                json: ${测试用户}
            captures:
                created_user_id: ["jsonpath", "$.id"]
            asserts:
                - ["status", "eq", 201]
                - ["jsonpath", "$.username", "eq", "${测试用户.username}"]
        '''
        
        [打印], 内容: "用户创建成功，ID: ${created_user_id}"
    end
end
```

### 时间序列数据测试

```python
@name: "时间序列数据测试"

# 生成一周的日期数据
function 生成日期范围 (开始日期, 天数) do
    日期列表 = []
    
    for i in range(0, ${天数}) do
        # 这里简化处理，实际应该使用日期库
        当前日期 = "${开始日期}_day_${i}"
        日期列表.append(${当前日期})
    end
    
    return ${日期列表}
end

# 测试一周内每天的数据
开始日期 = "2024-01-01"
测试天数 = 7
日期列表 = [生成日期范围], 开始日期: ${开始日期}, 天数: ${测试天数}

for 测试日期 in ${日期列表} do
    [打印], 内容: "测试日期: ${测试日期}"
    
    # 获取该日期的数据
    [HTTP请求], 客户端: "default", 配置: '''
        method: GET
        url: /api/reports/daily
        request:
            params:
                date: "${测试日期}"
        captures:
            daily_data: ["jsonpath", "$.data"]
        asserts:
            - ["status", "eq", 200]
            - ["jsonpath", "$.data", "not_empty"]
    '''
    
    # 验证数据完整性 - 注意：len() 函数调用不支持
    # [断言], 条件: "len(daily_data) > 0", 消息: "日报数据不应为空"  # 不支持
    [断言], 条件: "${daily_data} != []", 消息: "日报数据不应为空"
    [打印], 内容: "✓ ${测试日期} 数据验证通过"
end
```

## 数据驱动测试的最佳实践

### 1. 数据文件组织

```
data/
├── users/
│   ├── admin_users.csv
│   ├── regular_users.csv
│   └── guest_users.csv
├── scenarios/
│   ├── login_scenarios.json
│   ├── api_scenarios.json
│   └── error_scenarios.json
├── configurations/
│   ├── dev_config.xlsx
│   ├── test_config.xlsx
│   └── prod_config.xlsx
└── fixtures/
    ├── sample_data.json
    └── reference_data.csv
```

### 2. 数据文件命名规范

- 使用描述性名称：`user_registration_test_data.csv`
- 包含环境信息：`api_test_data_dev.json`
- 版本控制：`test_data_v2.1.xlsx`
- 分类组织：`auth/login_test_data.csv`

### 3. 数据质量保证

**验证数据文件：** `validate_data.dsl`
```python
@name: "数据文件验证"
@data: "user_test_data.csv" using csv

# 验证必需字段
必需字段 = ["username", "password", "expected_status"]

for 字段 in ${必需字段} do
    [断言], 条件: "'${字段}' in locals()", 消息: "数据文件缺少必需字段: ${字段}"
end

# 验证数据格式
[断言], 条件: "isinstance(${expected_status}, int)", 消息: "expected_status应为整数"
[断言], 条件: "${expected_status} >= 200 and ${expected_status} < 600", 消息: "状态码应在200-599范围内"

# 验证用户名格式 - 注意：len() 函数调用不支持
# [断言], 条件: "len('${username}') >= 3", 消息: "用户名长度应至少3个字符"  # 不支持
# 可以使用字符串比较或其他方式验证
[断言], 条件: "'${username}' != '' and '${username}' != 'ab'", 消息: "用户名长度应至少3个字符"

[打印], 内容: "✓ 数据行验证通过: ${username}"
```

### 4. 错误处理和跳过策略

```python
@name: "健壮的数据驱动测试"
@data: "user_test_data.csv" using csv

# 数据有效性检查
if "${username}" == "" do
    [打印], 内容: "跳过空用户名的数据行"
    continue
end

if ${expected_status} not in [200, 201, 400, 401, 403, 404, 500] do
    [打印], 内容: "跳过无效状态码的数据行: ${expected_status}"
    continue
end

# 执行测试逻辑
[打印], 内容: "测试用户: ${username}"

try
    [HTTP请求], 客户端: "default", 配置: '''
        method: POST
        url: /api/auth/login
        request:
            json:
                username: "${username}"
                password: "${password}"
        asserts:
            - ["status", "eq", ${expected_status}]
    '''
    [打印], 内容: "✓ 测试通过"
except Exception as e
    [打印], 内容: "✗ 测试失败: ${str(e)}"
    # 根据需要决定是否继续
end
```

### 5. 性能优化

```python
@name: "优化的数据驱动测试"
@data: "large_test_data.csv" using csv

# 批量处理优化
批次大小 = 10
当前批次 = []

# 收集批次数据
当前批次.append({
    "username": "${username}",
    "password": "${password}",
    "expected": ${expected_status}
})

# 当批次满时或到达末尾时处理 - 注意：len() 函数调用不支持
# if len(${当前批次}) >= ${批次大小} do  # 不支持
# 需要手动计数或使用其他方式
批次计数 = 批次计数 + 1
if ${批次计数} >= ${批次大小} do
    [处理用户批次], 用户列表: ${当前批次}
    当前批次 = []  # 清空批次
end
```

## 复杂场景示例

### 端到端电商测试流程

**数据文件：** `ecommerce_flow_data.json`
```json
[
    {
        "test_scenario": "完整购买流程",
        "user": {
            "username": "buyer1",
            "password": "password123"
        },
        "products": [
            {"id": "PROD-001", "quantity": 2},
            {"id": "PROD-002", "quantity": 1}
        ],
        "payment": {
            "method": "credit_card",
            "card_number": "4111111111111111"
        },
        "shipping": {
            "address": "123 Main St",
            "city": "Beijing",
            "zip": "100000"
        },
        "expected_total": 299.98
    }
]
```

**测试文件：** `test_ecommerce_flow.dsl`
```python
@name: "电商端到端流程测试"
@import: "ecommerce_utils.resource"
@data: "ecommerce_flow_data.json" using json

[打印], 内容: "开始测试场景: ${test_scenario}"

# 1. 用户登录
token = [用户登录], 用户名: ${user.username}, 密码: ${user.password}

# 2. 添加商品到购物车
购物车ID = null
for 商品 in ${products} do
    购物车ID = [添加到购物车], 商品ID: ${商品.id}, 数量: ${商品.quantity}, token: ${token}
end

# 3. 计算订单总额
订单详情 = [获取购物车详情], 购物车ID: ${购物车ID}, token: ${token}
[断言], 条件: "${订单详情.total} == ${expected_total}", 消息: "订单总额不符合预期"

# 4. 创建订单
订单ID = [创建订单], 购物车ID: ${购物车ID}, 配送信息: ${shipping}, token: ${token}

# 5. 处理支付
支付结果 = [处理支付], 订单ID: ${订单ID}, 支付方式: ${payment}, token: ${token}
[断言], 条件: "${支付结果.status} == 'success'", 消息: "支付应该成功"

# 6. 验证订单状态
最终订单状态 = [获取订单状态], 订单ID: ${订单ID}, token: ${token}
[断言], 条件: "${最终订单状态} == 'confirmed'", 消息: "订单状态应为已确认"

[打印], 内容: "✓ 场景 '${test_scenario}' 测试完成"
```

## 数据驱动测试的报告和分析

```python
@name: "数据驱动测试结果统计"
@data: "comprehensive_test_data.csv" using csv

# 初始化统计变量
总测试数 = 0
成功测试数 = 0
失败测试数 = 0
测试结果列表 = []

# 执行测试并收集结果
[打印], 内容: "执行测试: ${test_name}"
总测试数 = ${总测试数} + 1

# 执行实际测试逻辑
测试结果 = [执行测试逻辑], 测试数据: ${test_data}

if ${测试结果.success} do
    成功测试数 = ${成功测试数} + 1
    结果状态 = "PASS"
else
    失败测试数 = ${失败测试数} + 1
    结果状态 = "FAIL"
end

# 记录测试结果
测试记录 = {
    "name": "${test_name}",
    "status": "${结果状态}",
    "duration": ${测试结果.duration},
    "details": "${测试结果.message}"
}
测试结果列表.append(${测试记录})

# 在所有测试完成后输出统计信息
teardown do
    [打印], 内容: "=== 测试统计 ==="
    [打印], 内容: "总测试数: ${总测试数}"
    [打印], 内容: "成功: ${成功测试数}"
    [打印], 内容: "失败: ${失败测试数}"
    
    成功率 = (${成功测试数} / ${总测试数}) * 100
    [打印], 内容: "成功率: ${成功率}%"
    
    [打印], 内容: "详细结果:"
    for 结果 in ${测试结果列表} do
        [打印], 内容: "  ${结果.name}: ${结果.status} (${结果.duration}ms)"
    end
end
```

## 下一步

- 学习[环境配置管理](./configuration)了解如何为不同环境配置数据源
- 查看[测试报告](./reporting)了解如何生成数据驱动测试的详细报告
- 阅读[最佳实践](./best-practices)了解大规模数据驱动测试的组织方法 