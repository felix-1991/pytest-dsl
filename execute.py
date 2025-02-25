from lexer import get_lexer
from parser import get_parser, Node
from keywords import keywords


variables = {}


def eval_expression(expr_node):
    if expr_node.type == 'Expression':
        value = expr_node.value
        if isinstance(value, Node):
            return eval_expression(value)
        elif isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            var_name = value[2:-1]
            if var_name in variables:
                return variables[var_name]
            else:
                raise Exception(f"变量未定义: {var_name}")
        elif isinstance(value, str):
            # 处理字符串中的变量替换
            import re

            def replace_var(match):
                var_name = match.group(1)
                if var_name in variables:
                    return str(variables[var_name])
                else:
                    raise Exception(f"变量未定义: {var_name}")
            value = re.sub(
                r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}', replace_var, value)
            return value
        else:
            return value
    elif expr_node.type == 'KeywordCall':
        return execute(expr_node)
    else:
        raise Exception(f"无法求值的表达式类型: {expr_node.type}")


def execute(node):
    if node.type == 'Start':
        for child in node.children:
            execute(child)
    elif node.type == 'Metadata':
        pass  # Metadata不执行
    elif node.type == 'Statements':
        for stmt in node.children:
            execute(stmt)
    elif node.type == 'Assignment':
        var_name = node.value
        expr_value = eval_expression(node.children[0])
        variables[var_name] = expr_value
    elif node.type == 'AssignmentKeywordCall':
        var_name = node.value
        keyword_call_node = node.children[0]  # 子节点是 KeywordCall
        result = execute(keyword_call_node)  # 执行关键字调用
        if result is not None:
            variables[var_name] = result  # 将结果保存到变量中
        else:
            raise Exception(f"关键字 {keyword_call_node.value} 没有返回结果")
    elif node.type == 'ForLoop':
        var_name = node.value
        start = eval_expression(node.children[0])
        end = eval_expression(node.children[1])
        for i in range(int(start), int(end)):
            variables[var_name] = i
            execute(node.children[2])
    elif node.type == 'KeywordCall':
        # 查找关键字信息
        keyword_name = node.value
        keyword_info = keywords.get(keyword_name)
        if not keyword_info:
            raise Exception(f"未注册的关键字: {keyword_name}")
        if 'mapping' not in keyword_info:
            raise Exception(f"关键字 {keyword_name} 未定义参数映射")

        # 解析参数
        func = keyword_info['func']
        mapping = keyword_info['mapping']
        kwargs = {}
        for param in node.children[0]:
            param_name = param.value  # 中文参数名
            if param_name not in mapping:
                raise Exception(f"参数名 {param_name} 未定义映射关系")
            english_param_name = mapping[param_name]
            kwargs[english_param_name] = eval_expression(param.children[0])

        # 执行关键字函数
        result = func(**kwargs)
        return result
    elif node.type == 'ParameterItem':
        return {node.value: eval_expression(node.children[0])}
    elif node.type == 'Teardown':
        execute(node.children[0])
    else:
        raise Exception(f"未知的节点类型: {node.type}")


def read_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()


if __name__ == '__main__':
    lexer = get_lexer()
    parser = get_parser()

    dsl_code = read_file('test.auto')

    try:
        ast = parser.parse(dsl_code, lexer=lexer)
        execute(ast)
    except Exception as e:
        print(f"执行失败: {e}")
