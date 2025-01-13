from parser import get_parser, print_ast
from lexer import get_lexer


if __name__ == '__main__':
    lexer = get_lexer()
    parser = get_parser()

    dsl_code = """
    @name: 测试好用例
    @description: 这是一个测试用例
    @tags: [BVT, 自动化]
    @author: 陈双麟
    @date: 2021-08-10 14:30:00

    number = 5
    for i in range(1, ${number}) do
        [打印内容],内容: '第${i}次循环'
    end

    [API接口调用],方法:GET,URL:'https://www.baidu.com/1',请求头:'{"Content-Type": "application/json"}',请求参数:'{}',响应参数:'{"status_code": 200, "content": "success"}'
    [API接口调用],方法:GET,URL:'https://www.baidu.com/2',请求头:'{"Content-Type": "application/json"}',请求参数:'{}',响应参数:'{"status_code": 200, "content": "success"}'
    [API接口调用],方法:GET,URL:'https://www.baidu.com/3',请求头:'{"Content-Type": "application/json"}',请求参数:'{}',响应参数:'{"status_code": 200, "content": "success"}'

    @teardown do
        [打印内容],内容:测试结束
        [API接口调用],方法:GET,URL:'https://www.baidu.com',请求头:'{"Content-Type": "application/json"}',请求参数:'{}',响应参数:'{"status_code": 200, "content": "success"}'
    end
    """

    try:
        ast = parser.parse(dsl_code, lexer=lexer)
        print_ast(ast)
    except Exception as e:
        print(f"Parser failed: {e}")