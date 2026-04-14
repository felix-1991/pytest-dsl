# VS Code 扩展

pytest-dsl 提供了专门的 VS Code 扩展插件，为 DSL 文件提供完整的编辑器支持，包括语法高亮、智能补全、错误检查等功能，大大提升开发体验。

## 安装

### 方式一：VS Code 扩展商店

1. 打开 VS Code
2. 按 `Ctrl+Shift+X`（Windows/Linux）或 `Cmd+Shift+X`（Mac）打开扩展面板
3. 搜索 `pytest-dsl`
4. 找到 **pytest-dsl** 扩展并点击 **安装**

### 方式二：命令行安装

```bash
code --install-extension felix-1991.pytest-dsl-support
```

### 方式三：从VSIX文件安装

如果你有 `.vsix` 文件：

```bash
code --install-extension pytest-dsl.vsix
```

## 支持的文件类型

扩展自动识别以下文件类型：

- `.dsl` - pytest-dsl 测试文件（主要扩展名）
- `.pytest-dsl` - pytest-dsl 测试文件（备选扩展名）

## 核心功能

### 🎨 语法高亮

扩展提供完整的 DSL 语法高亮支持：

```python
# 注释高亮
@name: "测试名称"  # 元数据高亮
@description: "测试描述"

# 变量高亮
username = "admin"
api_url = "https://api.example.com"

# 关键字调用高亮
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: ${api_url}/users
    asserts:
        - ["status", "eq", 200]
'''

# 控制流高亮
if ${username} == "admin" do
    [打印], 内容: "管理员登录"
else
    [打印], 内容: "普通用户登录"
end

# 函数定义高亮
function 用户登录 (用户名, 密码="123456") do
    # 函数体
    return ${token}
end
```

### 💡 智能补全

#### 关键字补全

输入 `[` 后自动显示可用关键字列表：

- `[HTTP请求]` - HTTP 接口测试关键字
- `[打印]` - 打印输出关键字
- `[断言]` - 断言验证关键字
- `[等待]` - 延时等待关键字
- 以及其他已注册关键字...

#### 参数补全

选择关键字后，自动显示参数提示：

```python
[HTTP请求], |  # 光标位置，显示参数选项：
             # - 客户端
             # - 配置
             # - 超时时间
```

#### 变量补全

输入 `${` 后显示当前作用域内的变量：

```python
username = "admin"
password = "secret"

[HTTP请求], 配置: '''
    request:
        json:
            username: "${|}"  # 显示: username, password
'''
```

#### 控制流补全

- 输入 `if` 自动补全 `if-do-end` 结构
- 输入 `for` 自动补全 `for-do-end` 结构
- 输入 `function` 自动补全函数定义结构

### 🔍 错误检查

扩展提供实时的语法错误检测：

#### 语法错误检测

```python
# ❌ 语法错误：缺少 end
if condition do
    [打印], 内容: "hello"
# 错误提示：Expected 'end' keyword

# ❌ 语法错误：关键字格式错误
HTTP请求], 配置: "..."  # 缺少开头的 [
# 错误提示：Invalid keyword format

# ❌ 语法错误：变量引用错误
[打印], 内容: "${undefined_var"  # 缺少结束的 }
# 错误提示：Unclosed variable reference
```

#### 语义错误检测

```python
# ❌ 语义错误：未定义的变量
[打印], 内容: "${unknown_variable}"
# 警告：Variable 'unknown_variable' is not defined

# ❌ 语义错误：函数参数不匹配
function test_func (param1, param2) do
    # 函数体
end

[test_func], param1: "value1"  # 缺少 param2
# 警告：Missing required parameter 'param2'
```

### 📖 悬停提示

将鼠标悬停在关键字、变量或函数上，显示详细信息：

#### 关键字悬停

```python
[HTTP请求], 配置: "..."  # 悬停显示：
                      # HTTP请求关键字
                      # 用于发送HTTP请求并验证响应
                      # 参数：
                      # - 客户端: HTTP客户端名称
                      # - 配置: 请求配置（YAML格式）
                      # - 超时时间: 请求超时时间（秒）
```

