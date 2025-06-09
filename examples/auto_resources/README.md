# pytest-dsl 自动导入 resources 目录功能

## 功能概述

pytest-dsl 现在支持自动发现和导入项目根目录下的 `resources` 目录中的所有 `.resource` 文件，无需手动使用 `@import` 指令。这个功能让项目中的自定义关键字可以自动可用，大大简化了测试文件的编写。

## 功能特点

### ✨ 零配置自动导入
- 无需手动配置，系统自动发现并导入 `resources` 目录
- 支持多层嵌套目录结构
- 自动处理文件间的依赖关系

### 🧠 智能依赖解析
- 使用拓扑排序算法处理资源文件之间的依赖关系
- 自动按正确顺序加载文件，避免依赖冲突
- 检测并跳过循环依赖

### 🚀 高性能缓存机制
- 智能缓存已加载的资源文件，避免重复导入
- 支持多环境下的缓存管理

### 🌍 多环境支持
- CLI 工具中自动导入
- pytest 插件中自动导入
- 支持不同项目根目录的自动检测

## 项目结构

```
examples/auto_resources/
├── resources/                    # 自动导入的资源目录
│   ├── common/                  # 通用工具关键字
│   │   └── utils.resource       # 基础工具函数
│   ├── api/                     # API 测试关键字
│   │   └── http_utils.resource  # HTTP 工具（依赖 utils.resource）
│   └── simple/                  # 简单测试工具
│       └── test_utils.resource  # 测试辅助函数
├── test_auto_import.dsl         # 复杂自动导入演示
├── test_simple.dsl              # 简单自动导入演示
├── test_runner.py               # pytest 运行器
└── README.md                    # 本文档
```

## 资源文件示例

### 1. 基础工具 (`resources/common/utils.resource`)

```python
@name: "通用工具关键字"
@description: "提供常用的工具函数和辅助关键字"
@author: "pytest-dsl团队"
@date: "2024-01-15"

# 字符串处理关键字
function 格式化消息 (模板, 变量值) do
    格式化结果 = "${模板}: ${变量值}"
    [打印], 内容: "格式化消息 - ${格式化结果}"
    return ${格式化结果}
end

function 清理字符串 (输入字符串) do
    [打印], 内容: "字符串清理: '${输入字符串}'"
    return ${输入字符串}
end

# 数据验证关键字
function 验证非空 (值, 字段名="字段") do
    if ${值} == "" do
        错误消息 = "${字段名}不能为空"
        [打印], 内容: "验证失败: ${错误消息}"
        return "验证失败"
    end
    
    [打印], 内容: "验证通过: ${字段名}值为'${值}'"
    return "验证通过"
end

function 验证邮箱格式 (邮箱地址) do
    [打印], 内容: "验证邮箱: ${邮箱地址}"
    
    if "@" in ${邮箱地址} do
        [打印], 内容: "邮箱格式有效: ${邮箱地址}"
        return "邮箱格式有效"
    else
        [打印], 内容: "邮箱格式无效: ${邮箱地址}"
        return "邮箱格式无效"
    end
end

# 工具关键字
function 安全等待 (秒数, 描述="操作") do
    [打印], 内容: "开始等待${秒数}秒 - ${描述}"
    [等待], 秒数: ${秒数}
    [打印], 内容: "等待完成 - ${描述}"
    return "等待完成"
end

function 简单计算 (数字1, 数字2, 操作) do
    if ${操作} == "加法" do
        结果 = ${数字1} + ${数字2}
    elif ${操作} == "减法" do
        结果 = ${数字1} - ${数字2}
    elif ${操作} == "乘法" do
        结果 = ${数字1} * ${数字2}
    else
        结果 = 0
    end
    
    [打印], 内容: "${数字1} ${操作} ${数字2} = ${结果}"
    return ${结果}
end
```

### 2. API 工具 (`resources/api/http_utils.resource`)

