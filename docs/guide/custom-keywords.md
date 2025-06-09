# 自定义关键字概览

自定义关键字是pytest-dsl最强大的功能之一，它允许您将常用的测试逻辑封装成可复用的组件，提高测试代码的可读性和维护性。

## 什么是自定义关键字

自定义关键字是用户定义的可重用测试步骤，类似于编程语言中的函数。它们可以：

- 🔧 **封装复杂逻辑** - 将复杂的测试步骤简化为简单的关键字调用
- 🔄 **提高代码复用** - 一次定义，多处使用，减少重复代码
- 📖 **增强可读性** - 使测试用例更加直观和易于理解
- 🛠️ **简化操作** - 将多个步骤组合成单一的高级操作

## 两种定义方式

pytest-dsl提供了两种创建自定义关键字的方式，适合不同的使用场景和技能水平：

### 1. DSL内定义方式 🎯

**适合人群**：测试人员、无编程基础用户  
**特点**：零门槛、即时可用、语法简洁

```python
@name: "DSL内自定义关键字示例"

# 在DSL文件中直接定义
function 问候 (姓名, 前缀="你好") do
    消息 = "${前缀}, ${姓名}!"
    [打印], 内容: ${消息}
    return ${消息}
end

# 立即使用
结果 = [问候], 姓名: "张三", 前缀: "欢迎"
```

**优势**：
- ✅ 无需编程基础，使用自然语言风格
- ✅ 在同一文件中定义和使用，即时生效
- ✅ 语法简洁，学习成本低
- ✅ 完美集成DSL语法特性

**限制**：
- ❌ 功能相对有限，受DSL语法约束
- ❌ 不支持远程执行
- ❌ 无法使用第三方Python库
- ❌ 调试能力有限

### 2. Python代码定义方式 🚀

**适合人群**：开发人员、有编程基础用户  
**特点**：功能强大、高度灵活、支持远程执行

```python
# keywords/my_keywords.py
from pytest_dsl.core.keyword_manager import keyword_manager

@keyword_manager.register('HTTP请求', [
    {'name': '地址', 'mapping': 'url', 'description': '请求地址'},
    {'name': '方法', 'mapping': 'method', 'description': 'HTTP方法', 'default': 'GET'},
    {'name': '超时', 'mapping': 'timeout', 'description': '超时时间（秒）', 'default': 30}
])
def http_request(**kwargs):
    """HTTP请求关键字，支持重试和错误处理"""
    import requests
    
    url = kwargs.get('url')
    method = kwargs.get('method', 'GET')
    timeout = kwargs.get('timeout', 30)
    
    response = requests.request(method, url, timeout=timeout)
    return {
        'status_code': response.status_code,
        'text': response.text,
        'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None
    }
```

```python
# 在DSL中使用
@name: "Python关键字使用示例"

响应 = [HTTP请求], 地址: "https://api.github.com/users/octocat"
[数据比较], 实际值: ${响应["status_code"]}, 预期值: 200
```

**优势**：
- ✅ 功能强大，可使用完整Python生态系统
- ✅ 支持远程执行和分布式测试
- ✅ 完整的错误处理和类型检查
- ✅ 可以打包分发，便于团队共享
- ✅ 支持第三方库和复杂业务逻辑
- ✅ 支持插件机制，可发布到PyPI共享

**限制**：
- ❌ 需要Python编程基础
- ❌ 需要单独的Python文件管理
- ❌ 学习成本相对较高

### 插件机制 🚀

Python代码定义的关键字还支持**插件化分发**：

```python
# 1. 本地使用 - 项目keywords目录
project/
├── keywords/
│   ├── my_keywords.py
│   └── web_testing.py
└── tests/

# 2. 插件分发 - 打包成Python库
my-plugin/
├── my_plugin/
│   ├── __init__.py
│   └── keywords/
│       ├── __init__.py
│       ├── web_keywords.py
│       └── api_keywords.py
└── setup.py

# 3. 安装和使用
pip install my-pytest-dsl-plugin
# pytest-dsl会自动发现并加载已安装的插件
# 无需任何配置，直接在DSL中使用插件提供的关键字
```