#### 变量悬停

```python
username = "admin"    # 悬停显示：
                      # 变量: username
                      # 类型: str
                      # 值: "admin"

[打印], 内容: "${username}"  # 悬停 username 显示同样信息
```

#### 函数悬停

```python
function 登录 (用户名, 密码="默认") do
    # 函数体
end

token = [登录], 用户名: "admin"  # 悬停显示：
                              # 函数: 登录
                              # 参数: 用户名, 密码="默认"
                              # 返回值: token
```

### 🔗 定义跳转

#### 跳转到变量定义

```python
username = "admin"    # 变量定义位置

# ... 其他代码 ...

[打印], 内容: "${username}"  # Ctrl+Click 或 F12 跳转到定义
```

#### 跳转到函数定义

```python
function 用户登录 (用户名) do  # 函数定义位置
    # 函数体
end

# ... 其他代码 ...

[用户登录], 用户名: "admin"  # Ctrl+Click 跳转到函数定义
```

#### 跳转到包含的文件

```python
@include: "common_functions.dsl"  # Ctrl+Click 跳转到文件
```

### 📁 文件图标

扩展为 DSL 文件提供专用图标，在文件资源管理器中易于识别：

- `.dsl` 文件显示专门的 pytest-dsl 图标
- `.pytest-dsl` 文件显示相同的图标

## 配置选项

你可以在 VS Code 设置中自定义扩展行为：

### 通过设置界面配置

1. 打开 VS Code 设置（`Ctrl+,`）
2. 搜索 `pytest-dsl`
3. 调整相关设置

### 通过 settings.json 配置

```json
{
  "pytest-dsl.validation.enabled": true,
  "pytest-dsl.completion.enabled": true,
  "pytest-dsl.completion.includeBuiltinKeywords": true,
  "pytest-dsl.completion.includeVariables": true,
  "pytest-dsl.hover.enabled": true,
  "pytest-dsl.hover.showDocumentation": true,
  "pytest-dsl.format.enabled": true,
  "pytest-dsl.format.indentSize": 4,
  "pytest-dsl.format.useSpaces": true,
  "pytest-dsl.diagnostics.maxProblems": 100,
  "pytest-dsl.trace.server": "off"
}
```

### 配置选项说明

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `validation.enabled` | `true` | 启用语法验证 |
| `completion.enabled` | `true` | 启用智能补全 |
| `completion.includeBuiltinKeywords` | `true` | 补全中包含内置关键字 |
| `completion.includeVariables` | `true` | 补全中包含变量 |
| `hover.enabled` | `true` | 启用悬停提示 |
| `hover.showDocumentation` | `true` | 悬停时显示文档 |
| `format.enabled` | `true` | 启用代码格式化 |
| `format.indentSize` | `4` | 缩进大小 |
| `format.useSpaces` | `true` | 使用空格缩进 |
| `diagnostics.maxProblems` | `100` | 最大问题数量 |
| `trace.server` | `"off"` | 语言服务器跟踪级别 |

## 快捷键

扩展提供以下默认快捷键：

| 快捷键 | 功能 | 说明 |
|--------|------|------|
| `Ctrl+Space` | 触发补全 | 显示智能补全列表 |
| `F12` | 跳转到定义 | 跳转到变量/函数定义 |
| `Alt+F12` | 查看定义 | 在弹窗中预览定义 |
| `Shift+F12` | 查找引用 | 查找变量/函数的所有引用 |
| `F2` | 重命名符号 | 重命名变量/函数 |
| `Ctrl+Shift+F` | 格式化文档 | 格式化当前文档 |

## 代码片段

扩展包含常用的代码片段，提高编写效率：

### HTTP 测试片段

输入 `http` + `Tab`：

```python
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: ${1:https://api.example.com}
    asserts:
        - ["status", "eq", ${2:200}]
'''
```

### 函数定义片段

输入 `function` + `Tab`：

