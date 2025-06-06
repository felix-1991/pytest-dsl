# 自定义关键字

自定义关键字是pytest-dsl最强大的功能之一，它允许您将常用的测试逻辑封装成可复用的组件，提高测试代码的可读性和维护性。

## 什么是自定义关键字

自定义关键字是用户定义的可重用测试步骤，类似于编程语言中的函数。它们可以：

- 封装复杂的测试逻辑
- 提高代码复用性
- 增强测试用例的可读性
- 简化复杂操作的调用

## 定义自定义关键字

### 基本语法

在DSL文件中使用`function`关键字定义自定义关键字：

```python
function 关键字名称 (参数1, 参数2="默认值") do
    # 关键字实现
    [内置关键字], 参数: ${参数1}
    return ${结果}
end
```

### 简单示例

```python
@name: "自定义关键字基础示例"

# 定义一个简单的问候关键字
function 问候 (姓名, 前缀="你好") do
    消息 = "${前缀}, ${姓名}!"
    [打印], 内容: ${消息}
    return ${消息}
end

# 使用自定义关键字
结果1 = [问候], 姓名: "张三"
结果2 = [问候], 姓名: "李四", 前缀: "欢迎"

[打印], 内容: "第一次问候: ${结果1}"
[打印], 内容: "第二次问候: ${结果2}"
```

## 参数系统

### 必需参数和可选参数

```python
function 计算器 (操作, 数字1, 数字2=0, 精度=2) do
    if ${操作} == "加法" do
        结果 = ${数字1} + ${数字2}
    elif ${操作} == "减法" do
        结果 = ${数字1} - ${数字2}
    elif ${操作} == "乘法" do
        结果 = ${数字1} * ${数字2}
    elif ${操作} == "除法" do
        if ${数字2} == 0 do
            [打印], 内容: "错误：除数不能为0"
            return "错误"
        end
        结果 = ${数字1} / ${数字2}
    else
        [打印], 内容: "不支持的操作: ${操作}"
        return "不支持"
    end

    # 格式化结果精度
    格式化结果 = round(${结果}, ${精度})
    [打印], 内容: "${数字1} ${操作} ${数字2} = ${格式化结果}"
    
    return ${格式化结果}
end

# 使用示例
sum_result = [计算器], 操作: "加法", 数字1: 10, 数字2: 5
div_result = [计算器], 操作: "除法", 数字1: 10, 数字2: 3, 精度: 4
```

### 参数传递规则

1. **按名称传递**：推荐方式，清晰明确
   ```python
   [关键字名], 参数1: 值1, 参数2: 值2
   ```

2. **默认值处理**：未传递的参数使用默认值
   ```python
   function 示例 (必需参数, 可选参数="默认值") do
       [打印], 内容: "${必需参数} - ${可选参数}"
   end
   
   [示例], 必需参数: "测试"  # 可选参数使用默认值
   ```

3. **参数验证**：关键字可以验证参数的有效性
   ```python
   function 验证邮箱 (邮箱地址) do
       if "${邮箱地址}" == "" do
           [打印], 内容: "邮箱地址不能为空"
           return False
       end
       
       # 简单的邮箱格式验证
       if "@" not in "${邮箱地址}" do
           [打印], 内容: "邮箱格式无效"
           return False
       end
       
       [打印], 内容: "邮箱验证通过: ${邮箱地址}"
       return True
   end
   ```

## 返回值和变量作用域

### 返回值

自定义关键字可以返回单个值：

```python
function 生成随机数 (最小值=1, 最大值=100) do
    # 使用时间戳生成简单的随机数
    import time
    随机值 = (time.time() * 1000) % (${最大值} - ${最小值} + 1) + ${最小值}
    随机整数 = int(${随机值})
    
    [打印], 内容: "生成随机数: ${随机整数}"
    return ${随机整数}
end

# 使用返回值
number1 = [生成随机数], 最小值: 1, 最大值: 10
number2 = [生成随机数], 最小值: 50, 最大值: 100

[打印], 内容: "第一个随机数: ${number1}"
[打印], 内容: "第二个随机数: ${number2}"
```

### 变量作用域

