from core.lexer import get_lexer
from core.parser import get_parser
from core.dsl_executor import DSLExecutor
# 导入所有关键字定义
from keywords import api_keywords, system_keywords


def read_file(filename):
    """读取 DSL 文件内容"""
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    lexer = get_lexer()
    parser = get_parser()
    executor = DSLExecutor()
    
    try:
        dsl_code = read_file('test.auto')
        ast = parser.parse(dsl_code, lexer=lexer)
        executor.execute(ast)
    except Exception as e:
        print(f"执行失败: {e}")

if __name__ == '__main__':
    main()