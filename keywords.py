
# 定义参数结构
class Parameter:
    def __init__(self, name, mapping, description):
        self.name = name
        self.mapping = mapping
        self.description = description

# 注册关键字装饰器
keywords = {}

def register_keyword(name, parameters):
    def decorator(func):
        param_list = [Parameter(**p) for p in parameters]
        mapping = {p.name: p.mapping for p in param_list}
        keywords[name] = {
            'func': func,
            'mapping': mapping,
            'parameters': param_list
        }
        return func
    return decorator

# 1. [打印内容] 关键字
@register_keyword('打印内容', [
    {'name': '内容', 'mapping': 'content', 'description': '要打印的文本内容，支持多行字符串'}
])
def print_content(**kwargs):
    content = kwargs.get('content')
    print(f"内容: {content}")

# 2. [API接口调用] 关键字
@register_keyword('API接口调用', [
    {'name': '方法', 'mapping': 'method', 'description': 'HTTP请求方法，如GET或POST'},
    {'name': 'URL', 'mapping': 'url', 'description': '请求的URL地址'},
    {'name': '请求头', 'mapping': 'headers', 'description': '请求头信息，JSON格式'},
    {'name': '请求参数', 'mapping': 'params', 'description': '请求参数，JSON格式'},
    {'name': '响应参数', 'mapping': 'response', 'description': '预期的响应参数，JSON格式'}
])
def api_call(**kwargs):
    method = kwargs.get('method')
    url = kwargs.get('url')
    headers = kwargs.get('headers')
    params = kwargs.get('params')
    response = kwargs.get('response')
    print(f"API接口调用: method={method}, url={url}, headers={headers}, params={params}, response={response}")

# 3. [返回结果] 关键字
@register_keyword('返回结果', [
    {'name': '结果', 'mapping': 'result', 'description': '要返回的数值或字符串'}
])
def return_result(**kwargs):
    result = kwargs.get('result')
    return result

# 4. [API请求] 关键字
@register_keyword('API请求', [
    {'name': '内容', 'mapping': 'content', 'description': 'YAML-like的请求定义内容'},
    {'name': '函数文件', 'mapping': 'func_file', 'description': '可选，用于指定生成测试数据的函数文件'}
])
def api_request(**kwargs):
    content = kwargs.get('content')
    func_file = kwargs.get('func_file', None)
    print(f"API请求: content={content}, func_file={func_file}")
    # 这里可以添加实际的API请求逻辑，例如解析content并发送请求

# 可选：生成文档
def generate_docs():
    for name, keyword in keywords.items():
        print(f"关键字: {name}")
        print("参数:")
        for param in keyword['parameters']:
            print(f"  {param.name} ({param.mapping}): {param.description}")
        print()

if __name__ == '__main__':
    generate_docs()