- **局部变量**：在关键字内部定义的变量只在该关键字内有效
- **参数变量**：传入的参数在关键字内部可直接使用
- **全局变量**：可以通过特殊方式访问全局变量

```python
# 全局变量
global_counter = 0

function 增加计数器 (增量=1) do
    # 访问全局变量（需要特殊处理）
    new_value = ${global_counter} + ${增量}
    
    # 更新全局变量
    [设置全局变量], 变量名: "global_counter", 值: ${new_value}
    
    [打印], 内容: "计数器值: ${new_value}"
    return ${new_value}
end
```

## 流程控制在自定义关键字中的应用

### 条件分支

```python
function 处理HTTP状态码 (状态码, 期望状态="成功") do
    if ${状态码} >= 200 and ${状态码} < 300 do
        状态描述 = "成功"
        颜色 = "绿色"
    elif ${状态码} >= 300 and ${状态码} < 400 do
        状态描述 = "重定向"
        颜色 = "黄色"
    elif ${状态码} >= 400 and ${状态码} < 500 do
        状态描述 = "客户端错误"
        颜色 = "红色"
    elif ${状态码} >= 500 do
        状态描述 = "服务器错误"
        颜色 = "红色"
    else
        状态描述 = "未知状态"
        颜色 = "灰色"
    end

    [打印], 内容: "HTTP ${状态码}: ${状态描述} [${颜色}]"
    
    # 检查是否符合期望
    if ${期望状态} == "成功" and ${状态码} >= 200 and ${状态码} < 300 do
        return True
    elif ${期望状态} == "错误" and ${状态码} >= 400 do
        return True
    else
        return False
    end
end
```

### 循环处理

```python
function 批量验证URL (URL列表) do
    成功计数 = 0
    失败计数 = 0
    结果列表 = []

    for url in ${URL列表} do
        [打印], 内容: "正在验证: ${url}"
        
        # 简单的URL格式验证
        if "http" in "${url}" do
            验证结果 = "通过"
            成功计数 = ${成功计数} + 1
        else
            验证结果 = "失败"
            失败计数 = ${失败计数} + 1
        end
        
        结果项 = {"url": "${url}", "result": "${验证结果}"}
        结果列表.append(${结果项})
    end

    [打印], 内容: "验证完成 - 成功: ${成功计数}, 失败: ${失败计数}"
    
    总结果 = {
        "success_count": ${成功计数},
        "fail_count": ${失败计数},
        "results": ${结果列表}
    }
    
    return ${总结果}
end

# 使用示例
网址列表 = [
    "https://example.com",
    "https://test.com",
    "invalid-url",
    "https://api.example.com"
]

验证结果 = [批量验证URL], URL列表: ${网址列表}
[打印], 内容: "最终结果: ${验证结果}"
```

## 实际应用场景

### 场景1：API测试封装

```python
function 登录并获取Token (用户名, 密码, 服务器="default") do
    [打印], 内容: "正在登录用户: ${用户名}"
    
    # 发送登录请求
    [HTTP请求], 客户端: ${服务器}, 配置: '''
        method: POST
        url: /api/auth/login
        request:
            json:
                username: "${用户名}"
                password: "${密码}"
        captures:
            token: ["jsonpath", "$.access_token"]
            user_id: ["jsonpath", "$.user_id"]
        asserts:
            - ["status", "eq", 200]
            - ["jsonpath", "$.access_token", "not_empty"]
    '''
    
    [打印], 内容: "登录成功，用户ID: ${user_id}"
    
    # 返回token以供后续使用
    return ${token}
end

function API调用 (接口路径, 方法="GET", token="", 数据=null) do
    # 构建请求头
    请求头 = {}
    if "${token}" != "" do
        请求头["Authorization"] = "Bearer ${token}"
    end

    # 根据方法类型构建请求
    if "${方法}" == "GET" do
        [HTTP请求], 客户端: "default", 配置: '''
            method: GET
            url: "${接口路径}"
            request:
                headers: ${请求头}
            asserts:
                - ["status", "lt", 400]
        '''
    else
        [HTTP请求], 客户端: "default", 配置: '''
            method: "${方法}"
            url: "${接口路径}"
            request:
                headers: ${请求头}
                json: ${数据}
            asserts:
                - ["status", "lt", 400]
        '''
    end
    
    [打印], 内容: "${方法} ${接口路径} 调用成功"
end

# 使用组合关键字
token = [登录并获取Token], 用户名: "admin", 密码: "admin123"
[API调用], 接口路径: "/api/users", token: ${token}
[API调用], 接口路径: "/api/orders", 方法: "POST", token: ${token}, 数据: {"product_id": "123"}
```

