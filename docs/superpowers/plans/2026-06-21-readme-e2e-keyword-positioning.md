# README End-to-End Keyword Positioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an evidence-backed README section explaining that pytest-dsl can compose custom keywords into end-to-end flows through a keyword-driven extension model similar to Robot Framework.

**Architecture:** Keep API testing as the primary product entry point, then add one bounded section between report readability and Studio. Pin the positioning with a README regression test so future edits retain both the supported extension mechanisms and the explicit non-compatibility boundary.

**Tech Stack:** Markdown, pytest, Python `subprocess`, existing pytest-dsl README validation tests

---

### Task 1: Pin the end-to-end positioning contract

**Files:**
- Modify: `tests/test_readme_product_page.py`
- Test: `tests/test_readme_product_page.py`

- [ ] **Step 1: Write the failing README contract test**

Add this test after `test_readme_is_an_api_first_product_page`:

```python
def test_readme_positions_custom_keywords_for_end_to_end_testing():
    content = README.read_text(encoding="utf-8")
    section_heading = "## 从接口测试扩展到端到端"
    section_match = re.search(
        r"^## 从接口测试扩展到端到端\n(?P<body>.*?)(?=^## |\Z)",
        content,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert section_match is not None
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
    corrected_ecosystem_claims = (
        "- Python 关键字、pytest 插件和命令行生态仍可继续使用。",
        "- pytest 原生 `.dsl` / `.auto` 收集、插件和命令行生态。",
    )
    misleading_fixture_claims = (
        "Python 关键字、pytest 插件、fixture 和命令行生态仍可继续使用。",
        "pytest 原生 `.dsl` / `.auto` 收集、fixture 和插件生态。",
    )
    for claim in corrected_ecosystem_claims:
        assert claim in content
    for claim in misleading_fixture_claims:
        assert claim not in content

    assert (
        content.index("## 从 DSL 到可读报告")
        < content.index(section_heading)
        < content.index("## Pytest DSL Studio")
    )
    assert (
        "- 内置 HTTP 关键字可以与 DSL、Python、插件或远程自定义关键字组合，"
        "组织跨接口和外部驱动的端到端业务流程。"
    ) in content
```

- [ ] **Step 2: Run the test to verify the contract is missing**

Run:

```bash
python -m pytest tests/test_readme_product_page.py::test_readme_positions_custom_keywords_for_end_to_end_testing -q
```

Expected: FAIL because `README.md` does not yet contain `## 从接口测试扩展到端到端`.

### Task 2: Add the bounded end-to-end section

**Files:**
- Modify: `README.md`
- Test: `tests/test_readme_product_page.py`

- [ ] **Step 1: Add the section after “从 DSL 到可读报告” and before “Pytest DSL Studio”**

Insert this Markdown after the Allure report screenshot:

```markdown
## 从接口测试扩展到端到端

接口测试是 pytest-dsl 最直接的切入点，但关键字模型并不限定测试边界。pytest-dsl 提供类似 Robot Framework 的关键字驱动扩展方式：用例在 DSL 中描述业务流程，具体技术动作封装在可复用关键字中。

团队可以用 `function ... do ... end` 在 DSL 中组合业务关键字，用 `.resource` 文件跨用例复用，也可以通过项目 `keywords/`、Python 注册机制、插件或 XML-RPC 远程服务提供关键字。Python 关键字可以调用现有 Python 库和外部驱动，因此一个流程可以按以下方式组合：

`内置 [HTTP请求] → 团队自定义的页面操作关键字 → 团队自定义的数据校验关键字 → 通用断言和清理步骤`

这使接口准备、界面操作、后台核验和环境收尾可以使用同一套 DSL 业务步骤组织成端到端用例。浏览器、移动端、数据库、消息队列等领域能力需要团队提供对应驱动，并非全部由 pytest-dsl 内置。

这里的“类似”指关键字驱动的组织和扩展方式。pytest-dsl 基于 pytest，继续使用 pytest 的收集、插件和命令行生态；它不兼容 Robot Framework 的语法、库接口或现有用例，也不是 Robot Framework 的直接替代品。
```

- [ ] **Step 2: Correct the two existing pytest ecosystem claims**

Replace:

```markdown
- Python 关键字、pytest 插件、fixture 和命令行生态仍可继续使用。
```

with:

```markdown
- Python 关键字、pytest 插件和命令行生态仍可继续使用。
```

Replace:

```markdown
- pytest 原生 `.dsl` / `.auto` 收集、fixture 和插件生态。
```

with:

```markdown
- pytest 原生 `.dsl` / `.auto` 收集、插件和命令行生态。
```

- [ ] **Step 3: Add one core-capability bullet**

Under `### 扩展与集成`, add:

```markdown
- 内置 HTTP 关键字可以与 DSL、Python、插件或远程自定义关键字组合，组织跨接口和外部驱动的端到端业务流程。
```

- [ ] **Step 4: Run the focused README tests**

Run:

```bash
python -m pytest tests/test_readme_product_page.py -q
```

Expected: all tests in `tests/test_readme_product_page.py` PASS.

- [ ] **Step 5: Run documentation and full-suite verification**

Run:

```bash
python examples/readme_validation/run_all_tests.py --skip-remote
python -m pytest -q
git diff --check
```

Expected: README validation reports zero failures, pytest reports zero failures, and `git diff --check` produces no output.

- [ ] **Step 6: Commit the implementation**

```bash
git add README.md tests/test_readme_product_page.py
git commit -m "docs: explain end-to-end keyword extensibility"
```
