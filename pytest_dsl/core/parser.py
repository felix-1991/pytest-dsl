import ply.yacc as yacc
from pytest_dsl.core.lexer import tokens, get_lexer


class Node:
    def __init__(self, type, children=None, value=None):
        self.type = type
        self.children = children if children else []
        self.value = value


# 定义优先级和结合性
precedence = (
    ('left', 'COMMA'),
    ('left', 'GT', 'LT', 'GE', 'LE', 'EQ', 'NE'),  # 比较运算符优先级
    ('left', 'PLUS', 'MINUS'),  # 加减运算符优先级
    ('left', 'TIMES', 'DIVIDE'),  # 乘除运算符优先级
    ('right', 'EQUALS'),
)


def p_start(p):
    '''start : metadata statements teardown
             | metadata statements
             | statements teardown
             | statements'''

    if len(p) == 4:
        p[0] = Node('Start', [p[1], p[2], p[3]])
    elif len(p) == 3:
        # 判断第二个元素是teardown还是statements
        if p[2].type == 'Teardown':
            p[0] = Node('Start', [Node('Metadata', []), p[1], p[2]])
        else:
            p[0] = Node('Start', [p[1], p[2]])
    else:
        # 没有metadata和teardown
        p[0] = Node('Start', [Node('Metadata', []), p[1]])


def p_metadata(p):
    '''metadata : metadata_items
                | empty'''
    if p[1]:
        p[0] = Node('Metadata', p[1])
    else:
        p[0] = Node('Metadata', [])


def p_empty(p):
    '''empty :'''
    p[0] = None


def p_metadata_items(p):
    '''metadata_items : metadata_item metadata_items
                     | metadata_item'''
    if len(p) == 3:
        p[0] = [p[1]] + p[2]
    else:
        p[0] = [p[1]]


def p_metadata_item(p):
    '''metadata_item : NAME_KEYWORD COLON metadata_value
                    | DESCRIPTION_KEYWORD COLON metadata_value
                    | TAGS_KEYWORD COLON LBRACKET tags RBRACKET
                    | AUTHOR_KEYWORD COLON metadata_value
                    | DATE_KEYWORD COLON DATE
                    | DATA_KEYWORD COLON data_source
                    | IMPORT_KEYWORD COLON STRING'''
    if p[1] == '@tags':
        p[0] = Node(p[1], value=p[4])
    elif p[1] == '@data':
        # 对于数据驱动测试，将数据源信息存储在节点中
        data_info = p[3]  # 这是一个包含 file 和 format 的字典
        p[0] = Node(p[1], value=data_info, children=None)
    elif p[1] == '@import':
        p[0] = Node(p[1], value=p[3])
    else:
        p[0] = Node(p[1], value=p[3])


def p_metadata_value(p):
    '''metadata_value : STRING
                     | ID'''
    p[0] = p[1]


def p_tags(p):
    '''tags : tag COMMA tags
            | tag'''
    if len(p) == 4:
        p[0] = [p[1]] + p[3]
    else:
        p[0] = [p[1]]


def p_tag(p):
    '''tag : STRING
           | ID'''
    p[0] = Node('Tag', value=p[1])


def p_statements(p):
    '''statements : statement statements
                  | statement'''
    if len(p) == 3:
        p[0] = Node('Statements', [p[1]] + p[2].children)
    else:
        p[0] = Node('Statements', [p[1]])


def p_statement(p):
    '''statement : assignment
                | keyword_call
                | loop
                | custom_keyword
                | return_statement
                | if_statement'''
    p[0] = p[1]


def p_assignment(p):
    '''assignment : ID EQUALS expression
                 | ID EQUALS keyword_call'''
    if isinstance(p[3], Node) and p[3].type == 'KeywordCall':
        p[0] = Node('AssignmentKeywordCall', [p[3]], p[1])
    else:
        p[0] = Node('Assignment', value=p[1], children=[p[3]])


def p_expression(p):
    '''expression : expr_atom
                  | comparison_expr
                  | arithmetic_expr'''
    # 如果是比较表达式或其他复合表达式，则已经是一个Node对象
    if isinstance(p[1], Node):
        p[0] = p[1]
    else:
        p[0] = Node('Expression', value=p[1])


def p_expr_atom(p):
    '''expr_atom : NUMBER
                 | STRING
                 | PLACEHOLDER
                 | ID
                 | boolean_expr
                 | list_expr
                 | LPAREN expression RPAREN'''
    if p[1] == '(':
        # 处理括号表达式，直接返回括号内的表达式节点
        p[0] = p[2]
    elif isinstance(p[1], Node):
        p[0] = p[1]
    else:
        p[0] = Node('Expression', value=p[1])


def p_boolean_expr(p):
    '''boolean_expr : TRUE
                    | FALSE'''
    p[0] = Node('BooleanExpr', value=True if p[1] == 'True' else False)


