# 安装配置

本章将详细介绍如何安装和配置pytest-dsl，确保您能够顺利开始使用这个强大的测试框架。

## 系统要求

### Python版本要求

pytest-dsl支持以下Python版本：

- **Python 3.8+** （推荐Python 3.9或更高版本）
- 支持Windows、macOS、Linux等主流操作系统

### 依赖检查

在安装pytest-dsl之前，请确保您的系统已安装Python：

```bash
# 检查Python版本
python --version
# 或
python3 --version

# 检查pip版本
pip --version
# 或
pip3 --version
```

## 安装方式

### 方式一：使用pip安装（推荐）

```bash
# 安装最新版本
pip install pytest-dsl

# 安装指定版本
pip install pytest-dsl==1.0.0

# 升级到最新版本
pip install --upgrade pytest-dsl
```

### 方式二：使用uv安装（更快）

如果您使用uv作为包管理器：

```bash
# 安装uv（如果还没有安装）
pip install uv

# 使用uv安装pytest-dsl
uv pip install pytest-dsl

# 升级
uv pip install --upgrade pytest-dsl
```

### 方式三：从源码安装

```bash
# 克隆仓库
git clone https://github.com/felix-1991/pytest-dsl.git
cd pytest-dsl

# 安装开发版本
pip install -e .

# 或安装发布版本
pip install .
```

## 扩展组件安装

### UI测试扩展

如果您需要进行Web UI自动化测试，请安装UI扩展包：

```bash
# 安装UI测试扩展
pip install pytest-dsl-ui

# 或使用uv安装
uv pip install pytest-dsl-ui
```

UI扩展提供了丰富的浏览器自动化关键字，支持：
- 多种浏览器（Chrome、Firefox、Safari等）
- 元素操作（点击、输入、选择等）
- 页面导航和等待
- 断言验证
- 截图和调试

### VS Code扩展插件

为了获得最佳的开发体验，强烈推荐安装VS Code扩展：

#### 安装方式一：扩展商店

1. 打开VS Code
2. 按 `Ctrl+Shift+X`（Windows/Linux）或 `Cmd+Shift+X`（Mac）
3. 搜索 `pytest-dsl`
4. 点击**安装**

#### 安装方式二：命令行

```bash
code --install-extension felix-1991.pytest-dsl-vscode-extension
```

#### 扩展功能

VS Code扩展提供以下功能：
- **🎨 语法高亮**: 完整的DSL语法高亮
- **💡 智能补全**: 关键字和参数自动补全
- **🔍 错误检查**: 实时语法和语义错误检测
- **📖 悬停提示**: 关键字文档和参数说明
- **🔗 定义跳转**: 快速跳转到定义
- **📁 文件图标**: DSL文件专用图标

## 验证安装

### 核心框架验证

安装完成后，验证pytest-dsl是否正确安装：

```bash
# 检查版本
pytest-dsl --version

# 查看帮助信息
pytest-dsl --help

# 查看可用关键字
pytest-dsl-list --format text
```

如果看到版本信息和帮助内容，说明核心框架安装成功！

### UI扩展验证

如果安装了UI扩展，验证是否正确安装：

```bash
# 检查UI关键字是否可用
pytest-dsl-list --format text | grep -i "浏览器\|UI\|元素"

# 或者创建简单测试文件验证
echo '[打开浏览器], 浏览器类型: "chrome", 无头模式: true
[访问页面], URL: "https://example.com"
[关闭浏览器]' > ui_test.dsl

# 运行UI测试
pytest-dsl ui_test.dsl
```

### VS Code扩展验证

验证VS Code扩展是否正确安装：

1. 在VS Code中创建一个`.dsl`文件
2. 输入 `[` 应该看到关键字补全提示
3. 检查是否有语法高亮
4. 文件图标是否显示为pytest-dsl专用图标

如果以上功能正常，说明VS Code扩展安装成功！

## 开发环境配置

### IDE配置

#### VS Code配置

除了前面提到的pytest-dsl专用扩展外，还推荐安装以下VS Code扩展：

1. **pytest-dsl** - pytest-dsl语法支持（必装）
2. **Python** - Python语言支持
3. **YAML** - YAML文件语法高亮
4. **Better Comments** - 更好的注释显示

创建`.vscode/settings.json`：

```json
{
    "files.associations": {
        "*.dsl": "pytest-dsl",
        "*.pytest-dsl": "pytest-dsl",
        "*.resource": "python"
    },
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    
    // pytest-dsl扩展配置
    "pytest-dsl.validation.enabled": true,
    "pytest-dsl.completion.enabled": true,
    "pytest-dsl.hover.enabled": true,
    "pytest-dsl.format.indentSize": 4,
    "pytest-dsl.format.useSpaces": true
}
```

