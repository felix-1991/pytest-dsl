# pytest-dsl：用关键字组织从接口到端到端的自动化测试

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://python.org)
[![PyPI Version](https://img.shields.io/pypi/v/pytest-dsl.svg)](https://pypi.org/project/pytest-dsl/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

pytest-dsl 是一个基于 pytest 的关键字驱动通用自动化测试框架。它用 DSL 统一表达测试步骤、参数、变量、控制流和关键字调用，让测试过程更接近业务语言，同时保留 Python 与 pytest 生态的扩展能力。

API 测试是最容易上手、内置能力最完整的实践入口：一个 `[HTTP请求]` 关键字即可组合请求、捕获、断言、会话和 Allure 记录。但框架边界并不限定测试类型；团队可以把浏览器、移动端、数据库、消息队列或内部工具封装为关键字，继续组织集成测试、复杂业务流程和端到端测试。

- **统一表达**：接口调用、页面操作、数据核验和环境清理都可以成为可读的 DSL 业务步骤。
- **分层扩展**：简单流程在 DSL 中组合，技术能力通过 Python、插件或远程关键字接入。
- **同一执行核心**：命令行、pytest 原生收集、Allure 报告和 Pytest DSL Studio 使用同一套 DSL 文件。

## 为什么是 pytest-dsl

自动化测试从单个技术动作发展到完整业务流程后，维护成本通常不只来自驱动代码，还来自表达方式不统一：步骤边界依赖编写习惯，公共流程散落在测试代码中，业务名称与报告层级也容易脱节。

pytest-dsl 在 pytest 之上增加统一的测试表达层：

- 用固定 DSL 描述用例元信息、变量、控制流、数据驱动、setup、teardown 和关键字调用；
- 用关键字隔离业务意图与技术实现，关键字内部可以继续使用 Python 库和外部驱动；
- 用 `function ... do ... end` 和 `.resource` 组合、沉淀团队业务流程；
- 用 `步骤名称` 和真实关键字执行结构生成可读的 Allure 层级；
- 继续使用 pytest 的收集、插件、命令行和既有工程能力。

这不是替代 pytest，而是让不同类型的自动化测试使用同一种业务可读、可扩展的组织方式。

## 框架如何工作

pytest-dsl 将“测试流程”和“技术动作”分开：

`DSL 业务流程 → 内置或自定义关键字 → Python 库与外部驱动 → pytest 执行 → Allure 报告`

关键字可以来自四个层次：

1. pytest-dsl 内置的 HTTP、断言、变量和通用工具关键字；
2. 在 DSL 中通过 `function ... do ... end` 定义的业务关键字；
3. 项目 `keywords/`、Python 注册机制或 pytest-dsl 插件提供的领域关键字；
4. 通过 XML-RPC 服务运行在其他进程或环境中的远程关键字。

因此，测试人员可以在 DSL 中关注业务流程，熟悉 Python 或具体驱动的成员负责沉淀底层关键字。关键字实现变化时，用例的业务结构和报告名称无需随之重写。

## 从 API 开始：一个关键字完成请求链路

API 测试适合作为第一条实践路径，因为 `[HTTP请求]` 已经把 requests 调用、字段捕获、断言、命名会话、模板复用、失败重试和 Allure 附件组合在一个内置关键字中。安装 pytest-dsl 后，无需先实现请求客户端、字段提取器或报告包装器，就可以直接描述完整请求链路。

下面的可运行示例连续完成用户查询、登录、令牌传递和账户校验，最后使用通用 `[断言]` 汇总校验跨请求变量：

```python
@name: "接口测试核心链路：查询用户、登录并校验账户"
@description: "使用一个内置 HTTP请求 关键字完成请求、捕获、断言和变量传递"
@tags: ["api", "http", "quickstart"]

[HTTP请求], 客户端: "local_api", 配置: '''
    method: GET
    url: /api/users/${api_demo.user_id}
    captures:
        user_id: ["jsonpath", "$.data.id"]
        username: ["jsonpath", "$.data.username"]
        user_role: ["jsonpath", "$.data.role"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.code", "eq", 0]
        - ["jsonpath", "$.data.role", "eq", "tester"]
''', 步骤名称: "查询接口测试用户"

[HTTP请求], 客户端: "local_api", 配置: '''
    method: POST
    url: /api/sessions
    request:
        headers:
            Content-Type: application/json
        json:
            username: "${username}"
            password: "${api_demo.password}"
    captures:
        access_token: ["jsonpath", "$.data.access_token"]
        login_user_id: ["jsonpath", "$.data.user_id"]
    asserts:
        - ["status", "eq", 201]
        - ["jsonpath", "$.code", "eq", 0]
        - ["jsonpath", "$.data.user_id", "eq", ${user_id}]
''', 步骤名称: "登录并捕获访问令牌"

[HTTP请求], 客户端: "local_api", 配置: '''
    method: GET
    url: /api/users/${login_user_id}/profile
    request:
        headers:
            Authorization: "Bearer ${access_token}"
    captures:
        account_active: ["jsonpath", "$.data.active"]
        account_plan: ["jsonpath", "$.data.plan"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.data.active", "eq", true]
        - ["jsonpath", "$.data.plan", "eq", "team"]
''', 步骤名称: "携带令牌查询账户状态"

[断言], 条件: "${account_active} == True", 消息: "账户应该处于启用状态"
[打印], 内容: "接口测试核心链路验证完成：用户=${username}，角色=${user_role}，套餐=${account_plan}"
```

可运行源码位于 [`examples/gui_validation/tests/api_quickstart.dsl`](examples/gui_validation/tests/api_quickstart.dsl)。仓库提供本地 mock API，因此这个示例不依赖公网服务。

## 扩展到复杂测试与端到端

API 只是内置能力最完整的起点。关键字模型可以继续承载跨系统、跨技术栈的复杂测试。pytest-dsl 提供类似 Robot Framework 的关键字驱动扩展方式：用例在 DSL 中描述业务流程，具体技术动作封装在可复用关键字中。

团队可以用 `function ... do ... end` 在 DSL 中组合业务关键字，用 `.resource` 文件跨用例复用，也可以通过项目 `keywords/`、Python 注册机制、插件或 XML-RPC 远程服务提供关键字。Python 关键字可以调用现有 Python 库和外部驱动，因此一个流程可以按以下方式组合：

`内置 [HTTP请求] → 团队自定义的页面操作关键字 → 团队自定义的数据校验关键字 → 通用断言和清理步骤`

这使接口准备、界面操作、后台核验和环境收尾可以使用同一套 DSL 业务步骤组织成端到端用例。浏览器、移动端、数据库、消息队列等领域能力需要团队提供对应驱动，并非全部由 pytest-dsl 内置。

这里的“类似”只指关键字驱动的组织和扩展方式。pytest-dsl 基于 pytest，继续使用 pytest 的收集、插件和命令行生态；它不兼容 Robot Framework 的语法、库接口或现有用例，也不是 Robot Framework 的直接替代品。

## 从执行结构到可读报告

pytest-dsl 的报告层级来自真实执行结构，而不是运行结束后重新拼装文本。无论关键字执行的是 HTTP 请求、页面操作还是数据核验，DSL 中的用例名称、关键字调用和 `步骤名称` 都会形成对应的报告层级。

以仓库中的 API quickstart 为例，pytest 原生收集生成的 Allure 结果实际包含：

1. 顶层用例：`接口测试核心链路：查询用户、登录并校验账户`。
2. 每次 `调用关键字: HTTP请求` 下记录客户端、配置和步骤名称参数解析。
3. `步骤名称` 指定的业务步骤，例如 `登录并捕获访问令牌`。
4. 业务步骤内的 `发送HTTP请求 (客户端: local_api)` 和 `执行断言验证`。
5. `HTTP请求摘要`、`HTTP响应摘要`、`变量捕获摘要` 和 `HTTP断言摘要` 附件。

因此，测试设计中的业务步骤、执行过程和报告阅读顺序保持一致。请求或断言失败时，异常会落在对应关键字和子步骤中，而不是只留下一个缺少上下文的函数失败。

![DSL API 用例在 Allure 中形成分层步骤](docs/images/readme/allure-api-report.png)

## Pytest DSL Studio：统一的 DSL 工作台

Pytest DSL Studio 是仓库中的 Electron 桌面工作台，用于浏览、编辑、运行和调试 DSL 项目；它服务于同一套通用 DSL 与关键字体系，不是 pytest-dsl 的必需运行时。

当前工作台提供：

- 递归项目树和 CodeMirror 6 编辑器；
- DSL 关键字检索、插入和定义跳转；
- 语法检查、文件运行和交互式调试；
- 测试集选择及 pytest 构建执行；
- 基于 `--alluredir` 的构建产物和内嵌 Allure 实时报告；
- 运行输出、构建日志和报告导出。

### 编辑 DSL 用例（以 API 为例）

![在 Pytest DSL Studio 中编辑 API 用例](docs/images/readme/studio-api-editor.png)

### 运行 DSL 用例（以 API 为例）

![在 Pytest DSL Studio 中运行 API 用例](docs/images/readme/studio-api-run.png)

命令行适合 CI 和批量执行，Studio 适合本地编写、排错和查看报告；二者使用同一套 DSL 文件和 pytest-dsl 执行能力。

## 5 分钟：从 API 用例开始

### 1. 安装 pytest-dsl

```bash
pip install pytest-dsl
```

当前版本要求 Python 3.9 或更高版本。

### 2. 启动仓库内的 mock API

克隆仓库后，在仓库根目录执行：

```bash
python examples/gui_validation/tools/mock_api_server.py
```

服务默认监听 `http://127.0.0.1:8765/`。

### 3. 运行 DSL

另开终端：

```bash
cd examples/gui_validation
pytest-dsl tests/api_quickstart.dsl --yaml-vars config/api.yaml
```

### 4. 生成 Allure 结果

```bash
python -m pytest tests/api_quickstart.dsl \
  --yaml-vars config/api.yaml \
  --alluredir allure-results -q
```

### 5. 可选：启动 Studio

Node.js 20 或更高版本是 Studio 的开发运行环境要求：

```bash
npm install --prefix electron-gui
npm start --prefix electron-gui
```

在 Studio 中打开 `examples/gui_validation`，选择 `config/api.yaml`，再打开 `tests/api_quickstart.dsl`。构建页的内嵌实时报告需要本机可用的 Allure 3 CLI。

#### 项目运行环境与外部依赖

打包版 Studio 不会内置 Python、pytest-dsl 或 Allure。项目优先使用根目录 `.venv`/`venv` 中已安装 pytest-dsl 与测试依赖的解释器；也可以在顶部”配置 → 运行环境”中为当前项目选择 Python。Allure 3 是外部依赖，用于实时报告和 HTML 报告导出，可在同一区域选择其可执行文件。

更完整的项目说明见 [`examples/gui_validation/README.md`](examples/gui_validation/README.md)。

## 核心能力

### DSL 测试表达

- 变量、列表、字典及嵌套访问。
- `if / elif / else`、`for`、`while`、`break` 和 `continue`。
- setup、teardown、重试块和数据驱动。
- 关键字参数、返回值、步骤名称和业务可读的执行层级。

### 关键字扩展与组合

- 使用 `function ... do ... end` 定义 DSL 业务关键字，并通过 `.resource` 文件跨用例复用。
- Python 装饰器注册自定义关键字，并声明参数、默认值、分类和返回值。
- 项目 `keywords/`、pytest-dsl 插件和 XML-RPC 远程服务提供领域能力。
- 内置 HTTP 关键字可以与 DSL、Python、插件或远程自定义关键字组合，组织跨接口和外部驱动的端到端业务流程。

### HTTP/API 测试

- YAML 请求配置，支持查询参数、请求头、JSON、表单、文件、Cookie、超时、跳转、证书和代理等 requests 参数。
- JSONPath、XPath、正则、响应头、Cookie、状态码、响应体和响应时间捕获。
- 状态码、JSONPath、响应头、响应体、响应时间和 JSON Schema 等断言组合。
- 客户端配置、认证提供者、命名会话、请求模板和断言重试。
- 请求、响应、捕获和断言的 Allure 摘要；敏感字段在公共报告辅助函数中脱敏。

### 执行、报告与工具

- pytest 原生 `.dsl` / `.auto` 收集、插件和命令行生态。
- Allure 报告按真实关键字调用和业务步骤记录执行结构。
- 命令行运行、Allure 结果和 Studio 工作台使用同一执行核心。
- Studio 提供项目浏览、编辑、语法检查、运行、调试、构建和报告查看能力。

## 文档

- [快速开始](docs/guide/getting-started.md)
- [HTTP 接口测试](docs/guide/http-testing.md)
- [DSL 语法](docs/guide/dsl-syntax.md)
- [自定义关键字](docs/guide/custom-keywords.md)
- [远程关键字](docs/guide/remote-keywords.md)
- [测试报告](docs/guide/reporting.md)
- [Studio API 验证项目](examples/gui_validation/README.md)

## 运行测试

```bash
python -m pytest
npm run check --prefix electron-gui
```

README 中的历史教程已移到专题文档。新增或修改首页示例时，应同时提供可运行文件和回归验证。

## 贡献

欢迎通过 [Issues](https://github.com/felix-1991/pytest-dsl/issues) 报告问题，或通过 [Pull Requests](https://github.com/felix-1991/pytest-dsl/pulls) 提交改进。

## 许可证

本项目使用 [MIT License](LICENSE)。