def p_list_expr(p):
    '''list_expr : LBRACKET list_items RBRACKET
                 | LBRACKET RBRACKET'''
    if len(p) == 4:
        p[0] = Node('ListExpr', children=p[2])
    else:
        p[0] = Node('ListExpr', children=[])  # 空列表


def p_list_items(p):
    '''list_items : list_item
                  | list_item COMMA list_items'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1]] + p[3]


def p_list_item(p):
    '''list_item : expression'''
    p[0] = p[1]


def p_loop(p):
    '''loop : FOR ID IN RANGE LPAREN expression COMMA expression RPAREN DO statements END'''
    p[0] = Node('ForLoop', [p[6], p[8], p[11]], p[2])


def p_keyword_call(p):
    '''keyword_call : LBRACKET ID RBRACKET COMMA parameter_list
                   | LBRACKET ID RBRACKET'''
    if len(p) == 6:
        p[0] = Node('KeywordCall', [p[5]], p[2])
    else:
        p[0] = Node('KeywordCall', [[]], p[2])


def p_parameter_list(p):
    '''parameter_list : parameter_items'''
    p[0] = p[1]


def p_parameter_items(p):
    '''parameter_items : parameter_item COMMA parameter_items
                     | parameter_item'''
    if len(p) == 4:
        p[0] = [p[1]] + p[3]
    else:
        p[0] = [p[1]]


def p_parameter_item(p):
    '''parameter_item : ID COLON expression'''
    p[0] = Node('ParameterItem', value=p[1], children=[p[3]])


def p_teardown(p):
    '''teardown : TEARDOWN_KEYWORD DO statements END'''
    p[0] = Node('Teardown', [p[3]])


def p_data_source(p):
    '''data_source : STRING USING ID'''
    p[0] = {'file': p[1], 'format': p[3]}


def p_custom_keyword(p):
    '''custom_keyword : KEYWORD_KEYWORD ID LPAREN param_definitions RPAREN DO statements END'''
    p[0] = Node('CustomKeyword', [p[4], p[7]], p[2])


def p_param_definitions(p):
    '''param_definitions : param_def_list
                        | '''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = []


def p_param_def_list(p):
    '''param_def_list : param_def COMMA param_def_list
                     | param_def'''
    if len(p) == 4:
        p[0] = [p[1]] + p[3]
    else:
        p[0] = [p[1]]


def p_param_def(p):
    '''param_def : ID EQUALS STRING
                | ID EQUALS NUMBER
                | ID'''
    if len(p) == 4:
        p[0] = Node('ParameterDef', [Node('Expression', value=p[3])], p[1])
    else:
        p[0] = Node('ParameterDef', [], p[1])


def p_return_statement(p):
    '''return_statement : RETURN expression'''
    p[0] = Node('Return', [p[2]])


def p_if_statement(p):
    '''if_statement : IF expression DO statements END
                   | IF expression DO statements ELSE statements END'''
    if len(p) == 6:
        p[0] = Node('IfStatement', [p[2], p[4]], None)
    else:
        p[0] = Node('IfStatement', [p[2], p[4], p[6]], None)


def p_comparison_expr(p):
    '''comparison_expr : expr_atom GT expr_atom
                      | expr_atom LT expr_atom
                      | expr_atom GE expr_atom
                      | expr_atom LE expr_atom
                      | expr_atom EQ expr_atom
                      | expr_atom NE expr_atom'''
    
    # 根据规则索引判断使用的是哪个操作符
    if p.slice[2].type == 'GT':
        operator = '>'
    elif p.slice[2].type == 'LT':
        operator = '<'
    elif p.slice[2].type == 'GE':
        operator = '>='
    elif p.slice[2].type == 'LE':
        operator = '<='
    elif p.slice[2].type == 'EQ':
        operator = '=='
    elif p.slice[2].type == 'NE':
        operator = '!='
    else:
        print(f"警告: 无法识别的操作符类型 {p.slice[2].type}")
        operator = None
    
    p[0] = Node('ComparisonExpr', [p[1], p[3]], operator)


def p_arithmetic_expr(p):
    '''arithmetic_expr : expression PLUS expression
                       | expression MINUS expression
                       | expression TIMES expression
                       | expression DIVIDE expression'''
    
    # 根据规则索引判断使用的是哪个操作符
    if p.slice[2].type == 'PLUS':
        operator = '+'
    elif p.slice[2].type == 'MINUS':
        operator = '-'
    elif p.slice[2].type == 'TIMES':
        operator = '*'
    elif p.slice[2].type == 'DIVIDE':
        operator = '/'
    else:
        print(f"警告: 无法识别的操作符类型 {p.slice[2].type}")
        operator = None
    
    p[0] = Node('ArithmeticExpr', [p[1], p[3]], operator)


def p_error(p):
    if p:
        print(
            f"语法错误: 在第 {p.lineno} 行, 位置 {p.lexpos}, Token {p.type}, 值: {p.value}")
    else:
        print("语法错误: 在文件末尾")


def get_parser(debug=False):
    return yacc.yacc(debug=debug)
