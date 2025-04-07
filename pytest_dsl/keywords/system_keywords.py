import allure
from pytest_dsl.core.keyword_manager import keyword_manager


@keyword_manager.register('打印', [
    {'name': '内容', 'mapping': 'content', 'description': '要打印的文本内容'}
])
def print_content(**kwargs):
    content = kwargs.get('content')
    print(f"内容: {content}")


@keyword_manager.register('返回结果', [
    {'name': '结果', 'mapping': 'result', 'description': '要返回的结果值'}
])
def return_result(**kwargs):
    return kwargs.get('result')
