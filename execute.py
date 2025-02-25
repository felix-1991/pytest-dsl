from lexer import get_lexer
from parser import get_parser, Node
from keywords import keywords 

# 定义全局变量字典，用于存储DSL中定义的变量及其值
variables = {}

def eval_expression(expr_node):
    """
    对表达式节点进行求值，返回表达式的值。
    
    :param expr_node: AST中的表达式节点
    :return: 表达式求值后的结果
    :raises Exception: 当遇到未定义变量或无法求值的类型时抛出异常
    """
    if expr_node.type == 'Expression':
        value = expr_node.value  # 获取节点的值
        if isinstance(value, Node):
            # 如果值本身是一个节点，递归求值
            return eval_expression(value)
        elif isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            # 处理变量引用，例如 ${var_name}
            var_name = value[2:-1]  # 提取变量名，去掉${和}
            if var_name in variables:
                return variables[var_name]  # 返回变量的值
            else:
                raise Exception(f"变量未定义: {var_name}")
        elif isinstance(value, str):
            # 处理字符串中的变量替换，例如 "Hello ${name}"
            import re

            def replace_var(match):
                """替换字符串中的变量引用"""
                var_name = match.group(1)  # 获取正则匹配中的变量名
                if var_name in variables:
                    return str(variables[var_name])  # 返回变量值的字符串形式
                else:
                    raise Exception(f"变量未定义: {var_name}")
            
            # 使用正则表达式替换所有 ${var_name} 形式的变量引用
            value = re.sub(r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}', replace_var, value)
            return value
        else:
            # 直接返回基本类型的值（如整数、浮点数等）
            return value
    elif expr_node.type == 'KeywordCall':
        # 如果是关键字调用，执行关键字并返回结果
        return execute(expr_node)
    else:
        # 遇到无法处理的表达式类型，抛出异常
        raise Exception(f"无法求值的表达式类型: {expr_node.type}")

def execute(node):
    """
    根据AST节点类型执行相应的操作。
    
    :param node: AST中的节点
    :return: 对于某些节点类型（如KeywordCall），返回执行结果
    :raises Exception: 当遇到未知节点类型或执行失败时抛出异常
    """
    if node.type == 'Start':
        # 根节点，执行所有子节点
        for child in node.children:
            execute(child)
    elif node.type == 'Metadata':
        # 元数据节点，不执行任何操作
        pass
    elif node.type == 'Statements':
        # 语句块，依次执行所有子语句
        for stmt in node.children:
            execute(stmt)
    elif node.type == 'Assignment':
        # 赋值操作，将表达式的值赋给变量
        var_name = node.value  # 变量名
        expr_value = eval_expression(node.children[0])  # 求值表达式
        variables[var_name] = expr_value  # 存储到全局变量字典
    elif node.type == 'AssignmentKeywordCall':
        # 执行关键字调用并将结果赋值给变量
        var_name = node.value  # 变量名
        keyword_call_node = node.children[0]  # 子节点是KeywordCall类型
        result = execute(keyword_call_node)  # 执行关键字调用
        if result is not None:
            variables[var_name] = result  # 将结果保存到变量
        else:
            raise Exception(f"关键字 {keyword_call_node.value} 没有返回结果")
    elif node.type == 'ForLoop':
        # 处理for循环
        var_name = node.value  # 循环变量名
        start = eval_expression(node.children[0])  # 循环起始值
        end = eval_expression(node.children[1])  # 循环结束值
        for i in range(int(start), int(end)):
            variables[var_name] = i  # 更新循环变量
            execute(node.children[2])  # 执行循环体
    elif node.type == 'KeywordCall':
        # 执行关键字调用
        keyword_name = node.value  # 关键字名称
        keyword_info = keywords.get(keyword_name)  # 获取关键字信息
        if not keyword_info:
            raise Exception(f"未注册的关键字: {keyword_name}")
        if 'mapping' not in keyword_info:
            raise Exception(f"关键字 {keyword_name} 未定义参数映射")

        # 解析关键字参数
        func = keyword_info['func']  # 关键字对应的函数
        mapping = keyword_info['mapping']  # 参数名映射（中文到英文）
        kwargs = {}  # 存储参数的键值对
        for param in node.children[0]:  # 遍历参数节点
            param_name = param.value  # 参数名（中文）
            if param_name not in mapping:
                raise Exception(f"参数名 {param_name} 未定义映射关系")
            english_param_name = mapping[param_name]  # 转换为英文参数名
            kwargs[english_param_name] = eval_expression(param.children[0])  # 求值参数值

        # 调用关键字函数并返回结果
        result = func(**kwargs)
        return result
    elif node.type == 'ParameterItem':
        # 处理参数项，返回参数名和值的字典
        return {node.value: eval_expression(node.children[0])}
    elif node.type == 'Teardown':
        # 执行tear down操作
        execute(node.children[0])
    else:
        # 未知节点类型，抛出异常
        raise Exception(f"未知的节点类型: {node.type}")

def read_file(filename):
    """
    读取DSL文件的内容。
    
    :param filename: 文件路径
    :return: 文件内容的字符串
    """
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

if __name__ == '__main__':
    # 主程序入口
    lexer = get_lexer()  # 初始化词法分析器
    parser = get_parser()  # 初始化语法分析器

    # 读取DSL文件内容
    dsl_code = read_file('test.auto')

    try:
        # 解析DSL代码生成抽象语法树（AST）
        ast = parser.parse(dsl_code, lexer=lexer)
        # 执行AST
        execute(ast)
    except Exception as e:
        # 捕获并打印执行过程中的异常
        print(f"执行失败: {e}")