# README General Testing Framework Positioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the README around pytest-dsl as a general keyword-driven automation framework while keeping API testing as the fastest, best-supported entry path.

**Architecture:** Change the README contract first, then reorganize the product narrative around four layers: DSL expression, keyword extension, built-in HTTP capability, and shared execution/report tooling. Preserve the verified API quickstart and screenshots, but describe them as concrete examples rather than the framework boundary.

**Tech Stack:** Markdown, pytest, Python `re`, existing README validation scripts

---

### Task 1: Replace the API-first README contract

**Files:**
- Modify: `tests/test_readme_product_page.py`
- Test: `tests/test_readme_product_page.py`

- [ ] **Step 1: Replace the old product-positioning test**

Replace `test_readme_is_an_api_first_product_page` with:

```python
def test_readme_positions_a_general_framework_with_an_api_entry_path():
    content = README.read_text(encoding="utf-8")
    required = [
        "# pytest-dsl：用关键字组织从接口到端到端的自动化测试",
        "通用自动化测试框架",
        "API 测试是最容易上手、内置能力最完整的实践入口",
        "框架边界并不限定测试类型",
        "## 为什么是 pytest-dsl",
        "## 框架如何工作",
        "## 从 API 开始：一个关键字完成请求链路",
        "## 扩展到复杂测试与端到端",
        "## 从执行结构到可读报告",
        "## Pytest DSL Studio：统一的 DSL 工作台",
        "examples/gui_validation/tests/api_quickstart.dsl",
    ]
    for marker in required:
        assert marker in content

    headings = [
        "## 为什么是 pytest-dsl",
        "## 框架如何工作",
        "## 从 API 开始：一个关键字完成请求链路",
        "## 扩展到复杂测试与端到端",
        "## 从执行结构到可读报告",
        "## Pytest DSL Studio：统一的 DSL 工作台",
        "## 5 分钟：从 API 用例开始",
        "## 核心能力",
    ]
    assert [content.index(heading) for heading in headings] == sorted(
        content.index(heading) for heading in headings
    )

    core_headings = [
        "### DSL 测试表达",
        "### 关键字扩展与组合",
        "### HTTP/API 测试",
        "### 执行、报告与工具",
    ]
    assert [content.index(heading) for heading in core_headings] == sorted(
        content.index(heading) for heading in core_headings
    )
    assert "## 一个关键字开始接口测试" not in content
    assert len(content.splitlines()) < 500
```

- [ ] **Step 2: Update the end-to-end contract for the new section name and position**

In `test_readme_positions_custom_keywords_for_end_to_end_testing`, use:

```python
def test_readme_positions_custom_keywords_for_end_to_end_testing():
    content = README.read_text(encoding="utf-8")
    section_heading = "## 扩展到复杂测试与端到端"
    section_match = re.search(
        r"^## 扩展到复杂测试与端到端\n(?P<body>.*?)(?=^## |\Z)",
        content,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert section_match is not None, (
        "README is missing the '## 扩展到复杂测试与端到端' section"
    )
    section = section_match.group("body")
    required = [
        "类似 Robot Framework 的关键字驱动扩展方式",
        "function ... do ... end",
        ".resource",
        "项目 `keywords/`",
        "Python 注册机制",
        "插件或 XML-RPC 远程服务",
        "现有 Python 库和外部驱动",
        "团队自定义的页面操作关键字",
        "团队自定义的数据校验关键字",
        "浏览器、移动端、数据库、消息队列等领域能力",
        "并非全部由 pytest-dsl 内置",
        "pytest 的收集、插件和命令行生态",
        "不兼容 Robot Framework 的语法、库接口或现有用例",
        "不是 Robot Framework 的直接替代品",
    ]
    for marker in required:
        assert marker in section

    assert "fixture" not in section.lower()
    assert (
        content.index("## 从 API 开始：一个关键字完成请求链路")
        < content.index(section_heading)
        < content.index("## 从执行结构到可读报告")
    )
    assert (
        "- 内置 HTTP 关键字可以与 DSL、Python、插件或远程自定义关键字组合，"
        "组织跨接口和外部驱动的端到端业务流程。"
    ) in content
```

- [ ] **Step 3: Run the focused tests and confirm the old README fails the new contract**

Run:

```bash
python -m pytest tests/test_readme_product_page.py::test_readme_positions_a_general_framework_with_an_api_entry_path tests/test_readme_product_page.py::test_readme_positions_custom_keywords_for_end_to_end_testing -q
```

Expected: both tests fail because the README still contains the old title, headings, section order, and capability order.

- [ ] **Step 4: Commit the failing contract**

```bash
git add tests/test_readme_product_page.py
git commit -m "test: define general framework README contract"
```

### Task 2: Rebuild the README narrative

**Files:**
- Modify: `README.md`
- Test: `tests/test_readme_product_page.py`

- [ ] **Step 1: Rewrite the title and opening position**

Use this opening before `## 为什么是 pytest-dsl`:

```markdown
# pytest-dsl：用关键字组织从接口到端到端的自动化测试

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://python.org)
[![PyPI Version](https://img.shields.io/pypi/v/pytest-dsl.svg)](https://pypi.org/project/pytest-dsl/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

pytest-dsl 是一个基于 pytest 的关键字驱动通用自动化测试框架。它用 DSL 统一表达测试步骤、参数、变量、控制流和关键字调用，让测试过程更接近业务语言，同时保留 Python 与 pytest 生态的扩展能力。

API 测试是最容易上手、内置能力最完整的实践入口：一个 `[HTTP请求]` 关键字即可组合请求、捕获、断言、会话和 Allure 记录。但框架边界并不限定测试类型；团队可以把浏览器、移动端、数据库、消息队列或内部工具封装为关键字，继续组织集成测试、复杂业务流程和端到端测试。

- **统一表达**：接口调用、页面操作、数据核验和环境清理都可以成为可读的 DSL 业务步骤。
- **分层扩展**：简单流程在 DSL 中组合，技术能力通过 Python、插件或远程关键字接入。
- **同一执行核心**：命令行、pytest 原生收集、Allure 报告和 Pytest DSL Studio 使用同一套 DSL 文件。
```

