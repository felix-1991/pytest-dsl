from core.keyword_manager import keyword_manager

@keyword_manager.register('API接口调用', [
    {'name': '方法', 'mapping': 'method', 'description': 'HTTP请求方法'},
    {'name': 'URL', 'mapping': 'url', 'description': '请求的URL地址'},
    {'name': '请求头', 'mapping': 'headers', 'description': '请求头信息'},
    {'name': '请求参数', 'mapping': 'params', 'description': '请求参数'},
    {'name': '响应参数', 'mapping': 'response', 'description': '预期的响应参数'}
])
def api_call(**kwargs):
    # API调用实现
    method = kwargs.get('method')
    url = kwargs.get('url')
    headers = kwargs.get('headers')
    params = kwargs.get('params')
    response = kwargs.get('response')
    print(f"API接口调用: method={method}, url={url}, headers={headers}, params={params}, response={response}")


@keyword_manager.register('API请求', [
    {'name': '内容', 'mapping': 'content', 'description': 'YAML-like的请求定义内容'},
    {'name': '函数文件', 'mapping': 'func_file', 'description': '可选的测试数据函数文件'}
])
def api_request(**kwargs):
    # API请求实现
    content = kwargs.get('content')
    func_file = kwargs.get('func_file', None)
    print(f"API请求: content={content}, func_file={func_file}")
