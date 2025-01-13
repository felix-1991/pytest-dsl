import pytest
import allure
from main import get_lexer, get_parser, execute

def pytest_collect_file(parent, file_path):
    if file_path.suffix == ".auto":
        return AutoFile.from_parent(parent, path=file_path)

class AutoFile(pytest.File):
    def collect(self):
        lexer = get_lexer()
        parser = get_parser()
        
        with open(self.fspath, 'r', encoding='utf-8') as f:
            content = f.read()
            ast = parser.parse(content, lexer=lexer)
            
            metadata = next((n for n in ast.children if n.type == 'Metadata'), None)
            if metadata:
                title = None
                description = None
                tags = []
                for item in metadata.children:
                    if item.type == '@name':
                        title = item.value
                    elif item.type == '@description':
                        description = item.value
                    elif item.type == '@tags':
                        tags.extend(tag.value for tag in item.value)
                    elif item.type == '@author':
                        allure.dynamic.label("author", item.value)
                    elif item.type == '@date':
                        allure.dynamic.label("date", item.value)
                
                item = AutoItem.from_parent(
                    self,
                    name=self.fspath.basename,
                    ast=ast,
                    title=title,
                    description=description,
                    tags=tags
                )
                if title:
                    item.add_marker(pytest.mark.allure_title(title))
                if description:
                    item.add_marker(pytest.mark.allure_description(description))
                for tag in tags:
                    item.add_marker(pytest.mark.tag(tag))
                yield item

class AutoItem(pytest.Item):
    def __init__(self, name, parent, ast, title=None, description=None, tags=None):
        super().__init__(name, parent)
        self.ast = ast
        self.title = title
        self.description = description
        self.tags = tags

    def runtest(self):
        with allure.step("Execute test steps"):
            execute(self.ast)
            
    def repr_failure(self, excinfo):
        return str(excinfo.value)

    def reportinfo(self):
        return self.fspath, 0, f"Auto test: {self.name}"