Keep the existing badge Markdown unchanged.

- [ ] **Step 2: Replace the API-specific “why” comparison with the framework model**

Use these two sections:

```markdown
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
```

- [ ] **Step 3: Retain the verified quickstart under an API-entry heading**

Rename `## 一个关键字开始接口测试` to:

```markdown
## 从 API 开始：一个关键字完成请求链路
```

Replace its introductory parameter inventory with:

```markdown
API 测试适合作为第一条实践路径，因为 `[HTTP请求]` 已经把 requests 调用、字段捕获、断言、命名会话、模板复用、失败重试和 Allure 附件组合在一个内置关键字中。安装 pytest-dsl 后，无需先实现请求客户端、字段提取器或报告包装器，就可以直接描述完整请求链路。

下面的可运行示例连续完成用户查询、登录、令牌传递和账户校验，最后使用通用 `[断言]` 汇总校验跨请求变量：
```

Keep the existing `api_quickstart.dsl` fenced block byte-for-byte identical so `test_readme_embeds_the_runnable_api_quickstart_without_drift` remains meaningful. Keep the source link and local mock API statement immediately after it.

- [ ] **Step 4: Rename and tighten the end-to-end section**

Replace the section with:

```markdown
## 扩展到复杂测试与端到端

API 只是内置能力最完整的起点。关键字模型可以继续承载跨系统、跨技术栈的复杂测试：用例在 DSL 中描述业务流程，具体技术动作封装在可复用关键字中。这种组织方式类似 Robot Framework 的关键字驱动扩展思路。

团队可以用 `function ... do ... end` 在 DSL 中组合业务关键字，用 `.resource` 文件跨用例复用，也可以通过项目 `keywords/`、Python 注册机制、插件或 XML-RPC 远程服务提供关键字。Python 关键字可以调用现有 Python 库和外部驱动，因此一个流程可以按以下方式组合：

`内置 [HTTP请求] → 团队自定义的页面操作关键字 → 团队自定义的数据校验关键字 → 通用断言和清理步骤`

这使接口准备、界面操作、后台核验和环境收尾可以使用同一套 DSL 业务步骤组织成端到端用例。浏览器、移动端、数据库、消息队列等领域能力需要团队提供对应驱动，并非全部由 pytest-dsl 内置。

这里的“类似”只指关键字驱动的组织和扩展方式。pytest-dsl 基于 pytest，继续使用 pytest 的收集、插件和命令行生态；它不兼容 Robot Framework 的语法、库接口或现有用例，也不是 Robot Framework 的直接替代品。
```

- [ ] **Step 5: Generalize the report and Studio sections**

Rename the report heading to `## 从执行结构到可读报告` and begin with:

```markdown
pytest-dsl 的报告层级来自真实执行结构，而不是运行结束后重新拼装文本。无论关键字执行的是 HTTP 请求、页面操作还是数据核验，DSL 中的用例名称、关键字调用和 `步骤名称` 都会形成对应的报告层级。

以仓库中的 API quickstart 为例，pytest 原生收集生成的 Allure 结果实际包含：
```

Rename the Studio heading to `## Pytest DSL Studio：统一的 DSL 工作台` and use this introduction:

```markdown
Pytest DSL Studio 是仓库中的 Electron 桌面工作台，用于浏览、编辑、运行和调试 DSL 项目；它服务于同一套通用 DSL 与关键字体系，不是 pytest-dsl 的必需运行时。
```

Rename the two screenshot subheadings to `### 编辑 DSL 用例（以 API 为例）` and `### 运行 DSL 用例（以 API 为例）`.

- [ ] **Step 6: Rename the quickstart and reorder core capabilities**

Rename `## 5 分钟运行 API 示例` to:

```markdown
## 5 分钟：从 API 用例开始
```

Replace the core-capability section with these headings in this order, moving the existing accurate bullets under the matching heading and removing duplication:

```markdown
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
```

- [ ] **Step 7: Run focused README tests**

Run:

```bash
python -m pytest tests/test_readme_product_page.py -q
```

Expected: all tests in `tests/test_readme_product_page.py` pass.

- [ ] **Step 8: Commit the README rebuild**

```bash
git add README.md
git commit -m "docs: position pytest-dsl as a general test framework"
```

### Task 3: Verify the rewritten product page

**Files:**
- Verify: `README.md`
- Verify: `tests/test_readme_product_page.py`

- [ ] **Step 1: Run README validation**

Run:

```bash
python examples/readme_validation/run_all_tests.py --skip-remote
```

Expected: zero README example or link failures.

- [ ] **Step 2: Run the complete pytest suite**

Run:

```bash
python -m pytest -q
```

Expected: the suite exits with code 0.

- [ ] **Step 3: Check Markdown diff hygiene**

Run:

```bash
git diff --check HEAD~2..HEAD
```

Expected: no output.

- [ ] **Step 4: Inspect final scope**

Run:

```bash
git status --short
git log -3 --oneline
```

Expected: clean worktree; latest commits are the README implementation, the failing contract, and the approved design document.
