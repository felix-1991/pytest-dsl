import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


def test_readme_is_an_api_first_product_page():
    content = README.read_text(encoding="utf-8")
    required = [
        "## 为什么是 pytest-dsl",
        "## 一个关键字开始接口测试",
        "[HTTP请求]",
        "allure.step",
        "## 从 DSL 到可读报告",
        "## Pytest DSL Studio",
        "examples/gui_validation/tests/api_quickstart.dsl",
    ]
    for marker in required:
        assert marker in content
    assert len(content.splitlines()) < 500


def test_readme_positions_custom_keywords_for_end_to_end_testing():
    content = README.read_text(encoding="utf-8")
    section_match = re.search(
        r"^## 从接口测试扩展到端到端\n(?P<body>.*?)(?=^## |\Z)",
        content,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert section_match is not None, (
        "README is missing the '## 从接口测试扩展到端到端' section"
    )
    section = section_match.group("body")
    required = [
        "类似 Robot Framework 的关键字驱动扩展方式",
        "function ... do ... end",
        ".resource",
        "不兼容 Robot Framework 的语法",
        "需要团队提供对应驱动",
    ]

    for marker in required:
        assert marker in section


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