**插件优势**：
- 🌍 **全球分享** - 通过PyPI分发给全世界开发者
- 🔄 **版本管理** - 支持语义化版本和依赖管理
- 🛡️ **质量保证** - 可以包含完整的测试和文档
- 🎯 **专业领域** - 针对特定测试领域（Web、API、移动等）

## 选择指南

### 何时使用DSL内定义

- 🎯 **测试人员主导** - 团队主要由测试人员组成
- 🚀 **快速原型** - 需要快速创建和验证测试逻辑
- 📝 **简单逻辑** - 测试逻辑相对简单，不涉及复杂计算
- 🔄 **临时使用** - 关键字只在特定测试中使用

**示例场景**：
- 简单的数据验证和格式化
- 基础的业务流程封装
- 测试数据的生成和处理
- 简单的条件判断和循环

### 何时使用Python代码定义

- 👨‍💻 **开发人员参与** - 团队有Python开发能力
- 🌐 **分布式测试** - 需要在多个服务器上执行
- 🔧 **复杂逻辑** - 涉及复杂的数据处理或算法
- 📦 **团队共享** - 需要在多个项目间复用

**示例场景**：
- HTTP API测试和复杂断言
- 数据库操作和数据验证
- 文件处理和数据转换
- 第三方服务集成
- 性能测试和监控

## resources目录自动导入 🚀

### 零配置的关键字管理

pytest-dsl 提供了**自动导入机制**，可以零配置地导入项目根目录下 `resources` 目录中的所有 `.resource` 文件，让关键字管理变得前所未有的简单。

### 目录结构

```
your_project/
├── resources/                    # ⭐ 自动导入目录
│   ├── common/                  # 通用工具关键字
│   │   └── utils.resource       # 基础工具函数
│   ├── api/                     # API 测试关键字  
│   │   └── http_utils.resource  # HTTP 相关操作
│   ├── business/                # 业务流程关键字
│   │   └── workflows.resource   # 业务流程封装
│   └── data/                    # 数据处理关键字
│       └── validators.resource  # 数据验证
├── tests/                       # 测试文件
│   ├── *.dsl                   # DSL 测试文件
│   └── *.py                    # Python 测试文件
└── keywords/                    # Python 关键字（可选）
    └── *.py                    # Python 自定义关键字
```

### 零配置使用示例

**resources/common/utils.resource:**
```python
@name: "通用工具关键字"

function 格式化消息 (模板, 变量值) do
    格式化结果 = "${模板}: ${变量值}"
    return ${格式化结果}
end

function 验证非空 (值, 字段名="字段") do
    if ${值} == "" do
        return "验证失败"
    end
    return "验证通过"
end
```

**resources/api/http_utils.resource:**
```python
@name: "HTTP工具关键字"
@import: "../common/utils.resource"  # 可以导入其他资源文件

function 登录获取Token (用户名, 密码) do
    登录消息 = [格式化消息], 模板: "用户登录", 变量值: ${用户名}
    [打印], 内容: ${登录消息}
    
    # 模拟登录逻辑
    return "token_${用户名}_123456"
end
```

**test_example.dsl:**
```python
@name: "零配置自动导入测试"

# 🎯 直接使用resources中的关键字，无需任何@import指令！
用户名 = "testuser"
验证结果 = [验证非空], 值: ${用户名}, 字段名: "用户名"
登录结果 = [登录获取Token], 用户名: ${用户名}, 密码: "password123"

[打印], 内容: "验证结果: ${验证结果}"
[打印], 内容: "登录结果: ${登录结果}"
```

### 核心特性

- **🚀 零配置**：无需任何配置文件或import语句
- **🧠 智能依赖**：自动解析和处理文件间依赖关系
- **⚡ 高性能**：智能缓存，避免重复加载
- **🌍 多环境**：CLI、pytest、IDE等环境统一支持
- **🔄 向后兼容**：不影响现有的@import功能

### 工作原理

1. **自动发现**：启动时自动检测`resources`目录
2. **递归扫描**：遍历所有子目录，查找`.resource`文件
3. **依赖分析**：解析`@import`指令，构建依赖图
4. **拓扑排序**：按依赖关系确定加载顺序
5. **智能加载**：避免重复加载和循环依赖

### 最佳实践

