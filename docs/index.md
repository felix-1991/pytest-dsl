---
layout: home

hero:
  name: "pytest-dsl"
  text: "强大的关键字驱动测试自动化框架"
  tagline: 让测试自动化变得简单直观 - 使用自然语言风格的DSL编写测试，无需复杂编程技能
  image:
    src: /logo.svg
    alt: pytest-dsl
  actions:
    - theme: brand
      text: 快速开始
      link: /guide/getting-started
    - theme: alt
      text: GitHub
      link: https://github.com/felix-1991/pytest-dsl

features:
  - icon: 🎯
    title: 零门槛上手
    details: 自然语言风格的DSL语法，测试人员无需编程基础即可编写自动化测试
  - icon: 🔧
    title: 高度可扩展
    details: 轻松创建自定义关键字，支持参数默认值，适应任何测试场景
  - icon: 🌐
    title: 分布式执行
    details: 内置远程关键字功能，支持大规模分布式测试和跨网络执行
  - icon: 🔄
    title: 无缝集成
    details: 完美兼容pytest生态，可渐进式迁移现有测试项目
  - icon: 📊
    title: 丰富报告
    details: 可结合pytest生态生成 HTML、Allure 等测试报告
  - icon: 🛡️
    title: 企业级特性
    details: 支持 YAML 变量管理、认证配置、远程扩展等工程化能力
  - icon: 🖥️
    title: UI测试支持
    details: 可通过 pytest-dsl-ui 扩展包接入 Web UI 测试能力
  - icon: 🔨
    title: 开发工具
    details: 提供配套 VS Code 扩展和文档工具链，增强编辑体验
---

## 快速体验

### 安装

::: code-group

```bash [pip]
pip install pytest-dsl
```

```bash [uv (推荐)]
uv pip install pytest-dsl
```

:::

### VS Code 插件安装

pytest-dsl 提供独立的 VS Code 扩展，可在扩展商店搜索 `pytest-dsl` 或直接安装：

::: code-group

```bash [命令行]
code --install-extension felix-1991.pytest-dsl-support
```

```text [扩展商店]
在VS Code中按 Ctrl+Shift+X 打开扩展商店
搜索 "pytest-dsl" 并安装
```

:::

### UI测试支持

UI 测试能力由独立扩展包提供，需要额外安装：

```bash
pip install pytest-dsl-ui

#安装playwright依赖
playwright install
```

### 创建第一个测试

创建文件 `hello.dsl`：

```python
@name: "我的第一个测试"
@description: "学习pytest-dsl的第一步"

# 定义变量
message = "Hello, pytest-dsl!"
count = 3

# 打印欢迎消息
[打印], 内容: ${message}

# 简单循环
for i in range(1, ${count} + 1) do
    [打印], 内容: "第 ${i} 次循环"
end

# 测试断言
[断言], 条件: "${count} == 3", 消息: "计数器应该等于3"

teardown do
    [打印], 内容: "测试完成！"
end
```

### 运行测试

```bash
# 直接运行DSL文件
pytest-dsl hello.dsl

# 运行目录下所有DSL文件
pytest-dsl tests/
```

## 核心特性

### 🎯 自然语言风格

```python
# 像写文档一样编写测试
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://api.example.com/users/1
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.name", "exists"]
'''
```

### 🌐 远程执行

```python
@remote: "http://remote-server:8270/" as remote_machine

# 在远程机器上执行关键字
remote_machine|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://internal-api.example.com/data
'''
```

### 🧪 Pytest集成

```python
# test_runner.py
from pytest_dsl.core.auto_decorator import auto_dsl

@auto_dsl("./tests")
class TestDSL:
    """自动将DSL目录转换为pytest测试"""
    pass

# 使用pytest运行
# pytest test_runner.py -q
```

### 🖥️ Web UI测试

```python
# 通过 pytest-dsl-ui 扩展包提供的 UI 关键字进行浏览器自动化测试
[打开浏览器], 浏览器类型: "chrome", 无头模式: false

[访问页面], URL: "https://example.com"

[点击元素], 选择器: "#login-button"

[输入文本], 选择器: "input[name='username']", 文本: "admin"

[断言元素文本], 选择器: ".welcome-message", 期望文本: "欢迎回来"

[关闭浏览器]
```

