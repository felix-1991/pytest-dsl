# execute.py
import allure
from lexer import get_lexer
from parser import get_parser, Node
from keywords import keywords, execute_keyword  # 假设 keywords.py 中有 execute_keyword 函数

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
            import re
            def replace_var(match):
                var_name = match.group(1)
                if var_name in variables:
                    return str(variables[var_name])
                else:
                    raise Exception(f"变量未定义: {var_name}")
            value = re.sub(r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}', replace_var, value)
            return value
        else:
            return value
    elif expr_node.type == 'KeywordCall':
        return execute(expr_node)
    else:
        raise Exception(f"无法求值的表达式类型: {expr_node.type}")

def execute(node):
    """
    根据AST节点类型执行相应的操作。
    
    :param node: AST中的节点
    :return: 对于某些节点类型（如KeywordCall），返回执行结果
    :raises Exception: 当遇到未知节点类型或执行失败时抛出异常
    """
    if node.type == 'Start':
        # 提取元信息并设置 Allure 报告的标题、描述和标签
        metadata = {}
        for child in node.children:
            if child.type == 'Metadata':
                for item in child.children:
                    metadata[item.type] = item.value
        if '@name' in metadata:
            allure.dynamic.title(metadata['@name'])
        if '@description' in metadata:
            allure.dynamic.description(metadata['@description'])
        if '@tags' in metadata:
            for tag in metadata['@tags']:
                allure.dynamic.tag(tag.value)
        for child in node.children:
            execute(child)
    elif node.type == 'Metadata':
        pass  # 元数据在 Start 节点中已处理
    elif node.type == 'Statements':
        for stmt in node.children:
            execute(stmt)
    elif node.type == 'Assignment':
        var_name = node.value
        expr_value = eval_expression(node.children[0])
        with allure.step(f"赋值: {var_name} = {expr_value}"):
            variables[var_name] = expr_value
    elif node.type == 'AssignmentKeywordCall':
        var_name = node.value
        keyword_call_node = node.children[0]
        with allure.step(f"执行关键字调用并赋值给 {var_name}"):
            result = execute(keyword_call_node)
            if result is not None:
                variables[var_name] = result
                allure.attach(
                    f"变量: {var_name}\n值: {result}",
                    name="赋值详情",
                    attachment_type=allure.attachment_type.TEXT
                )
            else:
                raise Exception(f"关键字 {keyword_call_node.value} 没有返回结果")
    elif node.type == 'ForLoop':
        var_name = node.value
        start = eval_expression(node.children[0])
        end = eval_expression(node.children[1])
        with allure.step(f"执行循环: for {var_name} in range({start}, {end})"):
            for i in range(int(start), int(end)):
                variables[var_name] = i
                with allure.step(f"循环轮次: {var_name} = {i}"):
                    execute(node.children[2])
    elif node.type == 'KeywordCall':
        keyword_name = node.value
        keyword_info = keywords.get(keyword_name)
        if not keyword_info:
            raise Exception(f"未注册的关键字: {keyword_name}")
        mapping = keyword_info.get('mapping', {})
        kwargs = {}
        for param in node.children[0]:
            param_name = param.value
            english_param_name = mapping.get(param_name, param_name)
            kwargs[english_param_name] = eval_expression(param.children[0])
        with allure.step(f"执行关键字: {keyword_name}"):
            try:
                result = execute_keyword(keyword_name, **kwargs)
                allure.attach(
                    f"关键字: {keyword_name}\n参数: {kwargs}\n返回值: {result}",
                    name="执行详情",
                    attachment_type=allure.attachment_type.TEXT
                )
                return result
            except Exception as e:
                allure.attach(
                    f"关键字: {keyword_name}\n参数: {kwargs}\n异常: {str(e)}",
                    name="执行失败",
                    attachment_type=allure.attachment_type.TEXT
                )
                raise
    elif node.type == 'Teardown':
        with allure.step("执行 Teardown 清理操作"):
            execute(node.children[0])
    else:
        raise Exception(f"未知的节点类型: {node.type}")

def read_file(filename):
    """读取 DSL 文件内容"""
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