```python
@name: "HTTP工具关键字"
@description: "专门用于HTTP API测试的关键字集合"
@author: "API测试团队"
@date: "2024-01-15"

# 导入基础工具
@import: "../common/utils.resource"

function 登录获取Token (用户名, 密码, 服务器="default") do
    [打印], 内容: "开始登录用户: ${用户名}"
    
    # 使用导入的格式化消息关键字
    登录消息 = [格式化消息], 模板: "用户登录", 变量值: ${用户名}
    [打印], 内容: ${登录消息}
    
    # 模拟登录过程
    模拟Token = "token_${用户名}_123456"
    [打印], 内容: "登录成功 - Token: ${模拟Token}"
    
    return ${模拟Token}
end

function 带认证的API调用 (方法, 路径, 数据="", token="") do
    # 使用导入的验证关键字
    验证结果 = [验证非空], 值: ${方法}, 字段名: "HTTP方法"
    
    if ${验证结果} == "验证失败" do
        [打印], 内容: "API调用失败: HTTP方法不能为空"
        return "API调用失败"
    end
    
    [打印], 内容: "${方法} ${路径} 调用完成"
    return "API调用成功"
end

function 创建资源 (资源类型, 数据="") do
    [打印], 内容: "创建${资源类型}资源"
    
    # 使用验证关键字
    验证结果 = [验证非空], 值: "POST", 字段名: "HTTP方法"
    
    if ${验证结果} == "验证通过" do
        [打印], 内容: "POST /api/${资源类型} 调用完成"
        return "资源创建完成"
    else
        return "资源创建失败"
    end
end

function 获取资源 (资源类型, 资源ID) do
    [打印], 内容: "获取${资源类型}资源: ${资源ID}"
    
    # 使用验证关键字
    验证结果 = [验证非空], 值: "GET", 字段名: "HTTP方法"
    
    if ${验证结果} == "验证通过" do
        [打印], 内容: "GET /api/${资源类型}/${资源ID} 调用完成"
        return "资源获取完成"
    else
        return "资源获取失败"
    end
end
```

### 3. 简单工具 (`resources/simple/test_utils.resource`)

```python
@name: "简单测试工具"
@description: "提供简单的测试辅助功能"
@author: "测试团队"
@date: "2024-01-15"

function 生成测试数据 (数据类型, 数量=1) do
    [打印], 内容: "生成${数据类型}类型的测试数据，数量: ${数量}"
    
    if ${数据类型} == "用户" do
        结果 = "测试用户数据"
    elif ${数据类型} == "订单" do
        结果 = "测试订单数据"
    else
        结果 = "通用测试数据"
    end
    
    [打印], 内容: "生成的测试数据: ${结果}"
    return ${结果}
end

function 验证测试结果 (实际值, 预期值, 测试名称="测试") do
    [打印], 内容: "验证${测试名称}: 实际值=${实际值}, 预期值=${预期值}"
    
    if ${实际值} == ${预期值} do
        结果 = "验证通过"
        [打印], 内容: "${测试名称}验证通过"
    else
        结果 = "验证失败"
        [打印], 内容: "${测试名称}验证失败"
    end
    
    return ${结果}
end

function 清理测试环境 (环境类型="默认") do
    [打印], 内容: "清理${环境类型}测试环境"
    [等待], 秒数: 1
    [打印], 内容: "测试环境清理完成"
    return "清理完成"
end

function 简单问候 (姓名) do
    问候语 = "你好, ${姓名}!"
    [打印], 内容: ${问候语}
    return ${问候语}
end

function 简单计算 (数字1, 数字2, 操作) do
    if ${操作} == "加法" do
        结果 = ${数字1} + ${数字2}
    elif ${操作} == "减法" do
        结果 = ${数字1} - ${数字2}
    elif ${操作} == "乘法" do
        结果 = ${数字1} * ${数字2}
    else
        结果 = 0
    end
    
    [打印], 内容: "${数字1} ${操作} ${数字2} = ${结果}"
    return ${结果}
end
```

## 测试文件示例

### 复杂自动导入测试 (`test_auto_import.dsl`)