### 🔧 自定义关键字

```python
# 定义可复用的关键字
function 用户登录 (用户名, 密码="默认密码") do
    [HTTP请求], 客户端: "default", 配置: '''
        method: POST
        url: /api/login
        request:
            json:
                username: "${用户名}"
                password: "${密码}"
        captures:
            token: ["jsonpath", "$.token"]
    '''
    return ${token}
end

# 使用自定义关键字
token = [用户登录], 用户名: "admin"
```

### 📊 数据驱动

```python
@data: "test_data.csv" using csv

# CSV中的每一行都会执行一次测试
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: /api/login
    request:
        json:
            username: "${username}"
            password: "${password}"
    asserts:
        - ["status", "eq", ${expected_status}]
'''
```

## 开发工具支持

### VSCode扩展功能

以下能力来自独立的 VS Code 扩展，而非当前仓库主包直接内置：

#### 📊 智能关键字管理
- **关键字浏览器** - 侧边栏显示所有可用关键字
- **分类管理** - 按类型自动分组（内置、自定义、库、用户、收藏夹）
- **智能搜索** - 支持名称、参数、说明的实时模糊搜索
- **收藏夹功能** - 标记常用关键字，快速访问
- **树状结构** - 清晰的层级展示，支持展开/折叠

#### 🔍 智能编辑功能
- **语法高亮** - 完整的pytest-DSL语法高亮支持
- **智能补全** - 基于关键字库的自动补全和参数提示
- **参数模板** - 自动生成带参数的关键字模板
- **快捷键支持** - 高效的键盘操作和快捷插入
- **错误检查** - 实时语法和语义错误检测
- **悬停提示** - 关键字文档和参数说明

#### ⚙️ 便捷配置管理
- **关键字文件生成** - 自动生成和管理关键字JSON文件
- **实时缓存** - 智能缓存减少重复加载
- **可视化编辑** - 图形化界面编辑关键字定义

#### 🎮 交互操作支持
- **拖拽操作** - 支持从关键字浏览器拖拽到编辑器
- **右键菜单** - 丰富的上下文菜单操作
- **快速操作** - 一键插入、复制、收藏等功能

### 支持的文件类型

- `.dsl` - pytest-dsl测试文件
- `.pytest-dsl` - pytest-dsl测试文件（备选扩展名）

## 适用场景

<div class="use-cases">
  <div class="use-case">
    <h3>🔗 API接口测试</h3>
    <p>完整的HTTP测试支持，包括请求发送、响应捕获、断言验证</p>
  </div>
  <div class="use-case">
    <h3>🖥️ Web UI测试</h3>
    <p>浏览器自动化测试，支持元素交互、页面导航和界面验证</p>
  </div>
  <div class="use-case">
    <h3>🏗️ 分布式测试</h3>
    <p>跨服务调用、服务间通信和分布式系统测试，支持复杂的微服务架构验证</p>
  </div>
  <div class="use-case">
    <h3>🔄 回归测试</h3>
    <p>数据驱动和批量执行，轻松处理大量回归测试用例</p>
  </div>
  <div class="use-case">
    <h3>🔗 集成测试</h3>
    <p>跨系统测试协调，支持复杂的集成测试场景</p>
  </div>
  <div class="use-case">
    <h3>👥 团队协作</h3>
    <p>VS Code插件支持，提升团队开发效率和代码质量</p>
  </div>
</div>

<style>
.use-cases {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin: 2rem 0;
}

.use-case {
  padding: 1.5rem;
  border: 1px solid var(--vp-c-border);
  border-radius: 8px;
  background: var(--vp-c-bg-soft);
}

.use-case h3 {
  margin: 0 0 0.5rem 0;
  color: var(--vp-c-brand-1);
}

.use-case p {
  margin: 0;
  color: var(--vp-c-text-2);
  font-size: 0.9rem;
}
</style> 
