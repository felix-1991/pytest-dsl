# 示例库

欢迎来到pytest-dsl示例库！这里提供了丰富的实际应用示例，帮助您快速掌握pytest-dsl的各种功能和最佳实践。

## 示例分类

### 🚀 基础示例

适合初学者，展示pytest-dsl的基本功能：

- **[Hello World](./hello-world)** - 最简单的入门示例
- **[基本语法](./basic-syntax)** - DSL语法基础演示
- **[变量使用](./variables)** - 变量定义和引用示例
- **[流程控制](./control-flow)** - 条件判断和循环示例

### 🔧 高级示例

展示pytest-dsl的高级功能：

- **[自定义关键字](./custom-keywords)** - 创建可复用的测试组件
- **[数据驱动测试](./data-driven)** - 使用外部数据驱动测试
- **[命令行工具](./cli-tools)** - 关键字管理和文档生成
- **[远程测试](./remote-testing)** - 分布式测试执行
- **[远程Hook机制](./remote-hooks)** - 远程服务器扩展和自定义授权
- **[完整项目](./complete-project)** - 企业级测试项目结构

## 按场景浏览

### 🎯 我想学习基础语法

推荐学习路径：
1. [Hello World](./hello-world) - 了解基本结构
2. [基本语法](./basic-syntax) - 掌握语法规则
3. [变量使用](./variables) - 学习变量系统
4. [流程控制](./control-flow) - 掌握控制结构

### 🚀 我想分布式测试

推荐学习路径：
1. [远程测试](./remote-testing) - 基础远程执行
2. [远程Hook机制](./remote-hooks) - 服务器扩展和自定义授权
3. [完整项目](./complete-project) - 分布式项目架构

## 示例特点

### ✅ 可运行性

所有示例都经过验证，可以直接运行：

```bash
# 克隆示例到本地
git clone https://github.com/felix-1991/pytest-dsl.git
cd pytest-dsl/examples

# 运行示例
pytest-dsl hello_world.dsl
```

### 📝 详细注释

每个示例都包含详细的注释说明：

```python
@name: "示例：基本语法演示"
@description: "展示pytest-dsl的基本语法特性"

# 这是变量定义
message = "Hello, pytest-dsl!"

# 这是关键字调用
[打印], 内容: ${message}  # 打印变量内容
```

### 🎯 实际应用

示例基于真实的测试场景，具有实际参考价值：

- 使用真实的API端点（如JSONPlaceholder）
- 模拟实际的业务流程
- 展示常见的测试模式

### 📚 渐进式学习

示例按难度递增排列，支持渐进式学习：

- **初级** - 基础语法和简单功能
- **中级** - API测试和数据处理
- **高级** - 自定义扩展和项目架构

## 如何使用示例

### 1. 在线浏览

直接在文档中查看示例代码和说明。

### 2. 本地运行

```bash
# 安装pytest-dsl
pip install pytest-dsl

# 创建示例文件
# 复制示例代码到本地文件

# 运行示例
pytest-dsl your_example.dsl
```

### 3. 修改实验

鼓励您修改示例代码，观察结果变化：

```python
# 原始示例
[打印], 内容: "Hello, World!"

# 尝试修改
[打印], 内容: "你好，世界！"
[打印], 内容: "当前时间: ${当前时间}"
```

### 4. 组合应用

将多个示例的技巧组合使用：

```python
# 组合变量使用和API测试
api_url = "https://jsonplaceholder.typicode.com"
user_id = 1

[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: ${api_url}/users/${user_id}
    captures:
        user_name: ["jsonpath", "$.name"]
'''

[打印], 内容: "用户名: ${user_name}"
```

## 贡献示例

我们欢迎您贡献新的示例！

### 贡献指南

1. **选择主题** - 选择一个有价值的测试场景
2. **编写代码** - 确保代码可运行且有注释
3. **添加文档** - 提供清晰的说明和学习目标
4. **提交PR** - 通过GitHub提交您的贡献

### 示例要求

- **可运行** - 示例必须能够直接运行
- **有注释** - 关键代码需要有中文注释
- **有说明** - 包含学习目标和使用场景
- **有价值** - 展示实际的测试技巧或模式

## 获得帮助

如果在使用示例过程中遇到问题：

1. **检查环境** - 确认pytest-dsl已正确安装
2. **查看文档** - 参考相关章节的详细说明
3. **提交Issue** - 在GitHub上报告问题
4. **参与讨论** - 在社区中寻求帮助

---

准备好开始探索了吗？从[Hello World](./hello-world)开始您的pytest-dsl学习之旅吧！ 