```python
@name: "自动导入resources目录测试"
@description: "演示自动导入resources目录中的自定义关键字功能"
@author: "pytest-dsl团队"
@date: "2024-01-15"

# 注意：这里没有使用@import指令，但可以直接使用resources目录中定义的关键字
# 因为系统会自动导入resources目录中的所有.resource文件

[打印], 内容: "开始测试自动导入功能"

# 使用来自 resources/common/utils.resource 的关键字
测试数据 = "  Hello World  "
清理后的数据 = [清理字符串], 输入字符串: ${测试数据}

# 使用格式化消息关键字
格式化结果 = [格式化消息], 模板: "清理结果", 变量值: ${清理后的数据}
[打印], 内容: ${格式化结果}

# 使用验证关键字
用户名 = "testuser"
验证结果 = [验证非空], 值: ${用户名}, 字段名: "用户名"
[打印], 内容: "用户名验证结果: ${验证结果}"

# 验证邮箱格式
邮箱地址 = "test@example.com"
邮箱验证结果 = [验证邮箱格式], 邮箱地址: ${邮箱地址}
[打印], 内容: "邮箱验证结果: ${邮箱验证结果}"

# 测试简单计算关键字
计算结果1 = [简单计算], 数字1: 10, 数字2: 5, 操作: "加法"
计算结果2 = [简单计算], 数字1: 10, 数字2: 3, 操作: "乘法"
[打印], 内容: "计算结果1: ${计算结果1}"
[打印], 内容: "计算结果2: ${计算结果2}"

# 使用安全等待关键字
[安全等待], 秒数: 2, 描述: "测试等待功能"

# 使用来自 resources/api/http_utils.resource 的关键字
登录结果 = [登录获取Token], 用户名: "testuser", 密码: "password123"
[打印], 内容: "登录结果: ${登录结果}"

# 测试API调用关键字
API调用结果 = [带认证的API调用], 方法: "GET", 路径: "/api/users", token: ${登录结果}
[打印], 内容: "API调用结果: ${API调用结果}"

# 测试资源操作关键字
创建资源结果 = [创建资源], 资源类型: "users"
[打印], 内容: "创建资源结果: ${创建资源结果}"

获取资源结果 = [获取资源], 资源类型: "users", 资源ID: "123"
[打印], 内容: "获取资源结果: ${获取资源结果}"

# 使用来自 resources/simple/test_utils.resource 的关键字
生成的测试数据1 = [生成测试数据], 数据类型: "用户", 数量: 3
生成的测试数据2 = [生成测试数据], 数据类型: "订单"
[打印], 内容: "生成的测试数据1: ${生成的测试数据1}"
[打印], 内容: "生成的测试数据2: ${生成的测试数据2}"

# 测试验证关键字
验证结果1 = [验证测试结果], 实际值: "成功", 预期值: "成功", 测试名称: "登录测试"
验证结果2 = [验证测试结果], 实际值: "失败", 预期值: "成功", 测试名称: "错误测试"

[打印], 内容: "验证结果1: ${验证结果1}"
[打印], 内容: "验证结果2: ${验证结果2}"

[打印], 内容: "自动导入功能测试完成！"

# 清理操作
teardown do
    [打印], 内容: "清理测试环境"
    清理结果 = [清理测试环境], 环境类型: "自动导入测试"
    [打印], 内容: "清理结果: ${清理结果}"
end
```

## 使用方法

### 1. CLI 工具使用

```bash
# 直接运行测试文件，自动导入 resources 目录
python -m pytest_dsl.cli run test_auto_import.dsl

# 运行简单测试
python -m pytest_dsl.cli run test_simple.dsl

# 查看所有可用关键字（包括自动导入的）
python -m pytest_dsl.cli list-keywords --format json --output keywords.json
```

### 2. pytest 集成使用

```python
# test_runner.py
import pytest
from pytest_dsl.plugin import run_dsl_file

class TestAutoImport:
    def test_test_auto_import(self):
        """测试自动导入功能的复杂示例"""
        run_dsl_file("test_auto_import.dsl")
    
    def test_test_simple(self):
        """测试自动导入功能的简单示例"""
        run_dsl_file("test_simple.dsl")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### 3. 项目结构要求

```
your_project/
├── resources/              # 必须是这个名称
│   ├── common/            # 可以有任意层级的子目录
│   │   └── *.resource     # 资源文件
│   ├── api/
│   │   └── *.resource
│   └── ...
├── tests/                 # 测试文件目录
│   ├── *.dsl             # DSL 测试文件
│   └── *.py              # Python 测试文件
└── config/               # 配置文件目录（可选）
    └── *.yaml