```python
function ${1:函数名} (${2:参数}) do
    ${3:# 函数体}
    return ${4:result}
end
```

### 条件语句片段

输入 `if` + `Tab`：

```python
if ${1:condition} do
    ${2:# 代码块}
end
```

### 循环语句片段

输入 `for` + `Tab`：

```python
for ${1:i} in ${2:range(1, 10)} do
    ${3:# 循环体}
end
```

### 数据驱动片段

输入 `data` + `Tab`：

```python
@name: "${1:测试名称}"
@data: "${2:data.csv}" using csv

# 测试内容
${3:}
```

## 调试支持

### 运行配置

扩展会自动创建 `.vscode/launch.json` 配置：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Run pytest-dsl",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/venv/bin/pytest-dsl",
            "args": ["${file}"],
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}"
        },
        {
            "name": "Debug pytest-dsl",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/venv/bin/pytest-dsl",
            "args": ["${file}", "--verbose"],
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}",
            "justMyCode": false
        }
    ]
}
```

### 运行和调试

1. **运行当前文件**: `F5` 或点击运行按钮
2. **调试当前文件**: `Ctrl+F5` 或选择调试配置
3. **运行所有测试**: 在终端中使用 `pytest-dsl` 命令

## 工作区支持

### 多文件项目支持

扩展支持包含多个 DSL 文件的项目：

```
project/
├── tests/
│   ├── api_tests.dsl
│   ├── ui_tests.dsl
│   └── common/
│       └── functions.dsl
├── data/
│   └── test_data.csv
└── pytest-dsl.yaml
```

### 跨文件引用

扩展支持跨文件的定义跳转和引用查找：

```python
# common/functions.dsl
function 通用登录 (用户名) do
    # 登录逻辑
end

# api_tests.dsl
@include: "common/functions.dsl"

[通用登录], 用户名: "admin"  # 可以跳转到 common/functions.dsl
```

## 故障排除

### 常见问题

#### 1. 语法高亮不生效

**解决方案**：
- 确保文件扩展名为 `.dsl` 或 `.pytest-dsl`
- 重启 VS Code
- 检查是否安装了其他冲突的扩展

#### 2. 智能补全不工作

**解决方案**：
- 检查设置中的 `pytest-dsl.completion.enabled` 是否为 `true`
- 确保 pytest-dsl 已正确安装（`pip install pytest-dsl`）
- 重启 VS Code 语言服务器：`Ctrl+Shift+P` → "Reload Window"

#### 3. 错误检查误报

**解决方案**：
- 检查 DSL 语法是否正确
- 更新到最新版本的扩展
- 在设置中调整 `pytest-dsl.diagnostics.maxProblems`

#### 4. 性能问题

**解决方案**：
- 关闭不需要的功能（如悬停提示）
- 减少 `diagnostics.maxProblems` 的值
- 排除大型文件或目录

### 日志查看

1. 打开输出面板：`Ctrl+Shift+U`
2. 选择 "pytest-dsl" 输出频道
3. 查看详细的调试信息

### 报告问题

如果遇到问题，请访问 [GitHub Issues](https://github.com/felix-1991/pytest-dsl-vscode-extension/issues) 页面报告。

提供以下信息有助于快速解决问题：

- VS Code 版本
- 扩展版本
- 操作系统
- 重现步骤
- 错误截图或日志

## 更新和版本

### 自动更新

VS Code 默认会自动更新扩展。你也可以手动检查更新：

1. 打开扩展面板（`Ctrl+Shift+X`）
2. 点击扩展右上角的齿轮图标
3. 选择 "检查更新"

### 版本历史

可以在扩展详情页面查看版本历史和更新说明。

### 降级版本

如果新版本有问题，可以降级到之前的版本：

1. 在扩展面板中找到 pytest-dsl 扩展
2. 点击齿轮图标
3. 选择 "安装其他版本"
4. 选择要安装的版本

通过 VS Code 扩展，你可以获得完整的 pytest-dsl 开发体验，从编写到调试，一切都变得更加高效和便捷。 
