import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


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


def test_readme_references_the_three_verified_screenshots():
    content = README.read_text(encoding="utf-8")
    for name in (
        "studio-api-editor.png",
        "studio-api-run.png",
        "allure-api-report.png",
    ):
        assert f"docs/images/readme/{name}" in content


def test_readme_embeds_the_runnable_api_quickstart_without_drift():
    content = README.read_text(encoding="utf-8")
    example = (
        ROOT / "examples" / "gui_validation" / "tests" / "api_quickstart.dsl"
    ).read_text(encoding="utf-8")

    assert f"```python\n{example.rstrip()}\n```" in content


def test_readme_local_links_and_images_exist():
    content = README.read_text(encoding="utf-8")
    targets = re.findall(r"!?\[[^]]*\]\(([^)]+)\)", content)
    missing = []
    for raw_target in targets:
        target = raw_target.strip().split("#", 1)[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        if not (ROOT / target).resolve().exists():
            missing.append(raw_target)
    assert missing == []


def test_gui_validation_only_exposes_the_api_showcase_to_git():
    def is_ignored(path: str) -> bool:
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "-q", path],
            cwd=ROOT,
            check=False,
        )
        return result.returncode == 0

    public_showcase = (
        "examples/gui_validation/README.md",
        "examples/gui_validation/config/api.yaml",
        "examples/gui_validation/tests/api_quickstart.dsl",
        "examples/gui_validation/tools/mock_api_server.py",
    )
    local_validation_assets = (
        "examples/gui_validation/config/app.yaml",
        "examples/gui_validation/keywords/local_keyword.py",
        "examples/gui_validation/resources/local.resource",
        "examples/gui_validation/tests/remote_gui_smoke.dsl",
        "examples/gui_validation/tests/local_suite/example.dsl",
    )

    assert all(not is_ignored(path) for path in public_showcase)
    assert all(is_ignored(path) for path in local_validation_assets)