```

## 工作原理

### 自动发现机制

1. **项目根目录检测**：系统会自动检测项目根目录
2. **resources 目录扫描**：在根目录下查找 `resources` 目录
3. **递归文件发现**：递归扫描所有 `.resource` 文件
4. **依赖关系分析**：解析文件中的 `@import` 指令

### 依赖解析算法

1. **依赖图构建**：分析每个文件的 `@import` 指令
2. **拓扑排序**：使用拓扑排序确定加载顺序
3. **循环依赖检测**：自动检测并跳过循环依赖
4. **按序加载**：按依赖关系顺序加载文件

### 缓存机制

1. **文件级缓存**：避免重复加载同一文件
2. **关键字注册缓存**：避免重复注册同一关键字
3. **多环境支持**：在不同环境中维护独立缓存

## 技术实现

### 核心组件

1. **CustomKeywordManager** (`pytest_dsl/core/custom_keyword_manager.py`)
   - `auto_import_resources_directory()` - 自动导入主函数
   - `_sort_resources_by_dependencies()` - 依赖排序
   - `_extract_dependencies()` - 依赖提取

2. **DSL执行器集成** (`pytest_dsl/core/dsl_executor.py`)
   - `_auto_import_resources()` - 执行器中的自动导入

3. **CLI工具集成** (`pytest_dsl/cli.py`)
   - `load_all_keywords()` - CLI中的自动导入

4. **pytest插件集成** (`pytest_dsl/plugin.py`)
   - `pytest_configure()` - pytest环境中的自动导入

### 关键特性

- **零配置**：无需任何配置文件或设置
- **智能依赖**：自动处理文件间的依赖关系
- **高性能**：缓存机制避免重复加载
- **多环境**：CLI、pytest等环境都支持
- **向后兼容**：不影响现有的 `@import` 功能

## 测试结果

运行测试后，系统会显示：

```
发现resources目录: /path/to/project/resources
在resources目录中发现 3 个资源文件
已注册自定义关键字: 生成测试数据 来自文件: .../test_utils.resource
已注册自定义关键字: 格式化消息 来自文件: .../utils.resource
已注册自定义关键字: 登录获取Token 来自文件: .../http_utils.resource
...
共 43 个关键字
  内置: 29 个
  项目自定义: 14 个
```

## 最佳实践

### 1. 目录组织

```
resources/
├── common/          # 通用工具
├── api/            # API 相关
├── ui/             # UI 相关
├── database/       # 数据库相关
└── utils/          # 其他工具
```

### 2. 文件命名

- 使用描述性的文件名：`user_management.resource`
- 按功能模块组织：`auth.resource`, `payment.resource`
- 避免循环依赖：合理规划文件间的依赖关系

### 3. 关键字设计

- 使用清晰的中文关键字名称
- 提供合理的默认参数值
- 添加适当的错误处理和日志输出

## 故障排除

### 常见问题

1. **关键字未找到**
   - 检查 `resources` 目录是否存在
   - 确认文件扩展名为 `.resource`
   - 查看控制台输出的导入日志

2. **依赖关系错误**
   - 检查 `@import` 路径是否正确
   - 避免循环依赖
   - 使用相对路径引用

3. **语法错误**
   - 确保DSL语法正确
   - 检查日期格式（支持字符串格式）
   - 避免使用不支持的Python函数

### 调试方法

1. **查看导入日志**：运行时会显示详细的导入过程
2. **检查关键字列表**：使用 `list-keywords` 命令查看所有关键字
3. **逐步测试**：从简单的关键字开始测试

## 总结

pytest-dsl 的自动导入功能大大简化了项目中自定义关键字的管理和使用：

- ✅ **零配置**：无需手动导入，自动发现
- ✅ **智能依赖**：自动处理复杂的依赖关系
- ✅ **高性能**：缓存机制提升加载效率
- ✅ **多环境**：CLI、pytest等环境无缝支持
- ✅ **向后兼容**：不影响现有功能

这个功能让测试团队可以更专注于测试逻辑的编写，而不用担心关键字的导入和管理问题。 