# 资源文件

资源文件（`.resource`）是pytest-dsl的重要特性，允许您将自定义关键字、变量和配置组织到可复用的文件中，实现跨项目的代码共享和团队协作。

## 🚀 resources目录自动导入

pytest-dsl 现在支持**零配置自动导入**功能！只需将 `.resource` 文件放在项目根目录的 `resources` 目录下，系统会自动发现并导入，无需手动使用 `@import` 指令。

### 零配置使用

```
your_project/
├── resources/                    # ⭐ 放在这里的资源文件会自动导入
│   ├── common/                  # 通用工具
│   │   └── utils.resource
│   ├── api/                     # API测试
│   │   └── http_utils.resource
│   └── ui/                      # UI测试
│       └── page_utils.resource
├── tests/
│   └── test_example.dsl         # 可直接使用resources中的关键字
└── README.md
```

```python
# test_example.dsl
@name: "零配置自动导入示例"

# 🎯 直接使用resources中的关键字，无需@import！
结果 = [格式化消息], 模板: "测试", 变量值: "自动导入"
[打印], 内容: ${结果}
```

**特性**：
- 🚀 **零配置**：无需任何配置或import语句
- 🧠 **智能依赖**：自动处理文件间依赖关系
- ⚡ **高性能**：智能缓存，避免重复加载
- 🌍 **多环境**：CLI、pytest等环境统一支持

## 什么是资源文件

资源文件是以`.resource`为扩展名的DSL文件，主要用于：

- 存储可复用的自定义关键字
- 定义公共变量和常量
- 组织项目级别的工具函数
- 实现跨测试文件的代码共享
- 建立标准化的测试组件库
- **零配置项目级自动导入**（新功能）

## 资源文件结构

资源文件的结构与普通DSL文件相似，但通常不包含实际的测试执行流程：

```python
@name: "资源文件名称"
@description: "资源文件描述"
@author: "作者名称"
@date: "创建日期"

# 可以导入其他资源文件
@import: "base_utils.resource"

# 定义常量和变量
DEFAULT_TIMEOUT = 30
API_VERSION = "v1"

# 定义自定义关键字
function 关键字名称 (参数列表) do
    # 关键字实现
end

# 更多关键字定义...
```

## 创建资源文件

### 基础资源文件示例

创建一个基础工具资源文件 `utils.resource`：

```python
@name: "通用工具关键字"
@description: "包含常用的工具函数和辅助关键字"
@author: "测试团队"
@date: "2024-01-15"

# 定义常用常量
DEFAULT_TIMEOUT = 30
MAX_RETRY_COUNT = 3
SUCCESS_STATUS_CODES = [200, 201, 202]

# 字符串处理关键字
function 格式化消息 (模板, 变量值) do
    格式化结果 = "${模板}: ${变量值}"
    [打印], 内容: "格式化消息 - ${格式化结果}"
    return ${格式化结果}
end

function 清理字符串 (输入字符串) do
    # 去除前后空格并转换为小写
    清理结果 = "${输入字符串}".strip().lower()
    [打印], 内容: "字符串清理: '${输入字符串}' -> '${清理结果}'"
    return ${清理结果}
end

# 数据验证关键字
function 验证非空 (值, 字段名="字段") do
    if "${值}" == "" do
        错误消息 = "${字段名}不能为空"
        [打印], 内容: "验证失败: ${错误消息}"
        return {"valid": False, "message": ${错误消息}}
    end
    
    [打印], 内容: "验证通过: ${字段名}值为'${值}'"
    return {"valid": True, "value": "${值}"}
end

function 验证邮箱格式 (邮箱地址) do
    if "@" not in "${邮箱地址}" do
        return {"valid": False, "message": "邮箱格式无效"}
    end
    
    if "." not in "${邮箱地址}" do
        return {"valid": False, "message": "邮箱格式无效"}
    end
    
    return {"valid": True, "email": "${邮箱地址}"}
end

# 等待和重试关键字
function 安全等待 (秒数, 描述="操作") do
    [打印], 内容: "开始等待${秒数}秒 - ${描述}"
    [等待], 秒数: ${秒数}
    [打印], 内容: "等待完成 - ${描述}"
end

function 重试执行 (最大次数=3) do
    当前次数 = 1
    
    for i in range(1, ${最大次数} + 1) do
        当前次数 = ${i}
        [打印], 内容: "第${当前次数}次尝试"
        
        # 这里可以插入实际要重试的逻辑
        # 返回成功标志来控制是否继续重试
        成功 = True  # 这里应该是实际的执行结果
        
        if ${成功} do
            [打印], 内容: "第${当前次数}次尝试成功"
            return {"success": True, "attempts": ${当前次数}}
        else
            [打印], 内容: "第${当前次数}次尝试失败"
            if ${当前次数} < ${最大次数} do
                [安全等待], 秒数: 2, 描述: "重试间隔"
            end
        end
    end
    
    return {"success": False, "attempts": ${最大次数}}
end
```