### 场景2：数据处理和验证

```python
function 处理用户数据 (用户信息) do
    # 验证必需字段
    必需字段 = ["name", "email", "age"]
    
    for field in ${必需字段} do
        if ${field} not in ${用户信息} do
            [打印], 内容: "缺少必需字段: ${field}"
            return {"status": "error", "message": "缺少必需字段: ${field}"}
        end
    end

    # 数据清理和格式化
    清理后的数据 = {}
    清理后的数据["name"] = ${用户信息["name"]}.strip().title()
    清理后的数据["email"] = ${用户信息["email"]}.strip().lower()
    清理后的数据["age"] = int(${用户信息["age"]})

    # 业务规则验证
    if ${清理后的数据["age"]} < 18 do
        return {"status": "error", "message": "年龄必须大于等于18岁"}
    end

    if "@" not in ${清理后的数据["email"]} do
        return {"status": "error", "message": "邮箱格式无效"}
    end

    [打印], 内容: "用户数据验证通过: ${清理后的数据["name"]}"
    return {"status": "success", "data": ${清理后的数据}}
end

# 使用示例
原始数据 = {
    "name": "  张三  ",
    "email": "ZHANGSAN@EXAMPLE.COM  ",
    "age": "25"
}

处理结果 = [处理用户数据], 用户信息: ${原始数据}
[打印], 内容: "处理结果: ${处理结果}"
```

### 场景3：测试环境准备

```python
function 准备测试环境 (环境名称="test", 清理现有数据=True) do
    [打印], 内容: "开始准备测试环境: ${环境名称}"
    
    # 环境配置
    if ${环境名称} == "test" do
        数据库URL = "test_database.db"
        API端口 = 8080
    elif ${环境名称} == "dev" do
        数据库URL = "dev_database.db"
        API端口 = 8081
    else
        [打印], 内容: "不支持的环境: ${环境名称}"
        return False
    end

    # 清理现有数据
    if ${清理现有数据} do
        [打印], 内容: "正在清理现有测试数据..."
        # 这里可以添加数据库清理逻辑
        [等待], 秒数: 1  # 模拟清理时间
    end

    # 创建测试数据
    [打印], 内容: "正在创建测试数据..."
    测试用户 = [创建测试用户], 环境: ${环境名称}
    测试订单 = [创建测试订单], 用户ID: ${测试用户["id"]}

    # 启动服务
    [打印], 内容: "正在启动测试服务，端口: ${API端口}"
    
    环境信息 = {
        "name": ${环境名称},
        "database_url": ${数据库URL},
        "api_port": ${API端口},
        "test_user": ${测试用户},
        "test_order": ${测试订单}
    }

    [打印], 内容: "测试环境准备完成"
    return ${环境信息}
end

function 创建测试用户 (环境="test") do
    用户数据 = {
        "id": "test_user_001",
        "name": "测试用户",
        "email": "testuser@example.com",
        "environment": ${环境}
    }
    
    [打印], 内容: "创建测试用户: ${用户数据["name"]}"
    return ${用户数据}
end

function 创建测试订单 (用户ID) do
    订单数据 = {
        "id": "test_order_001",
        "user_id": ${用户ID},
        "product": "测试商品",
        "amount": 99.99
    }
    
    [打印], 内容: "创建测试订单: ${订单数据["id"]}"
    return ${订单数据}
end

# 使用环境准备关键字
环境 = [准备测试环境], 环境名称: "test", 清理现有数据: True
[打印], 内容: "环境信息: ${环境}"
```

## 错误处理和调试

### 错误处理模式

