import ply.yacc as yacc
from lexer import tokens, get_lexer

class Node:
    def __init__(self, type, children=None, value=None):
        self.type = type
        self.children = children if children else []
        self.value = value

# Parser rules with adjustments

def p_start(p):
    '''start : metadata statements teardown
             | metadata statements'''
    if len(p) == 4:
        p[0] = Node('Start', [p[1], p[2], p[3]])
    else:
        p[0] = Node('Start', [p[1], p[2]])

def p_metadata(p):
    '''metadata : metadata_item metadata
                | metadata_item'''
    if len(p) == 3:
        p[0] = Node('Metadata', [p[1]] + p[2].children)
    else:
        p[0] = Node('Metadata', [p[1]])

def p_metadata_item(p):
    '''metadata_item : NAME_KEYWORD COLON STRING
                     | NAME_KEYWORD COLON ID
                     | DESCRIPTION_KEYWORD COLON STRING
                     | DESCRIPTION_KEYWORD COLON ID
                     | TAGS_KEYWORD COLON LBRACKET tags RBRACKET
                     | AUTHOR_KEYWORD COLON STRING
                     | AUTHOR_KEYWORD COLON ID
                     | DATE_KEYWORD COLON DATE'''
    if p[1] == '@tags':
        p[0] = Node(p[1], value=p[4])
    else:
        p[0] = Node(p[1], value=p[3])

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
        p[0] = Node('Statements', [p[1]] + p[2].children )
    else:
        p[0] = Node('Statements', [p[1]])

def p_statement(p):
    '''statement : assignment
                 | loop
                 | keyword_call'''
    p[0] = p[1]

def p_assignment(p):
    '''assignment : ID EQUALS expression'''
    p[0] = Node('Assignment', value=p[1], children=[p[3]])

def p_expression(p):
    '''expression : NUMBER
                  | STRING
                  | PLACEHOLDER
                  | ID
                  | keyword_call'''
    p[0] = Node('Expression', value=p[1])

def p_loop(p):
    '''loop : FOR ID IN RANGE LPAREN expression COMMA expression RPAREN DO statements END'''
    p[0] = Node('ForLoop', [p[6], p[8], p[11]], p[2])

def p_keyword_call(p):
    '''keyword_call : LBRACKET ID RBRACKET COMMA parameter_list'''
    p[0] = Node('KeywordCall', [p[5]], p[2])

def p_parameter_list(p):
    '''parameter_list : parameter_item
                      | parameter_list COMMA parameter_item'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]

def p_parameter_item(p):
    '''parameter_item : ID COLON expression'''
    p[0] = Node('ParameterItem', value=p[1], children=[p[3]])

def p_teardown(p):
    '''teardown : TEARDOWN_KEYWORD DO statements END'''
    p[0] = Node('Teardown', [p[3]])

# Error handling
def p_error(p):
    if p:
        print(f"Syntax error at token {p.type}, value: {p.value}, line: {p.lineno}, position: {p.lexpos}")
        # Error recovery: Skip until the next keyword or END token
        while True:
            tok = p.token()
            if not tok or tok.type in ['END', 'TEARDOWN_KEYWORD', 'LBRACKET']:
                break
        p.errok()
    else:
        print("Syntax error at EOF")

# AST printing function
def print_ast(node: Node, level: int = 0) -> None:
    indent = '  ' * level
    if node.value is not None:
        if isinstance(node.value, list):
            print(f"{indent}{node.type}:")
            for item in node.value:
                if isinstance(item, Node):
                    print_ast(item, level + 1)
                else:
                    print(f"{indent}  Non-node child: {item}")
        elif isinstance(node.value, Node):
            print_ast(node.value, level + 1)
        else:
            print(f"{indent}{node.type}: {node.value}")
    else:
        print(f"{indent}{node.type}:")
    
    for child in node.children:
        if isinstance(child, Node):
            print_ast(child, level + 1)
        elif isinstance(child, list):
            for item in child:
                if isinstance(item, Node):
                    print_ast(item, level + 2)
                else:
                    print(f"{indent}  Non-node child: {item}")
        else:
            print(f"{indent}  Non-node child: {child}")


def get_parser():
    return yacc.yacc()