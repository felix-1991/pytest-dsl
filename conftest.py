import pytest
from pathlib import Path

def pytest_collect_file(parent, file_path):
    if file_path.suffix == ".auto" and file_path.name.startswith("test"):
        return AutoFile.from_parent(parent, path=file_path)

class AutoFile(pytest.File):
    def collect(self):
        yield AutoItem.from_parent(self, name=self.path.stem)

class AutoItem(pytest.Item):
    def runtest(self):
        from execute import execute, read_file, get_lexer, get_parser
        lexer = get_lexer()
        parser = get_parser()
        dsl_code = read_file(str(self.path))
        ast = parser.parse(dsl_code, lexer=lexer)
        execute(ast)

    def reportinfo(self):
        return self.fspath, 0, f"DSL Test: {self.name}"