#### VS Code工作区配置

创建`.vscode/launch.json`用于调试：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "运行当前DSL文件",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/venv/bin/pytest-dsl",
            "args": ["${file}"],
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}"
        },
        {
            "name": "调试当前DSL文件",
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

#### PyCharm配置

在PyCharm中配置DSL文件支持：

1. 打开 **Settings** → **Editor** → **File Types**
2. 选择 **Python** 文件类型
3. 在 **File name patterns** 中添加：
   - `*.dsl`
   - `*.resource`

### 虚拟环境配置

推荐使用虚拟环境隔离项目依赖：

```bash
# 创建虚拟环境
python -m venv pytest-dsl-env

# 激活虚拟环境
# Windows
pytest-dsl-env\Scripts\activate
# macOS/Linux
source pytest-dsl-env/bin/activate

# 在虚拟环境中安装pytest-dsl
pip install pytest-dsl

# 验证安装
pytest-dsl --version
```

## 项目初始化

### 创建项目结构

创建一个标准的pytest-dsl项目结构：

```bash
# 创建项目目录
mkdir my-pytest-dsl-project
cd my-pytest-dsl-project

# 创建标准目录结构
mkdir -p {tests,resources,config,reports}

# 创建配置文件
touch config/dev.yaml
touch config/prod.yaml

# 创建第一个测试文件
touch tests/hello.dsl

# 创建资源文件
touch resources/common.resource
```

项目结构如下：

```
my-pytest-dsl-project/
├── tests/              # 测试文件目录
│   └── hello.dsl
├── resources/          # 资源文件目录
│   └── common.resource
├── config/             # 配置文件目录
│   ├── dev.yaml
│   └── prod.yaml
├── reports/            # 测试报告目录
└── README.md           # 项目说明
```

### 基础配置文件

创建`config/dev.yaml`：

```yaml
# 开发环境配置
environment: "development"
debug: true

# API配置
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
      User-Agent: "pytest-dsl/1.0"

# 测试数据
test_data:
  admin_user:
    username: "admin"
    password: "admin123"
  normal_user:
    username: "user"
    password: "user123"
```

### 第一个测试文件

创建`tests/hello.dsl`：

```python
@name: "Hello World测试"
@description: "验证pytest-dsl安装和配置"

# 打印欢迎消息
[打印], 内容: "欢迎使用pytest-dsl！"

# 简单的断言测试
[断言], 条件: "1 + 1 == 2", 消息: "数学计算错误"

# 测试变量使用
message = "pytest-dsl配置成功"
[打印], 内容: ${message}

# 测试API调用（使用公共API）
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.title", "exists"]
''', 步骤名称: "测试API连接"

[打印], 内容: "所有测试通过！pytest-dsl已准备就绪。"
```

如果安装了UI扩展，也可以创建`tests/ui_hello.dsl`测试UI功能：

```python
@name: "UI Hello World测试"
@description: "验证UI扩展安装和配置"

# 打开浏览器（无头模式，避免干扰）
[打开浏览器], 浏览器类型: "chrome", 无头模式: true

# 访问示例页面
[访问页面], URL: "https://example.com"

# 验证页面标题
[断言元素包含文本], 选择器: "h1", 期望文本: "Example Domain"

# 截图保存
[截取页面截图], 文件路径: "reports/ui_test_screenshot.png"

# 清理：关闭浏览器
teardown do
    [关闭浏览器]
    [打印], 内容: "UI测试完成！"
end
```

### 运行测试验证

```bash
# 运行基础测试验证配置
pytest-dsl tests/hello.dsl --yaml-vars config/dev.yaml

# 如果看到类似输出，说明配置成功：
# ✓ 欢迎使用pytest-dsl！
# ✓ pytest-dsl配置成功
# ✓ 测试API连接
# ✓ 所有测试通过！pytest-dsl已准备就绪。

# 如果安装了UI扩展，运行UI测试
pytest-dsl tests/ui_hello.dsl

# UI测试成功输出示例：
# ✓ 打开浏览器: chrome (无头模式)
# ✓ 访问页面: https://example.com
# ✓ 断言元素包含文本: h1 -> "Example Domain"
# ✓ 截取页面截图: reports/ui_test_screenshot.png
# ✓ UI测试完成！
```

## 常见问题

### 安装问题

#### 问题1：pip安装失败

```bash
# 错误信息：Could not find a version that satisfies the requirement pytest-dsl
```

**解决方案**：
```bash
# 升级pip
pip install --upgrade pip

# 使用国内镜像源
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pytest-dsl
```

#### 问题2：权限错误

```bash
# 错误信息：Permission denied
```

**解决方案**：
```bash
# 使用用户安装
pip install --user pytest-dsl

# 或使用虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows
pip install pytest-dsl
```

#### 问题3：Python版本不兼容

```bash
# 错误信息：Requires Python '>=3.8'
```

**解决方案**：
```bash
# 检查Python版本
python --version

# 如果版本过低，请升级Python或使用pyenv管理多版本
# 安装pyenv（macOS）
brew install pyenv

# 安装Python 3.9
pyenv install 3.9.0
pyenv global 3.9.0
```

### 配置问题

#### 问题1：命令找不到

```bash
# 错误信息：command not found: pytest-dsl
```

**解决方案**：
```bash
# 检查PATH环境变量
echo $PATH

# 找到pytest-dsl安装位置
pip show pytest-dsl

# 添加到PATH（如果需要）
export PATH=$PATH:~/.local/bin
```

#### 问题2：关键字加载失败

```bash
# 错误信息：No keywords found
```

**解决方案**：
```bash
# 检查安装完整性
pip install --force-reinstall pytest-dsl

# 验证关键字加载
pytest-dsl-list --format text
```

#### 问题3：UI扩展问题

```bash
# 错误信息：No module named 'selenium' 或浏览器驱动错误
```

**解决方案**：
```bash
# 重新安装UI扩展
pip install --force-reinstall pytest-dsl-ui

# 安装浏览器驱动（如果需要）
# Chrome
pip install chromedriver-autoinstaller

# Firefox
pip install geckodriver-autoinstaller
```

#### 问题4：VS Code扩展不工作

```bash
# 症状：没有语法高亮或智能补全
```

**解决方案**：
1. 确认扩展已正确安装：
   - 打开扩展面板（Ctrl+Shift+X）
   - 搜索"pytest-dsl"确认已安装

2. 检查文件关联：
   ```json
   {
     "files.associations": {
       "*.dsl": "pytest-dsl",
       "*.pytest-dsl": "pytest-dsl"
     }
   }
   ```

3. 重启VS Code语言服务器：
   - 按 `Ctrl+Shift+P`
   - 运行 "Developer: Reload Window"

### 运行问题

#### 问题1：YAML配置文件错误

```bash
# 错误信息：YAML parsing error
```

**解决方案**：
```bash
# 检查YAML语法
python -c "import yaml; yaml.safe_load(open('config/dev.yaml'))"

# 使用在线YAML验证器检查语法
```

#### 问题2：网络连接问题

```bash
# 错误信息：Connection timeout
```

**解决方案**：
```yaml
# 在配置文件中增加超时时间
http_clients:
  default:
    timeout: 60  # 增加超时时间
    retries: 3   # 增加重试次数
```

## 高级配置

### 环境变量配置

设置常用的环境变量：

```bash
# Linux/macOS
export PYTEST_DSL_CONFIG_DIR="./config"
export PYTEST_DSL_LOG_LEVEL="INFO"

# Windows
set PYTEST_DSL_CONFIG_DIR=./config
set PYTEST_DSL_LOG_LEVEL=INFO
```

### 日志配置

创建`logging.yaml`：

```yaml
version: 1
formatters:
  default:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: default
  file:
    class: logging.FileHandler
    filename: logs/pytest-dsl.log
    level: DEBUG
    formatter: default
loggers:
  pytest_dsl:
    level: DEBUG
    handlers: [console, file]
    propagate: false
root:
  level: INFO
  handlers: [console]
```

### 性能优化配置

对于大型项目，可以进行以下优化：

```yaml
# config/performance.yaml
performance:
  # 并发配置
  max_workers: 4
  
  # 缓存配置
  cache_enabled: true
  cache_size: 1000
  
  # 超时配置
  default_timeout: 30
  max_timeout: 300
  
  # 重试配置
  default_retries: 3
  max_retries: 10
```

## 下一步

现在您已经成功安装和配置了pytest-dsl，可以继续学习：

1. **[第一个测试](./first-test)** - 创建更复杂的测试用例
2. **[DSL语法基础](./dsl-syntax)** - 深入学习DSL语法
3. **[HTTP API测试](./http-testing)** - 开始API测试之旅

如果在安装过程中遇到问题，请在[GitHub Issues](https://github.com/felix-1991/pytest-dsl/issues)中寻求帮助。 