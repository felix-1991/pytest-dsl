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
    'return': 'RETURN',  # 添加return关键字支持
    'else': 'ELSE',   # 添加else关键字支持
    'elif': 'ELIF',   # 添加elif关键字支持
    'if': 'IF',  # 添加if关键字支持
    'as': 'AS',   # 添加as关键字支持，用于远程关键字别名
    'function': 'FUNCTION',  # 添加function关键字支持，用于自定义关键字定义
    'teardown': 'TEARDOWN',   # 添加teardown关键字支持，用于清理操作
    'break': 'BREAK',  # 添加break关键字支持，用于循环控制
    'continue': 'CONTINUE'  # 添加continue关键字支持，用于循环控制
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
    'LBRACE',    # 左大括号 {，用于字典字面量
    'RBRACE',    # 右大括号 }，用于字典字面量
    'COLON',
    'COMMA',
    'PLACEHOLDER',
    'NAME_KEYWORD',
    'DESCRIPTION_KEYWORD',
    'TAGS_KEYWORD',
    'AUTHOR_KEYWORD',
    'DATE_KEYWORD',
    'DATA_KEYWORD',  # Add new token for @data keyword
    'IMPORT_KEYWORD',   # 添加@import关键字
    'REMOTE_KEYWORD',   # 添加@remote关键字
    'GT',        # 大于 >
    'LT',        # 小于 <
    'GE',        # 大于等于 >=
    'LE',        # 小于等于 <=
    'EQ',        # 等于 ==
    'NE',        # 不等于 !=
    'PLUS',      # 加法 +
    'MINUS',     # 减法 -
    'TIMES',     # 乘法 *
    'DIVIDE',    # 除法 /
    'MODULO',    # 模运算 %
    'PIPE',      # 管道符 |，用于远程关键字调用
] + list(reserved.values())

# 正则表达式定义 token
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_LBRACKET = r'\['
t_RBRACKET = r'\]'
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_COLON = r':'
t_COMMA = r','
t_EQUALS = r'='
t_GT = r'>'
t_LT = r'<'
t_GE = r'>='
t_LE = r'<='
t_EQ = r'=='
t_NE = r'!='
t_PLUS = r'\+'
t_MINUS = r'-'
t_TIMES = r'\*'
t_DIVIDE = r'/'
t_MODULO = r'%'

# 增加PLACEHOLDER规则，匹配 ${变量名} 格式，支持点号、数组索引和字典键访问
# 匹配: ${variable}, ${obj.prop}, ${arr[0]}, ${dict["key"]}, ${obj[0].prop} 等
t_PLACEHOLDER = (r'\$\{[a-zA-Z_\u4e00-\u9fa5][a-zA-Z0-9_\u4e00-\u9fa5]*'
                 r'(?:(?:\.[a-zA-Z_\u4e00-\u9fa5][a-zA-Z0-9_\u4e00-\u9fa5]*)'
                 r'|(?:\[[^\]]+\]))*\}')

# 添加管道符的正则表达式定义
t_PIPE = r'\|'

# 添加@remote关键字的token规则
def t_REMOTE_KEYWORD(t):
    r'@remote'
    return t


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


def t_DATA_KEYWORD(t):
    r'@data'
    return t


def t_IMPORT_KEYWORD(t):
    r'@import'
    return t


def t_NUMBER(t):
    r'\d+(\.\d+)?'
    # 如果包含小数点，转换为浮点数；否则转换为整数
    if '.' in t.value:
        t.value = float(t.value)
    else:
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