### API测试资源文件

创建专门用于API测试的资源文件 `api_utils.resource`：

```python
@name: "API测试工具关键字"
@description: "专门用于API接口测试的关键字集合"
@author: "API测试团队"
@date: "2024-01-15"

# 导入基础工具
@import: "utils.resource"

# API相关常量
API_TIMEOUT = 30
RETRY_DELAY = 2
COMMON_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "pytest-dsl-api-client/1.0"
}

# 认证相关关键字
function 登录获取Token (用户名, 密码, 服务器="default") do
    [打印], 内容: "开始登录用户: ${用户名}"
    
    [HTTP请求], 客户端: ${服务器}, 配置: '''
        method: POST
        url: /api/auth/login
        request:
            json:
                username: "${用户名}"
                password: "${密码}"
            timeout: ${API_TIMEOUT}
        captures:
            access_token: ["jsonpath", "$.access_token"]
            refresh_token: ["jsonpath", "$.refresh_token"]
            user_id: ["jsonpath", "$.user_id"]
        asserts:
            - ["status", "eq", 200]
            - ["jsonpath", "$.access_token", "not_empty"]
    '''
    
    [打印], 内容: "登录成功 - 用户ID: ${user_id}"
    
    # 保存token到全局变量
    [设置全局变量], 变量名: "current_token", 值: ${access_token}
    [设置全局变量], 变量名: "current_user_id", 值: ${user_id}
    
    return {
        "token": ${access_token},
        "refresh_token": ${refresh_token},
        "user_id": ${user_id}
    }
end

function 带认证的API调用 (方法, 路径, 数据=null, token="") do
    # 获取token
    使用的Token = ${token}
    if "${使用的Token}" == "" do
        使用的Token = [获取全局变量], 变量名: "current_token"
    end
    
    # 构建请求头
    请求头 = ${COMMON_HEADERS}
    请求头["Authorization"] = "Bearer ${使用的Token}"
    
    # 根据方法执行请求
    if "${方法}" == "GET" do
        [HTTP请求], 客户端: "default", 配置: '''
            method: GET
            url: "${路径}"
            request:
                headers: ${请求头}
                timeout: ${API_TIMEOUT}
            asserts:
                - ["status", "lt", 400]
        '''
    else
        [HTTP请求], 客户端: "default", 配置: '''
            method: "${方法}"
            url: "${路径}"
            request:
                headers: ${请求头}
                json: ${数据}
                timeout: ${API_TIMEOUT}
            asserts:
                - ["status", "lt", 400]
        '''
    end
    
    [打印], 内容: "${方法} ${路径} 调用完成"
end

# CRUD操作关键字
function 创建资源 (资源类型, 数据, token="") do
    [打印], 内容: "创建${资源类型}资源"
    
    [带认证的API调用], 方法: "POST", 路径: "/api/${资源类型}", 数据: ${数据}, token: ${token}
    
    # 这里应该捕获创建的资源ID，但需要在实际HTTP请求中配置captures
    return {"status": "created", "type": ${资源类型}}
end

function 获取资源 (资源类型, 资源ID, token="") do
    [打印], 内容: "获取${资源类型}资源: ${资源ID}"
    
    [带认证的API调用], 方法: "GET", 路径: "/api/${资源类型}/${资源ID}", token: ${token}
    
    return {"status": "retrieved", "type": ${资源类型}, "id": ${资源ID}}
end

function 更新资源 (资源类型, 资源ID, 数据, token="") do
    [打印], 内容: "更新${资源类型}资源: ${资源ID}"
    
    [带认证的API调用], 方法: "PUT", 路径: "/api/${资源类型}/${资源ID}", 数据: ${数据}, token: ${token}
    
    return {"status": "updated", "type": ${资源类型}, "id": ${资源ID}}
end

function 删除资源 (资源类型, 资源ID, token="") do
    [打印], 内容: "删除${资源类型}资源: ${资源ID}"
    
    [带认证的API调用], 方法: "DELETE", 路径: "/api/${资源类型}/${资源ID}", token: ${token}
    
    return {"status": "deleted", "type": ${资源类型}, "id": ${资源ID}}
end

# 响应验证关键字
function 验证API响应结构 (期望字段列表) do
    [打印], 内容: "验证API响应结构"
    
    # 这里应该与最近的HTTP请求结果配合使用
    # 实际实现需要能够访问上一次请求的响应数据
    
    for field in ${期望字段列表} do
        [打印], 内容: "检查字段: ${field}"
        # 实际验证逻辑
    end
    
    return {"status": "validated", "fields": ${期望字段列表}}
end

function 验证状态码范围 (最小值, 最大值) do
    [打印], 内容: "验证状态码在${最小值}-${最大值}范围内"
    
    # 这里应该与HTTP请求的captures配合使用
    # 实际实现需要能够访问响应状态码
    
    return {"status": "validated", "range": "${最小值}-${最大值}"}
end
```

