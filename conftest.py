import pytest
from pathlib import Path
from execute import DSLExecutor, read_file, get_lexer, get_parser

lexer = get_lexer()
parser = get_parser()


def pytest_collect_file(parent, file_path):
    if file_path.suffix == ".auto" and file_path.name.startswith("test"):
        return AutoFile.from_parent(parent, path=file_path)

class AutoFile(pytest.File):
    def collect(self):
        yield AutoItem.from_parent(self, name=self.path.stem)

class AutoItem(pytest.Item):
    def runtest(self):
        dsl_code = read_file(str(self.path))
        ast = parser.parse(dsl_code, lexer=lexer)
        executor = DSLExecutor()
        executor.execute(ast)

    def reportinfo(self):
        return self.fspath, 0, f"DSL Test: {self.name}"


# 定义全局前置和后置fixture
@pytest.fixture(scope="module", autouse=True)
def auto_setup_teardown(request):
    # 获取当前测试模块的目录
    module_path = Path(request.fspath).parent
    setup_file = module_path / "setup.auto"
    teardown_file = module_path / "teardown.auto"

    # 执行setup.auto（前置操作）
    if setup_file.exists():
        print(f"Running setup: {setup_file}")
        # 占位符：实际中这里需要解析和执行DSL语法
        dsl_code = read_file(str(setup_file))
        ast = parser.parse(dsl_code, lexer=lexer)
        executor = DSLExecutor()
        executor.execute(ast)

    yield  # 执行测试

    # 执行teardown.auto（后置操作）
    if teardown_file.exists():
        print(f"Running teardown: {teardown_file}")
        dsl_code = read_file(str(teardown_file))
        ast = parser.parse(dsl_code, lexer=lexer)
        executor = DSLExecutor()
        executor.execute(ast)