```
resources/
├── common/          # 🏗️ 基础层：最通用的工具
│   ├── utils.resource
│   └── validators.resource
├── api/             # 🌐 服务层：API相关操作
│   ├── http_utils.resource
│   └── auth_utils.resource
├── ui/              # 🖥️ 界面层：UI测试相关
│   ├── page_utils.resource
│   └── element_utils.resource
└── business/        # 🏢 业务层：业务流程封装
    ├── user_flows.resource
    └── order_flows.resource
```

**依赖方向**：business → ui/api → common（避免循环依赖）

## 混合使用策略

在实际项目中，两种方式可以完美结合使用：

```python
# 1. 使用Python定义基础能力关键字
# keywords/base_keywords.py
@keyword_manager.register('数据库查询', [...])
def database_query(**kwargs):
    # 复杂的数据库操作逻辑
    pass

@keyword_manager.register('HTTP请求', [...])  
def http_request(**kwargs):
    # 完整的HTTP请求处理
    pass
```

```python
# 2. 在DSL中定义业务流程关键字
@name: "用户管理测试"

function 创建测试用户 (用户名, 邮箱) do
    # 使用Python关键字作为基础能力
    用户数据 = {"username": ${用户名}, "email": ${邮箱}}
    响应 = [HTTP请求], 地址: "/api/users", 方法: "POST", 数据: ${用户数据}
    
    # DSL逻辑处理
    if ${响应["status_code"]} == 201 do
        [打印], 内容: "用户创建成功: ${用户名}"
        return ${响应["json"]["user_id"]}
    else
        [打印], 内容: "用户创建失败"
        return null
    end
end

function 验证用户存在 (用户ID) do
    # 组合使用基础关键字
    查询结果 = [数据库查询], SQL: "SELECT * FROM users WHERE id = ?", 参数: [${用户ID}]
    
    查询结果长度 = [获取长度], 对象: ${查询结果}
    if ${查询结果长度} > 0 do
        [打印], 内容: "用户存在: ${查询结果[0]["username"]}"
        return True
    else
        [打印], 内容: "用户不存在"
        return False
    end
end

# 使用组合关键字
用户ID = [创建测试用户], 用户名: "testuser", 邮箱: "test@example.com"
存在状态 = [验证用户存在], 用户ID: ${用户ID}
[断言], 条件: "${存在状态} == True"
```

## 功能对比表

| 特性 | DSL内定义 | Python代码定义 | resources自动导入 |
|------|-----------|----------------|------------------|
| **学习门槛** | 🟢 极低 | 🟡 中等 | 🟢 极低 |
| **开发速度** | 🟢 极快 | 🟡 中等 | 🟢 极快 |
| **功能强大程度** | 🟡 中等 | 🟢 极强 | 🟡 中等 |
| **远程执行** | 🔴 不支持 | 🟢 完全支持 | 🔴 不支持 |
| **第三方库** | 🔴 不支持 | 🟢 完全支持 | 🔴 不支持 |
| **错误处理** | 🟡 基础 | 🟢 完整 | 🟡 基础 |
| **类型安全** | 🟡 基础 | 🟢 完整 | 🟡 基础 |
| **调试能力** | 🟡 基础 | 🟢 完整 | 🟡 基础 |
| **代码复用** | 🟡 文件内 | 🟢 跨项目 | 🟢 项目内 |
| **插件分发** | 🔴 不支持 | 🟢 PyPI分发 | 🔴 不支持 |
| **社区共享** | 🔴 不支持 | 🟢 插件生态 | 🟡 Git共享 |
| **团队协作** | 🟢 易于理解 | 🟡 需要技能 | 🟢 易于理解 |
| **组织管理** | 🔴 分散 | 🟡 需规划 | 🟢 结构化 |
| **导入配置** | 🔴 需手动 | 🔴 需注册 | 🟢 零配置 |
| **依赖处理** | 🔴 手动管理 | 🟡 需规划 | 🟢 智能解析 |

## 快速开始

### 体验DSL内定义