## 导入和使用资源文件

### 基本导入语法

在DSL测试文件中使用`@import`指令导入资源文件：

```python
@name: "使用资源文件的测试"
@description: "演示如何导入和使用资源文件"

# 导入单个资源文件
@import: "utils.resource"

# 导入多个资源文件
@import: "api_utils.resource"

# 导入相对路径的资源文件
@import: "./resources/database_utils.resource"

# 导入子目录中的资源文件
@import: "common/string_utils.resource"

# 现在可以使用资源文件中定义的关键字
测试数据 = {
    "name": "  测试用户  ",
    "email": "TEST@EXAMPLE.COM"
}

# 使用导入的字符串清理关键字
清理后的名称 = [清理字符串], 输入字符串: ${测试数据["name"]}
清理后的邮箱 = [清理字符串], 输入字符串: ${测试数据["email"]}

# 验证数据
名称验证结果 = [验证非空], 值: ${清理后的名称}, 字段名: "用户名"
邮箱验证结果 = [验证邮箱格式], 邮箱地址: ${清理后的邮箱}

[打印], 内容: "名称验证: ${名称验证结果}"
[打印], 内容: "邮箱验证: ${邮箱验证结果}"
```

### 使用导入的常量

```python
@import: "api_utils.resource"

# 使用资源文件中定义的常量
[打印], 内容: "API超时设置: ${API_TIMEOUT}"
[打印], 内容: "重试延迟: ${RETRY_DELAY}"

# 在HTTP请求中使用常量
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /api/status
    request:
        headers: ${COMMON_HEADERS}
        timeout: ${API_TIMEOUT}
    asserts:
        - ["status", "eq", 200]
'''
```

## 资源文件组织结构

### 推荐的项目结构

```
project_root/
├── tests/                          # 测试文件目录
│   ├── api/                        # API测试
│   │   ├── test_users.dsl
│   │   ├── test_orders.dsl
│   │   └── test_auth.dsl
│   ├── ui/                         # UI测试
│   │   ├── test_login.dsl
│   │   └── test_dashboard.dsl
│   └── integration/                # 集成测试
│       └── test_workflow.dsl
├── resources/                      # 资源文件目录
│   ├── common/                     # 通用资源
│   │   ├── utils.resource          # 基础工具
│   │   ├── constants.resource      # 常量定义
│   │   └── validators.resource     # 验证器
│   ├── api/                        # API测试资源
│   │   ├── auth.resource           # 认证相关
│   │   ├── crud.resource           # CRUD操作
│   │   └── fixtures.resource       # 测试数据
│   ├── ui/                         # UI测试资源
│   │   ├── page_objects.resource   # 页面对象
│   │   └── interactions.resource   # 交互操作
│   └── database/                   # 数据库资源
│       ├── connections.resource    # 连接管理
│       └── queries.resource        # 查询操作
├── config/                         # 配置文件
│   ├── dev.yaml
│   ├── test.yaml
│   └── prod.yaml
└── pytest.ini                     # pytest配置
```

### 分层资源管理

#### 基础层资源 (common/)

```python
# resources/common/constants.resource
@name: "全局常量定义"

# 环境配置
ENVIRONMENTS = {
    "dev": "https://dev-api.example.com",
    "test": "https://test-api.example.com", 
    "prod": "https://api.example.com"
}

# 测试配置
DEFAULT_TIMEOUT = 30
MAX_RETRY_COUNT = 3
RETRY_DELAY = 2

# 状态码定义
HTTP_SUCCESS_CODES = [200, 201, 202]
HTTP_CLIENT_ERROR_CODES = [400, 401, 403, 404]
HTTP_SERVER_ERROR_CODES = [500, 502, 503, 504]
```

#### 功能层资源 (api/, ui/, database/)

