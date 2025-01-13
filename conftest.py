import pytest
import allure
from main import get_lexer, get_parser, execute

def pytest_collect_file(parent, path):
    if path.ext == ".auto":
        return AutoFile.from_parent(parent, fspath=path)


class AutoFile(pytest.File):
    def collect(self):
        # Parse metadata
        lexer = get_lexer()
        parser = get_parser()
        
        with open(self.fspath, 'r', encoding='utf-8') as f:
            content = f.read()
            ast = parser.parse(content, lexer=lexer)
            
            # Find metadata node
            metadata = next((n for n in ast.children if n.type == 'Metadata'), None)
            if metadata:
                for item in metadata.children:
                    if item.type == '@name':
                        allure.dynamic.title(item.value)
                    elif item.type == '@description':
                        allure.dynamic.description(item.value)
                    elif item.type == '@tags':
                        for tag in item.value:
                            allure.tag(tag)
                            pytest.mark.marker(tag)
                    elif item.type == '@author':
                        allure.dynamic.label("author", item.value)
                    elif item.type == '@date':
                        allure.dynamic.label("date", item.value)
        
        yield AutoItem.from_parent(self, name=self.fspath.basename, ast=ast)

class AutoItem(pytest.Item):
    def __init__(self, name, parent, ast):
        super().__init__(name, parent)
        self.ast = ast

    def runtest(self):
        with allure.step("Execute test steps"):
            execute(self.ast)
            
    def repr_failure(self, excinfo):
        return str(excinfo.value)

    def reportinfo(self):
        return self.fspath, 0, f"Auto test: {self.name}"