```python
@name: "DSL关键字快速体验"

# 定义一个简单的关键字
function 计算BMI (身高, 体重) do
    # 计算BMI值：体重(kg) / 身高(m)²
    BMI原值 = ${体重} / (${身高} * ${身高})
    BMI值 = [四舍五入], 数值: ${BMI原值}, 小数位数: 2
    
    if ${BMI值} < 18.5 do
        分类 = "偏瘦"
    elif ${BMI值} < 24 do
        分类 = "正常"
    elif ${BMI值} < 28 do
        分类 = "偏胖"
    else
        分类 = "肥胖"
    end
    
    结果 = {"bmi": ${BMI值}, "category": ${分类}}
    [打印], 内容: "BMI: ${BMI值}, 分类: ${分类}"
    return ${结果}
end

# 使用关键字
我的BMI = [计算BMI], 身高: 1.75, 体重: 70
[数据比较], 实际值: ${我的BMI["category"]}, 预期值: "正常"
```

### 体验Python代码定义

1. 创建关键字文件 `keywords/demo.py`：

```python
from pytest_dsl.core.keyword_manager import keyword_manager
import random

@keyword_manager.register('生成测试数据', [
    {'name': '数据类型', 'mapping': 'data_type', 'description': '数据类型：user/order/product'},
    {'name': '数量', 'mapping': 'count', 'description': '生成数量', 'default': 1}
])
def generate_test_data(**kwargs):
    """生成测试数据"""
    data_type = kwargs.get('data_type')
    count = kwargs.get('count', 1)
    
    templates = {
        'user': lambda i: {
            'id': f'user_{i:03d}',
            'name': f'测试用户{i}',
            'email': f'user{i}@test.com'
        },
        'order': lambda i: {
            'id': f'order_{i:03d}',
            'amount': round(random.uniform(10, 1000), 2),
            'status': random.choice(['pending', 'paid', 'shipped'])
        },
        'product': lambda i: {
            'id': f'product_{i:03d}',
            'name': f'测试商品{i}',
            'price': round(random.uniform(1, 100), 2)
        }
    }
    
    if data_type not in templates:
        raise ValueError(f"不支持的数据类型: {data_type}")
    
    template = templates[data_type]
    return [template(i) for i in range(1, count + 1)]
```

2. 在DSL中使用：

```python
@name: "Python关键字快速体验"

# 生成测试数据
用户数据 = [生成测试数据], 数据类型: "user", 数量: 3
订单数据 = [生成测试数据], 数据类型: "order", 数量: 2

[打印], 内容: "生成的用户: ${用户数据}"
[打印], 内容: "生成的订单: ${订单数据}"

# 验证数据
用户数据长度 = [获取长度], 对象: ${用户数据}
订单数据长度 = [获取长度], 对象: ${订单数据}
[数据比较], 实际值: ${用户数据长度}, 预期值: 3
[数据比较], 实际值: ${订单数据长度}, 预期值: 2
```

## 学习路径

### 初学者路径 🎯

1. **从DSL内定义开始** - [DSL内自定义关键字](./custom-keywords-dsl.md)
2. **掌握基本语法** - 学习function、参数、返回值
3. **练习流程控制** - 条件判断、循环处理
4. **实际项目应用** - 封装常用测试步骤

### 进阶用户路径 🚀

1. **学习Python定义** - [Python代码自定义关键字](./custom-keywords-python.md)
2. **掌握装饰器语法** - @keyword_manager.register
3. **学习参数配置** - mapping、default、description
4. **探索高级特性** - 远程执行、错误处理、性能优化

### 团队协作路径 🤝

1. **制定规范** - 关键字命名、参数设计规范
2. **分工合作** - 开发人员负责Python关键字，测试人员负责DSL关键字
3. **建立库** - 创建团队共享的关键字库
4. **持续优化** - 根据使用反馈不断改进

## 下一步

根据您的需求和技能水平，选择合适的学习路径：

- 🎯 **测试人员/初学者** → [DSL内自定义关键字](./custom-keywords-dsl.md)
- 🚀 **开发人员/进阶用户** → [Python代码自定义关键字](./custom-keywords-python.md)
- 📁 **了解组织方式** → [资源文件](./resource-files.md)
- 🌐 **分布式测试** → [远程关键字](./remote-keywords.md)
- 📖 **最佳实践** → [最佳实践指南](./best-practices.md) 