```python
# resources/api/auth.resource
@name: "认证相关关键字"
@import: "../common/constants.resource"

function 获取访问令牌 (用户名, 密码, 环境="test") do
    服务器地址 = ${ENVIRONMENTS[环境]}
    
    [HTTP请求], 客户端: "default", 配置: '''
        method: POST
        url: ${服务器地址}/auth/token
        request:
            json:
                username: "${用户名}"
                password: "${密码}"
        captures:
            token: ["jsonpath", "$.access_token"]
        asserts:
            - ["status", "in", ${HTTP_SUCCESS_CODES}]
    '''
    
    return ${token}
end
```

#### 业务层资源 (business/)

```python
# resources/business/user_management.resource
@name: "用户管理业务流程"
@import: "../api/auth.resource"
@import: "../api/crud.resource"

function 完整用户注册流程 (用户数据) do
    [打印], 内容: "开始完整用户注册流程"
    
    # 1. 注册用户
    注册结果 = [创建资源], 资源类型: "users", 数据: ${用户数据}
    
    # 2. 验证邮箱（模拟）
    [安全等待], 秒数: 1, 描述: "邮箱验证处理"
    
    # 3. 激活账户
    激活数据 = {"status": "active"}
    激活结果 = [更新资源], 资源类型: "users", 资源ID: ${注册结果["id"]}, 数据: ${激活数据}
    
    # 4. 首次登录
    登录结果 = [获取访问令牌], 用户名: ${用户数据["username"]}, 密码: ${用户数据["password"]}
    
    return {
        "user": ${注册结果},
        "activation": ${激活结果},
        "token": ${登录结果}
    }
end
```

## 资源文件的高级特性

### 嵌套导入

资源文件可以导入其他资源文件，形成依赖链：

```python
# base.resource
@name: "基础功能"

function 基础日志 (消息) do
    [打印], 内容: "[BASE] ${消息}"
end
```

```python
# advanced.resource
@name: "高级功能"
@import: "base.resource"

function 高级日志 (消息, 级别="INFO") do
    [基础日志], 消息: "[${级别}] ${消息}"
end
```

```python
# test.dsl
@name: "测试文件"
@import: "advanced.resource"

# 可以使用所有导入链中的关键字
[基础日志], 消息: "直接使用基础功能"
[高级日志], 消息: "使用高级功能", 级别: "DEBUG"
```

### 条件导入和版本控制

```python
# version_specific.resource
@name: "版本特定功能"

API_VERSION = "v2"

function 版本化API调用 (端点, 数据=null) do
    完整路径 = "/api/${API_VERSION}/${端点}"
    
    [HTTP请求], 客户端: "default", 配置: '''
        method: POST
        url: "${完整路径}"
        request:
            json: ${数据}
    '''
end
```

### 参数化资源文件

```python
# configurable.resource
@name: "可配置资源文件"

# 可以通过全局变量配置行为
function 环境感知操作 (操作类型) do
    当前环境 = [获取全局变量], 变量名: "current_environment"
    
    if "${当前环境}" == "prod" do
        [打印], 内容: "生产环境模式: ${操作类型}"
        # 生产环境的谨慎操作
    else
        [打印], 内容: "测试环境模式: ${操作类型}" 
        # 测试环境的完整操作
    end
end
```

## 实际应用场景

### 场景1：团队协作标准化

```python
# resources/team/standards.resource
@name: "团队测试标准"
@description: "定义团队统一的测试标准和规范"

# 标准测试数据格式
STANDARD_USER = {
    "username": "test_user",
    "email": "test@example.com",
    "password": "Test123!@#"
}

STANDARD_HEADERS = {
    "Content-Type": "application/json",
    "X-Test-Suite": "pytest-dsl",
    "X-Team": "qa-team"
}

# 标准验证流程
function 标准API验证 (响应) do
    # 团队统一的API响应验证标准
    [断言], 条件: "response.status_code < 400", 消息: "API调用不应返回错误状态"
    
    # 标准响应时间验证
    if response.elapsed.total_seconds() > 5 do
        [打印], 内容: "警告: API响应时间超过5秒"
    end
    
    # 标准头部验证
    [断言], 条件: "'Content-Type' in response.headers", 消息: "响应应包含Content-Type头"
end

function 标准错误处理 (错误类型, 错误消息) do
    格式化消息 = "[${错误类型}] ${错误消息}"
    [打印], 内容: ${格式化消息}
    
    # 记录到团队日志系统（如果配置了的话）
    日志级别 = "ERROR"
    [打印], 内容: "日志级别: ${日志级别}"
end
```

### 场景2：多环境支持

