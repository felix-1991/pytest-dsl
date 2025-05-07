import ply.lex as lex

# 保留字（关键字）
reserved = {
    'do': 'DO',
    'end': 'END',
    'for': 'FOR',
    'in': 'IN',
    'range': 'RANGE',
    'using': 'USING',  # Add new keyword for data-driven testing
    'True': 'TRUE',    # 添加布尔值支持
    'False': 'FALSE',   # 添加布尔值支持
    'return': 'RETURN'  # 添加return关键字支持
}

# token 名称列表
tokens = [
    'ID',
    'NUMBER',
    'EQUALS',
    'STRING',
    'DATE',
    'LPAREN',
    'RPAREN',
    'LBRACKET',
    'RBRACKET',
    'COLON',
    'COMMA',
    'PLACEHOLDER',
    'NAME_KEYWORD',
    'DESCRIPTION_KEYWORD',
    'TAGS_KEYWORD',
    'AUTHOR_KEYWORD',
    'DATE_KEYWORD',
    'TEARDOWN_KEYWORD',
    'DATA_KEYWORD',  # Add new token for @data keyword
    'KEYWORD_KEYWORD',  # 添加@keyword关键字
    'IMPORT_KEYWORD',   # 添加@import关键字
] + list(reserved.values())

# 正则表达式定义 token
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_LBRACKET = r'\['
t_RBRACKET = r'\]'
t_COLON = r':'
t_COMMA = r','
t_EQUALS = r'='

# 增加PLACEHOLDER规则，匹配 ${变量名} 格式
t_PLACEHOLDER = r'\$\{[a-zA-Z_\u4e00-\u9fa5][a-zA-Z0-9_\u4e00-\u9fa5]*\}'


def t_DATE(t):
    r'\d{4}-\d{2}-\d{2}(\s+\d{2}:\d{2}:\d{2})?'
    return t


def t_ID(t):
    r'[a-zA-Z_\u4e00-\u9fa5][a-zA-Z0-9_\u4e00-\u9fa5]*'
    t.type = reserved.get(t.value, 'ID')
    return t


def t_STRING(t):
    r"""(\'\'\'[\s\S]*?\'\'\'|\"\"\"[\s\S]*?\"\"\"|'[^']*'|\"[^\"]*\")"""
    # 处理单引号和双引号的多行/单行字符串
    if t.value.startswith("'''") or t.value.startswith('"""'):
        t.value = t.value[3:-3]  # 去掉三引号
    else:
        t.value = t.value[1:-1]  # 去掉单引号或双引号
    return t

# 定义以 @ 开头的关键字的 token 规则


def t_NAME_KEYWORD(t):
    r'@name'
    return t


def t_DESCRIPTION_KEYWORD(t):
    r'@description'
    return t


def t_TAGS_KEYWORD(t):
    r'@tags'
    return t


def t_AUTHOR_KEYWORD(t):
    r'@author'
    return t


def t_DATE_KEYWORD(t):
    r'@date'
    return t


def t_TEARDOWN_KEYWORD(t):
    r'@teardown'
    return t


def t_DATA_KEYWORD(t):
    r'@data'
    return t


def t_KEYWORD_KEYWORD(t):
    r'@keyword'
    return t


def t_IMPORT_KEYWORD(t):
    r'@import'
    return t


def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t


# 忽略空格和制表符
t_ignore = ' \t'

# 忽略注释
t_ignore_COMMENT = r'\#.*'

# 跟踪行号


def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# 错误处理


def t_error(t):
    print(f"非法字符 '{t.value[0]}' 在行 {t.lineno} 位置 {t.lexpos}")
    t.lexer.skip(1)

# 模块接口


def get_lexer():
    return lex.lex()