```python
function 安全API调用 (URL, 重试次数=3) do
    当前尝试 = 1
    
    for i in range(1, ${重试次数} + 1) do
        当前尝试 = ${i}
        [打印], 内容: "第 ${当前尝试} 次尝试调用: ${URL}"
        
        # 这里可以添加try-catch逻辑（如果支持）
        # 目前使用条件判断模拟
        随机结果 = ${当前尝试} % 2  # 模拟成功/失败
        
        if ${随机结果} == 0 do
            [打印], 内容: "API调用成功"
            return {"status": "success", "attempt": ${当前尝试}}
        else
            [打印], 内容: "API调用失败，准备重试..."
            if ${当前尝试} < ${重试次数} do
                [等待], 秒数: 2  # 重试间隔
            end
        end
    end
    
    [打印], 内容: "所有重试都失败了"
    return {"status": "failed", "attempts": ${重试次数}}
end
```

### 调试信息输出

```python
function 调试关键字 (操作, 数据, 详细=False) do
    [打印], 内容: "=== 调试信息开始 ==="
    [打印], 内容: "操作: ${操作}"
    [打印], 内容: "数据类型: ${type(data)}"
    
    if ${详细} do
        [打印], 内容: "详细数据: ${数据}"
        [打印], 内容: "当前时间: $(date)"
    end
    
    # 执行实际操作
    if ${操作} == "保存" do
        [打印], 内容: "执行保存操作"
        结果 = "保存成功"
    elif ${操作} == "加载" do
        [打印], 内容: "执行加载操作"  
        结果 = "加载成功"
    else
        [打印], 内容: "未知操作: ${操作}"
        结果 = "操作失败"
    end
    
    [打印], 内容: "操作结果: ${结果}"
    [打印], 内容: "=== 调试信息结束 ==="
    
    return ${结果}
end
```

## 最佳实践

### 1. 命名规范

- 使用有意义的中文名称
- 关键字名称应该描述其功能
- 参数名称应该清晰明确

```python
# 好的命名
function 验证用户登录状态 (用户ID, 预期状态="已登录") do
    # ...
end

# 避免的命名
function func1 (param1, param2) do
    # ...
end
```

### 2. 参数设计

- 必需参数放在前面，可选参数放在后面
- 为可选参数提供合理的默认值
- 避免参数过多（建议不超过5个）

```python
# 好的参数设计
function 发送邮件 (收件人, 主题, 内容, 发件人="system@example.com", 紧急=False) do
    # ...
end
```

### 3. 功能单一性

每个自定义关键字应该专注于单一功能：

```python
# 好的设计 - 单一功能
function 验证邮箱格式 (邮箱地址) do
    # 只负责验证邮箱格式
end

function 发送验证邮件 (邮箱地址) do
    # 只负责发送邮件
end

# 避免 - 功能混杂
function 验证并发送邮件 (邮箱地址) do
    # 既验证又发送，职责不清
end
```

### 4. 返回值一致性

- 保持返回值类型的一致性
- 对于可能失败的操作，考虑返回统一的结果结构

```python
function 处理文件 (文件路径, 操作) do
    if 文件不存在 do
        return {"success": False, "message": "文件不存在"}
    end
    
    # 执行操作
    if 操作成功 do
        return {"success": True, "data": "处理结果"}
    else
        return {"success": False, "message": "操作失败"}
    end
end
```

### 5. 文档和注释

虽然DSL语法不支持注释，但可以通过打印语句或变量名来增加可读性：

```python
function 复杂计算 (输入数据) do
    步骤描述 = "开始复杂计算"
    [打印], 内容: ${步骤描述}
    
    中间结果1 = ${输入数据} * 2
    中间结果2 = ${中间结果1} + 10
    最终结果 = ${中间结果2} / 3
    
    步骤描述 = "计算完成"
    [打印], 内容: ${步骤描述}
    
    return ${最终结果}
end
```

## 与资源文件结合使用

自定义关键字通常与资源文件结合使用，实现更好的代码组织和复用。这将在[资源文件](./resource-files)章节中详细介绍。

## 下一步

- 学习[资源文件](./resource-files)了解如何组织和共享自定义关键字
- 查看[HTTP API测试](./http-testing)了解如何将自定义关键字用于API测试
- 阅读[最佳实践](./best-practices)了解项目组织的最佳方法 