```python
# resources/environments/env_manager.resource
@name: "环境管理器"

# 环境配置映射
ENVIRONMENT_CONFIGS = {
    "local": {
        "api_base": "http://localhost:8000",
        "db_host": "localhost",
        "timeout": 10
    },
    "dev": {
        "api_base": "https://dev-api.example.com",
        "db_host": "dev-db.example.com", 
        "timeout": 30
    },
    "staging": {
        "api_base": "https://staging-api.example.com",
        "db_host": "staging-db.example.com",
        "timeout": 30
    },
    "prod": {
        "api_base": "https://api.example.com",
        "db_host": "prod-db.example.com",
        "timeout": 60
    }
}

function 切换环境 (环境名称) do
    if ${环境名称} not in ${ENVIRONMENT_CONFIGS} do
        [打印], 内容: "错误: 不支持的环境 ${环境名称}"
        return False
    end
    
    环境配置 = ${ENVIRONMENT_CONFIGS[环境名称]}
    
    # 设置环境相关的全局变量
    [设置全局变量], 变量名: "current_environment", 值: ${环境名称}
    [设置全局变量], 变量名: "api_base_url", 值: ${环境配置["api_base"]}
    [设置全局变量], 变量名: "default_timeout", 值: ${环境配置["timeout"]}
    
    [打印], 内容: "已切换到环境: ${环境名称}"
    [打印], 内容: "API地址: ${环境配置["api_base"]}"
    
    return True
end

function 获取环境配置 (配置键) do
    当前环境 = [获取全局变量], 变量名: "current_environment"
    
    if "${当前环境}" == "" do
        [打印], 内容: "警告: 未设置当前环境，使用默认环境 'dev'"
        当前环境 = "dev"
    end
    
    环境配置 = ${ENVIRONMENT_CONFIGS[当前环境]}
    
    if ${配置键} in ${环境配置} do
        return ${环境配置[配置键]}
    else
        [打印], 内容: "错误: 配置键 '${配置键}' 在环境 '${当前环境}' 中不存在"
        return null
    end
end
```

## 最佳实践

### 1. 文件命名和组织

- 使用描述性的文件名（如`user_api.resource`而不是`utils.resource`）
- 按功能域组织资源文件（api/、ui/、database/等）
- 使用分层结构，从通用到具体

### 2. 关键字设计原则

- 每个关键字应该有单一职责
- 使用清晰的参数命名
- 提供合理的默认值
- 包含适当的日志输出

### 3. 依赖管理

```python
# 好的做法 - 明确声明依赖
@name: "订单管理"
@import: "auth.resource"      # 认证功能
@import: "api_base.resource"  # API基础功能

# 避免 - 循环依赖
# A.resource导入B.resource，B.resource又导入A.resource
```

### 4. 版本控制

- 为资源文件添加版本信息
- 使用Git等版本控制工具管理资源文件
- 定期重构和更新资源文件

### 5. 文档注释

```python
@name: "用户管理API"
@description: "提供用户相关的API操作关键字，包括CRUD操作和验证功能"
@author: "API测试团队"
@version: "2.1.0"
@date: "2024-01-15"

# 每个关键字都应该有清晰的用途说明
function 创建新用户 (用户数据, 验证邮箱=True) do
    # 用途: 创建新用户账户
    # 参数: 
    #   - 用户数据: 包含用户信息的字典
    #   - 验证邮箱: 是否需要邮箱验证步骤
    # 返回: 创建的用户信息字典
    
    [打印], 内容: "开始创建用户: ${用户数据['username']}"
    # 实现逻辑...
end
```

## 错误处理和调试

### 资源文件加载错误

```python
# 检查资源文件是否正确加载
@name: "资源文件测试"

# 测试导入是否成功
@import: "utils.resource"

# 验证关键字是否可用
[打印], 内容: "测试资源文件导入"

# 调用导入的关键字验证
result = [格式化消息], 模板: "测试", 变量值: "成功"
[打印], 内容: "结果: ${result}"
```

### 调试资源文件

```python
# debug.resource - 调试专用资源文件
@name: "调试工具"

function 调试变量 (变量名, 变量值) do
    [打印], 内容: "=== 调试信息 ==="
    [打印], 内容: "变量名: ${变量名}"
    [打印], 内容: "变量值: ${变量值}"
    [打印], 内容: "变量类型: ${type(变量值)}"
    [打印], 内容: "==============="
end

function 调试关键字调用 (关键字名, 参数字典) do
    [打印], 内容: "调用关键字: ${关键字名}"
    [打印], 内容: "参数: ${参数字典}"
end
```

## 下一步

- 学习[数据驱动测试](./data-driven)了解如何使用资源文件进行数据驱动测试
- 查看[环境配置管理](./configuration)了解如何结合配置文件使用资源文件
- 阅读[最佳实践](./best-practices)了解大型项目中的资源文件组织方法 